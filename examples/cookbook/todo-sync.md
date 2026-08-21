# Кукбук: инкрементальная синхронизация дел (Todo)

Вы храните у себя копию дел ("Дела", `Todo`) из Мегаплана и хотите узнавать,
что изменилось, не перечитывая весь список каждый раз. Для задач (`Task`) и
сделок (`Deal`) для этого есть `timeUpdated` и фильтр по времени изменения.
У `Todo` этого нет — и это не недосмотр, а факт API, с которым нужно
проектировать интеграцию иначе.

## Почему нельзя просто спросить "что изменилось"

Три факта:

1. **У `Todo` нет `timeUpdated`.** Проверено на живом аккаунте: полный
   `GET /api/v3/todo/{id}` не содержит такого поля ни при каких
   обстоятельствах — только `timeCreated` и `timeFinished`. Спросить "дай мне
   дела, изменённые после X" через API нельзя в принципе, потому что серверу
   нечем ответить на такой вопрос.
2. **Через сделку это тоже, судя по всему, не поймать.** По наблюдениям
   интегратора, задавшего исходный вопрос («создание Todo, изменение `when`
   и завершение Todo не меняют `Deal.timeUpdated`»), и подтверждению
   поддержки Мегаплана — изменение привязанного к сделке дела не трогает
   `Deal.timeUpdated`. На нашем стенде это отдельно не проверялось. В любом
   случае полагаться на `timeUpdated` сделки как индикатор изменений её дел
   не стоит: даже если это поведение когда-то изменится, для дел остаётся
   единственный надёжный источник — они сами (см. ниже), а не сделка,
   к которой они привязаны.
3. **Клиентский фильтр по дате не помогает.** Мегаплан молча игнорирует
   незнакомые поля фильтра (200 OK и полная невырезанная выборка), поэтому
   полагаться на самодельный `filter` по датам для `Todo` нельзя — сервер не
   откажет с ошибкой, он просто вернёт всё как есть, и это легко принять за
   рабочий фильтр, пока не сравните количество строк руками.

Отсюда архитектура: **основной канал — вебхуки**, `TodoSync` из SDK — это
**страховка и первичная загрузка**, а не замена вебхукам.

## Основной канал: поток событий `Todo`

В Мегаплане у приложений есть поток событий (webhooks), и для дел он несёт
события `on_after_create`, `on_after_update` (в том числе завершение дела —
это тоже `update`, смена статуса) и `on_after_drop`. Дело в этом потоке
приходит как сущность `Todo` — в payload события `model`/`contentType`
равны `"Todo"`. Полное описание конверта событий и подключения приложения —
в официальной документации: <https://dev.megaplan.ru/apps/events.html>.

Условия, которые обязан соблюдать приёмник:

- **Отвечать `200 OK` не дольше 20 секунд.** Дольше — Мегаплан считает
  доставку неуспешной.
- **Доставка at-least-once.** Одно и то же событие может прийти повторно —
  дедуплицируйте по `uuid` события на своей стороне (например, храните
  последние N обработанных `uuid` или используйте таблицу с уникальным
  ключом на `uuid`).
- **При ошибке следующие события удерживаются.** Если приёмник ответил не
  `200` (или не уложился в таймаут), Мегаплан не продолжит слать более новые
  события для этого приложения, пока не будет обработано зависшее — то есть
  сломанный приёмник останавливает всю очередь, не только одно событие.
  Поэтому обработчик должен быть быстрым и не падать на неожиданной форме
  payload.

SDK не предоставляет HTTP-сервер для приёма вебхуков — это часть вашего
приложения (свой фреймворк, свой роутинг). Ниже — обработчик, независимый от
фреймворка: вы вызываете его из своего HTTP-хендлера после разбора JSON тела
запроса.

