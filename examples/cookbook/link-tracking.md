# Кукбук: отслеживание связей сущностей (кто и когда привязал что к чему)

Вы хотите узнавать, когда сделку связали с другой сделкой или с задачей (или
когда связь убрали) — без опроса "проверить всё заново и сравнить". В API v3
для этого нет вебхука, но есть недокументированный, но стабильный путь через
журнал сущности. Этот рецепт — про него.

## Почему вебхука на link/unlink нет

Поток событий приложений несёт только три типа события:
`on_after_create`, `on_after_update`, `on_after_drop`
(<https://dev.megaplan.ru/apps/events.html>). Отдельного события "связь
добавлена" или "связь снята" в API v3 не существует. `on_after_update`
сработает при изменении сущности вообще, но не скажет, что именно
изменилось — уж тем более не скажет, что изменение было именно связью.

## Почему нельзя использовать API v1

Если вы искали `saveRelation`/`removeRelation` или поле `RelatedObjects` —
это методы **API v1**, и в API v3 их нет вообще. Второе частое заблуждение:
поле `relationLinks` у сделки (и счётчик `relationLinksCount`) — это не про
связи между сущностями, а про **упоминания-ссылки** в тексте (когда одна
сущность упоминает другую через `@`-ссылку в описании или комментарии).
Отдельный эндпоинт `GET /deal/{id}/relationLinks`, который могло бы показаться
логичным попробовать, не существует — сервер отвечает `404`.

## Где на самом деле виден факт связи: `BasedOnHistory`

Журнал сущности (`get_history()`) содержит не только `Changeset` (изменения
полей), но и недокументированный тип записи `BasedOnHistory` — именно он
пишется при каждом связывании и развязывании:

```python
{
    "id": 1096,
    "timeCreated": {"contentType": "DateTime", "value": "..."},
    "basedModel": {"contentType": "Deal", "id": 219},
    "generatedModel": {"contentType": "Task", "id": 4102},
    "user": {"contentType": "Employee", "id": 7},
    "unlink": False,
    "description": "...",
}
```

`unlink=False` — связь создана, `unlink=True` — связь снята. Запись видна
**с обеих сторон связи**: и в журнале сделки `219`, и в журнале задачи
`4102`, каждая — от своего лица (`basedModel` — сторона, от которой связь
пошла, `generatedModel` — вторая сторона).

**Проверенный факт (стенд, задача 12/12b):** привязка (`unlink=False`)
появляется в журнале обеих сторон практически мгновенно — подтверждено
трижды. **Открытый вопрос:** отвязка через API (`Task.deals = []`) в трёх
прогонах ни разу не дала `unlink=True`-запись ни на одной из сторон за
время ожидания (до 36 с). Причина не установлена — либо задержка журнала
для этого типа записи существенно больше, чем для привязки, либо очистка
поля не эквивалентна серверному действию «отвязать» через UI (где
`unlink=True` встречается регулярно). Если вам нужно надёжно ловить именно
отвязку, не полагайтесь на быстрый `get_link_events()` — сверяйте текущее
состояние (`get_linked_tasks()`/`get_linked_deals()`) между двумя срезами.

В SDK это поднято в типизированную модель `LinkEvent` и метод
`get_link_events(entity_id, since_id=...)` — он есть на всех пяти
сущностях, где сервер вообще пишет журнал: сделки, задачи, проекты,
контрагенты, дела.

```python
"""Incremental polling of link changes, by cursor, on several entity types."""

from __future__ import annotations

from megaplan_sdk import MegaplanClient
from megaplan_sdk.models.history import LinkEvent


async def poll_deal_links(client: MegaplanClient, deal_id: int, since_id: int | None) -> int:
    """Poll link changes for a deal, returning the new cursor to store."""
    events: list[LinkEvent] = await client.deals.get_link_events(deal_id, since_id=since_id)
    for event in events:
        verb = "отвязал" if event.unlink else "привязал"
        print(f"{event.time.value if event.time else '?'}: {verb} "
              f"{event.other.content_type}#{event.other.id} (via {event.user})")

    if not events:
        return since_id or 0
    return max(event.id for event in events if event.id is not None)


# The same method exists on the other four resources with journal access:
#   client.tasks.get_link_events(task_id, since_id=...)
#   client.projects.get_link_events(project_id, since_id=...)
#   client.contractors.get_link_events(contractor_id, since_id=...)
#   client.todos.get_link_events(todo_id, since_id=...)
```

Курсор здесь — просто наибольший `id` записи журнала, который вы уже
обработали; `id` растёт монотонно, так что `since_id` — обычный инкрементальный
опрос без риска пропустить запись между вызовами (кроме одновременных с
самим опросом — как и любой курсорный опрос).

**Не берите `events[0]` как «последнее событие».** На боевом стенде порядок
подтверждён эмпирически как «сначала новые» (по убыванию `timeCreated`), но
метод не передаёт `sort_by` — это дефолтный порядок сервера, не
задокументированный контракт API. Используйте `max(event.id for event in
events)` (как в примере выше), а не индекс `[0]`/`[-1]`, — так код не
сломается, если сервер когда-нибудь изменит порядок ответа.

## Почему нельзя серверно отфильтровать "только связи"

Соблазн — попросить у журнала сразу только записи о связях. Не выходит:
серверный фильтр `filters=["BasedOnHistory"]` отвечает `422` — сервер не
принимает этот тип как значение фильтра. Работают только `Self` и `Item`,
причём `Self` как раз **исключает** записи `BasedOnHistory` из выдачи
(значит, если вы уже используете `filters=["Self"]` для журнала где-то ещё,
записи о связях туда и не попадут). Поиск по журналу (`history/search`) тоже
не индексирует эти записи отдельно. Итог: фильтрация по типу записи —
целиком на стороне клиента, `get_link_events()` уже делает это за вас
(отбирает `BasedOnHistory` из общего потока журнала и заворачивает в
`LinkEvent`).

## Текущее состояние связей — без истории

Если вам не нужна история изменений, а нужен снимок "что сейчас с чем
связано" — не читайте журнал, читайте подресурсы карточки напрямую:

```python
"""Current link state, without touching the journal."""

from __future__ import annotations

from megaplan_sdk import MegaplanClient


async def snapshot_deal_links(client: MegaplanClient, deal_id: int) -> None:
    linked_deals = await client.deals.get_linked_deals(deal_id)
    linked_tasks = await client.deals.get_linked_tasks(deal_id)
    actual_tasks = await client.deals.get_actual_linked_tasks(deal_id)
    print(len(linked_deals), len(linked_tasks), len(actual_tasks))
```

Для веера сделок — не гонять `get_linked_deals()` в цикле (N запросов), а
использовать `get_linked_deals_many()`: он собирает вызовы в один HTTP-запрос
через `POST /api/v3/bulk`.

```python
"""Linked deals for many deals in one HTTP round trip."""

from __future__ import annotations

from megaplan_sdk import MegaplanClient
from megaplan_sdk.models.deal import Deal


async def links_for_portfolio(client: MegaplanClient, deal_ids: list[int]) -> dict[int, list[Deal]]:
    # One POST /api/v3/bulk instead of len(deal_ids) separate requests.
    # Deals that failed the sub-call (no access, deleted) are simply
    # omitted from the result rather than reported as "no links".
    return await client.deals.get_linked_deals_many(deal_ids)
```

Для произвольных наборов запросов, которых нет как готового `*_many()`
метода, есть общий `client.bulk()` — тот же транспорт, без обёртки под
конкретную сущность:

```python
"""Ad-hoc batching through client.bulk() when no *_many() wrapper exists."""

from __future__ import annotations

from megaplan_sdk import MegaplanClient


async def bulk_linked_deals(client: MegaplanClient, deal_ids: list[int]) -> None:
    results = await client.bulk(
        [{"method": "GET", "url": f"/api/v3/deal/{i}/linkedDeals"} for i in deal_ids]
    )
    for result in results:
        if result.is_success:
            print(result.status, len(result.data or []))
```

## Итоговая схема

- **Текущее состояние** связей — подресурсы (`get_linked_deals()` и т.п.),
  для многих сущностей разом — `get_linked_deals_many()` / `client.bulk()`.
- **Кто и когда связал/отвязал** — журнал через `get_link_events(entity_id,
  since_id=...)`, курсор — наибольший увиденный `id`. Работает на сделках,
  задачах, проектах, контрагентах и делах. Привязка видна мгновенно с обеих
  сторон (подтверждено); отвязка через API — открытый вопрос, см. выше.
- Вебхука на сам факт связи нет — `on_after_update` в потоке событий можно
  использовать только как триггер "в сущности что-то изменилось, имеет смысл
  сверить журнал", не как источник самого факта связи.

См. также: [рецепт по инкрементальной синхронизации дел](todo-sync.md).