```python
"""Example webhook receiver for the Megaplan "events" stream (Todo events).

Wire `handle_todo_event` into your own web framework's route — it does not
depend on one. The exact envelope fields (`uuid`, `model`, action name) are
documented at https://dev.megaplan.ru/apps/events.html; consult it for the
byte-exact shape your account sends.
"""

from __future__ import annotations

from typing import Any

from megaplan_sdk import MegaplanClient

# Dedup store for event uuids already processed. A real implementation
# should use something durable (Redis, a database table with a unique
# constraint on uuid) — a process-local set only survives one process.
_seen_event_uuids: set[str] = set()


async def handle_todo_event(client: MegaplanClient, event: dict[str, Any]) -> None:
    """Handle one "events" webhook payload for a Todo change.

    Args:
        client: An authenticated MegaplanClient.
        event: Parsed JSON body of the webhook request.

    Note:
        Delivery is at-least-once — the same uuid can arrive more than once.
        Your route handler must still answer 200 within 20 seconds even if
        this function decides there is nothing to do.
    """
    event_uuid = event.get("uuid")
    if event_uuid is not None:
        if event_uuid in _seen_event_uuids:
            return  # already processed, this is a redelivery
        _seen_event_uuids.add(event_uuid)

    action = event.get("action")  # e.g. "on_after_create" / "on_after_update" / "on_after_drop"
    todo_id = event.get("model", {}).get("id") or event.get("id")
    if todo_id is None:
        return

    if action == "on_after_drop":
        await remove_local_todo(int(todo_id))
        return

    # on_after_create / on_after_update: re-fetch the current state and
    # upsert it locally. Finishing a todo is also on_after_update — there
    # is no separate "finished" event, check the fresh status yourself.
    todo = await client.todos.get(int(todo_id))
    await upsert_local_todo(todo)


async def remove_local_todo(todo_id: int) -> None:
    """Placeholder: delete the todo from your local store."""


async def upsert_local_todo(todo: Any) -> None:
    """Placeholder: insert or update the todo in your local store."""
```

## Страховка и первичная загрузка: `TodoSync`

Вебхуки могут быть пропущены (приёмник лежал, деплой, сетевой сбой дольше
удержания очереди) или вы подключаете интеграцию не с нуля — нужен и способ
загрузить текущее состояние, и периодическая сверка "на всякий случай".
Для этого в SDK есть `megaplan_sdk.sync.TodoSync`.

`TodoSync` не спрашивает сервер "что изменилось" (спросить нельзя — см.
выше). Вместо этого он на каждом опросе проходит весь список дел через
`client.todos.iterate()` и сравнивает отпечаток (fingerprint) значимых полей
каждого дела с отпечатком из предыдущего состояния. Состояние
(`TodoSyncState`) — обычный сериализуемый объект, который хранит и
передаёт между вызовами вызывающий код; сам `TodoSync` не пишет ничего на
диск и не хранит глобального состояния.

```python
"""First run, saving state, and a second run with TodoSync."""

from __future__ import annotations

import json

from megaplan_sdk import MegaplanClient
from megaplan_sdk.sync import TodoSync, TodoSyncState


async def first_run(client: MegaplanClient) -> str:
    """Initial load: every in-window todo is reported as `created`."""
    sync = TodoSync(client.todos, window_days=30)
    changes = await sync.poll()  # state=None → first poll

    for todo in changes.created:
        print("new:", todo.id, todo.name)

    # Persist state.to_dict() somewhere durable (a file, a database row,
    # a cache key) — TodoSync itself keeps nothing between calls.
    return json.dumps(changes.state.to_dict())


async def next_run(client: MegaplanClient, saved_state_json: str) -> str:
    """A later poll: diff against the previously saved state."""
    sync = TodoSync(client.todos, window_days=30)
    state = TodoSyncState.from_dict(json.loads(saved_state_json))
    changes = await sync.poll(state)

    for todo in changes.created:
        apply_create(todo)
    for todo in changes.updated:
        apply_update(todo)
    for todo_id in changes.deleted:
        apply_delete(todo_id)

    return json.dumps(changes.state.to_dict())


def apply_create(todo: object) -> None:
    """Placeholder: insert the todo into your local store."""


def apply_update(todo: object) -> None:
    """Placeholder: update the todo in your local store."""


def apply_delete(todo_id: int) -> None:
    """Placeholder: remove the todo from your local store."""
```

## Самое важное место: что значит `deleted` и флаг `looks_truncated`

Это единственная часть рецепта, которую нельзя пропустить не читая.

`TodoChanges.deleted` означает **ровно одно**: сервер перестал отдавать этот
`id` вообще. Это не то же самое, что "дело вне текущего окна
(`window_days`)". Дело, которое сервер по-прежнему отдаёт, но которое больше
не проходит окно (например, завершилось и стало старше `window_days`), тихо
уходит из внутреннего состояния `TodoSyncState.fingerprints` **без**
попадания в `deleted`. Спутать одно с другим означало бы: рутинная смена
окна выглядит для потребителя как массовое удаление, и наивная реализация
удалит из локальной копии живые данные.

Отсюда же берётся `TodoChanges.looks_truncated`. Пустой ответ сервера при
непустом предыдущем состоянии сам по себе подозрителен: это может быть
временный сбой прав, пустая страница, обрыв пагинации — а не "все дела
разом удалили". Поэтому если сервер вернул пустой список дел, а до этого
`TodoSync` уже что-то знал, `poll()` **не трогает снапшот**: возвращает
`deleted=[]`, `state`, равный переданному, и `looks_truncated=True`.

```python
"""Handling `looks_truncated` before touching `deleted`."""

from __future__ import annotations

from megaplan_sdk.sync import TodoSync, TodoSyncState


async def guarded_poll(sync: TodoSync, state: TodoSyncState) -> TodoSyncState:
    changes = await sync.poll(state)

    if changes.looks_truncated:
        # The response looked empty/suspect. `changes.deleted` is guaranteed
        # empty and `changes.state` is unchanged — do NOT propagate `deleted`
        # to your local store here, just retry the poll later.
        log_suspect_response()
    else:
        for todo_id in changes.deleted:
            apply_delete(todo_id)

    return changes.state


def log_suspect_response() -> None:
    """Placeholder: record that this poll's response was not trusted."""


def apply_delete(todo_id: int) -> None:
    """Placeholder: remove the todo from your local store."""
```

**Обязательное правило для потребителя:** при `looks_truncated=True`
пропустите обработку `deleted` (он и так пуст) и просто повторите опрос
позже. Реализация, которая зеркалит `deleted` в свою копию без проверки
этого флага, рискует стереть живые данные при любом транзиентном сбое ответа
сервера.

## Честное ограничение окна

`window_days` — не серверный, а клиентский фильтр: незавершённые дела в окне
всегда, завершённые/сброшенные — только если их `when` попадает в
`±window_days` от сегодня. Дело, которое **изменилось, находясь вне текущего
окна**, и которое не поймал вебхук, `TodoSync` не найдёт — ни в этот опрос,
ни в следующие, пока окно не расширят настолько, чтобы это дело снова в него
попало. Это не баг, а прямое следствие того, что серверного фильтра "что
изменилось" для `Todo` не существует: `TodoSync` может либо пройти весь
список целиком (дорого при большом окне), либо ограничить себя окном ценой
этого слепого пятна. Если вашему сценарию нужна гарантия "ничего не
пропущено" без ограничения по времени — полагайтесь на вебхуки как основной
канал, а `TodoSync` используйте только для восстановления после сбоев в
пределах разумного окна.

## Итоговая схема

1. Подписка на поток событий приложения, обработчик как выше — основной
   канал, обрабатывает изменения в реальном времени.
2. `TodoSync.poll()` — периодически (например, раз в час) как страховка на
   случай пропущенных вебхуков, и один раз при первом подключении интеграции
   для начальной загрузки.
3. При `looks_truncated=True` — не трогать `deleted`, просто повторить опрос
   позже.
4. Дела вне `window_days` без активности — вне досягаемости `TodoSync`;
   расширяйте окно, если это релевантно вашему сценарию.

См. также: [рецепт по отслеживанию связей сущностей](link-tracking.md).
