# Журнал изменений

Все значимые изменения в этом проекте будут документироваться в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и этот проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [Не выпущено]

## [0.6.0] — 2026-08-07

### ⚠️ Изменения поведения (breaking)
- `list()`/`iterate()` с `expand=` больше не возвращают `*FullDetails`.
  Загруженные сущности подставляются вместо голых ссылок на иммутабельных
  копиях, тип не меняется: `deals.list(expand=["manager"])` → `list[Deal]`,
  где `deal.manager` — полный `Employee` (#BUG-2).
  Миграция: `deal_full.manager_details` → `deal.manager`,
  `task_full.task` → сам `task`. `get_full_details()` не изменился.
- `deals.get_history()` возвращает типизированные записи (`Changeset`,
  `BasedOnHistory`) вместо сырых `dict`; неизвестные типы остаются `dict`.
  Прежнее поведение — `get_history(..., raw=True)`.
- `Employee.birthday` — модель `DateOnly` вместо `dict` (#FR-G).
  Миграция: `emp.birthday["month"]` → `emp.birthday.month`, плюс
  `emp.birthday.date` → `datetime.date | None`.
- Удалено предупреждение о серверной дедупликации ссылок (#36): SDK теперь
  дозаполняет повторные ссылки сам, советовать обход больше нечего.

### Добавлено
- `client.notifications` — ресурс уведомлений (#FR-F): `list()`/`iterate()` с
  флагом `is_mention`, `counter()`, `activity_types()`. Модель `Notification`
  с `entity_ref` (разбор ссылки на сущность из HTML) и `subject_comment`.
  Сервер принимает только `isActive` и пагинацию, поэтому `only_mentions`
  фильтрует на клиенте, а в `iterate()` — после пагинации.
- `client.raw(method, path, query=, json=)` — вызов эндпоинтов без ресурса с
  авторефрешем токена, ретраями и разбором `meta.errors` (#BUG-1). Транспорт
  был исправен и раньше: `_http.get(path, {"limit": 60})` сам строит
  `?{"limit": 60}` — литерал руками собирать не нужно.
- `client.bulk(calls=[...])` над `POST /api/v3/bulk` и
  `deals.get_linked_deals_many()` — N вызовов одним HTTP-запросом (#FR-E).
  Порядок ответов сохраняется, статус у каждого вызова свой.
- Связи сделок: `get_linked_deals()`, `get_linked_tasks()`,
  `get_actual_linked_tasks()`, `get_based_on_linked_deals()`.
- `deals.get_link_events(deal_id, since_id=, since_time=)` — кто, когда и какую
  связь добавил или удалил, без сравнения двух состояний сделки. Вебхука на
  связи в API нет, карточка отдаёт только счётчики, но журнал пишет
  `BasedOnHistory` с флагом `unlink`.
- `deals.iterate_history()` — автопагинация по журналу.
- Модели журнала: `Changeset`, `FieldChange`, `BasedOnHistory`, `LinkEvent`.
- `normalize_state_name()` — нормализация имён состояний (эмодзи, регистр,
  пробелы) для сравнения (#NOTE-2).

### Исправлено
- `deals.get_full_details(include_related_tasks=True)` больше не бросает
  `NotImplementedError`: задачи читаются из `/deal/{id}/linkedTasks`. Фильтра
  tasks-by-deal по-прежнему нет, но подресурс отдаёт ровно задачи из
  `tasksCount` (проверено на стенде).
- Повторные ссылки (`owner`/`responsible`/`manager`/`contractor`), которые
  сервер дедуплицирует в пределах одного ответа, дозаполняются из полного
  вхождения в том же ответе — в том числе из другого поля другой записи
  (#BUG-4). Ни словарь `{id: name}`, ни `expand=` для этого больше не нужны.
- `deals.list(fields=[...])` проверяет поля на клиенте и объясняет ошибку
  вместо сырого 422 (#BUG-3). Отвергаемые сервером имена сняты со стенда:
  `deadline`, `responsible`, `createdAt`, `updatedAt`.

### Известные ограничения
- Загрузка вложений (`attachments.upload`, #FR-D) и ресурс `client.todos`
  (#NOTE-1) перенесены в 0.6.1 — обе требуют write-проверок на стенде.
- Вехи у сделок невозможны: `GET /api/v3/deal/{id}/milestones` → 404,
  `GET /api/v3/milestone` → 405 (только POST).

## [0.5.0] — 2026-07-16

### ⚠️ Изменения поведения (breaking)
- `auth.authenticate()`, `auth.refresh_token()` и `MegaplanClient.authenticate()`
  возвращают модель `AuthTokenResponse` (`access_token`, `refresh_token`,
  `expires_in`, `token_type`) вместо `str` (#FR-A, #FR-B).
  Миграция: `token = await mp.auth.refresh_token(...)`; используйте
  `token.access_token` и сохраняйте `token.refresh_token` — сервер ротирует его
  при каждом refresh.
- Удалены deprecated-обёртки `tasks.create_comment()`, `deals.create_comment()`,
  `projects.create_comment()` — как и было анонсировано в 0.4.2. Используйте
  `client.comments.create(entity_id=..., content=..., entity_type=...)`.

### Добавлено
- `client.attachments` — скачивание вложений: `download(attach) -> bytes` и
  `stream(attach)` для больших файлов (#FR-C).
- `comments_count` на `Task`/`Deal`/`Project` и во всех `*FullDetails`;
  `get_full_details` заказывает `commentsCount` на карточке, признак усечения:
  `len(details.comments) < details.comments_count` (#34).
- `get_full_details(..., resolve_participants=True)` — `auditors`/`executors`
  резолвятся в полные `Employee` батчем через кэш по умолчанию (#35).
- `tasks.get()`/`deals.get()`/`projects.get()` принимают `fields=[...]`.

### Изменено
- `list()` логирует warning при серверной дедупликации связанных полей,
  заказанных через `fields=` (owner/responsible/manager/contractor), с
  подсказкой использовать `expand=` (#36).

## [0.4.3] — 2026-07-02

Релиз по итогам повторной регрессии баг-репорта 0.4.2 на живом стенде:
пять записей отчёта отозваны как устаревшие (уже исправлены в 0.4.1),
реальные остатки закрыты здесь.

### Добавлено
- **`tasks.get_full_details(expand_comment_owners=True)`** — резолв
  авторов комментариев в полные объекты `Employee` одним батчем
  параллельных кэшируемых запросов (#30). API никогда не заполняет
  `owner` у комментариев, поэтому раньше `include_comments=True`
  оставлял голые ссылки `{contentType, id}`. Флаг opt-in: без
  `include_comments=True` кидает `ValueError` (fail-fast как у
  `*_limit`). Симметричный sugar `comments.list(entity_id,
  expand_comment_owners=True)` эквивалентен `expand=["owner"]`.
- **Валидация `fields` для задач (#32).** Синонимы полей из других
  CRM-API (`timeUpdated`, `updatedAt`, `updated_at`, `dateUpdated`,
  `createdAt`, `created_at`, `dateCreated`) перехватываются на клиенте
  с подсказкой реальных полей Task (`statusChangeTime`,
  `lastCommentTimeCreated`, `activity`, `timeCreated`) вместо сырого
  серверного 422 «Task have not this fields». Работает в
  `tasks.list()`, `tasks.iterate()` и `TaskQuery.fields()`.
  Неизвестные и кастомные поля категорий по-прежнему проходят —
  чёрный список, а не белый (модель не может служить allowlist:
  она наследует отвергаемый сервером `timeUpdated` и не описывает
  все легитимные поля).

### Исправлено
- **`details.owner` после `expand=` возвращал сырую ссылку с
  `name=None` (#25).** Списочный API встраивает повторяющуюся
  связанную сущность полностью только при первом вхождении, дальше —
  голый `{contentType, id}`; при этом результат expand лежал только в
  `owner_details`/`responsible_details`. Теперь у контейнеров
  `*FullDetails` есть явные свойства, предпочитающие загруженную
  сущность сырой ссылке: `owner`/`responsible` у
  `TaskFullDetails`/`ProjectFullDetails`, `manager`/`contractor` у
  `DealFullDetails`. Сырая ссылка доступна через `details.task.owner`
  и аналоги.

## [0.4.2] — 2026-07-02

Архитектурный релиз: углубление модулей по итогам ревью (кандидаты 1–7)
плюс исправления, найденные при эмпирической проверке API на стенде.

### ⚠️ Изменения поведения (breaking)
- **`deals.get_full_details(include_related_tasks=True)` теперь кидает
  `NotImplementedError`.** Проверка на стенде показала, что у API нет
  рабочего фильтра «задачи по сделке»: объектные варианты baseOn тихо
  игнорируются (эндпоинт возвращает ВСЕ задачи аккаунта), строковые —
  422; сервер явно сообщает, что у Task нет полей deal/trade/baseOn.
  Старая реализация молча возвращала несвязанные задачи.
- `HTTPClient.post_form()` возвращает `dict` (разобранный JSON) вместо
  сырого `httpx.Response` и транслирует транспортные ошибки в
  `AuthenticationError`.
- `deals.add_auditor()` шлёт полную ссылку `{id, contentType}`
  (проверено на стенде); `deals.get_auditors()` возвращает `list[Any]`
  через общий базовый хелпер (та же форма, что у tasks/projects).

### Добавлено
- **`Page`** — тип позиции страницы: `tasks.list(page=Page(after=100))`
  вместо тройки `page_after/page_before/page_with` (легаси-параметры
  остаются). Неоднозначные комбинации (after+before) невыразимы.
- **`TaskQuery`** и **`tasks.list_by(query)`** — флюент-запрос списка
  задач с валидацией при построении: search()+filter() взаимоисключающие,
  статусы и поля сортировки проверяются сразу, недоступные для поиска
  поля отклоняются, `with_time_fields()` включает поля дат (#8),
  `unsorted()` отключает дефолтную сортировку (#14).
- `AuthManager.restore_token()` — публичное восстановление токена.
- `HTTPClient.open()` — публичное открытие пула соединений (пара к
  `close()`).

### Исправлено
- Нерегулярность API при удалении аудитора сделки: рабочий путь —
  `DELETE /deal/{id}/auditors/{auditorId}` без contentType (у задач и
  проектов — с contentType); старый вариант возвращал 404.
- Маппинг фильтров: camelCase-типы (`fileStorage`, `customCrm`) давали
  неверный путь (`filestorageFilter`) из-за приведения к нижнему
  регистру — записи таблицы были недостижимы.
- `expand` у `employees.list()` больше не мутирует объекты — поля
  заменяются на иммутабельных копиях (публичный контракт не изменился).
- `NotImplementedError` из фетчеров `get_full_details` пробрасывается
  наружу, а не деградирует в `None` с warning в логе.

### Устарело (удаление в 0.5.0)
- `tasks.create_comment()`, `deals.create_comment()`,
  `projects.create_comment()` — используйте
  `client.comments.create(entity_id=..., content=..., entity_type=...)`.

### Внутреннее (архитектура)
- Декларативный конвейер expand: `ExpandRule` + один движок
  `_expand_and_wrap` в BaseResource вместо четырёх копий по ресурсам.
- Единый реестр имён API (`registry.py`): contentType, типы фильтров и
  алиасы (`todo`→task, `trade`→deal) в одном месте; обе легаси-таблицы
  делегируют ему.
- Швы уплотнены: httpx исчез из auth-модуля, клиент не трогает приватные
  поля коллабораторов, формат хранения кэша решается только в
  `_cache_get`/`_cache_put`.
- Тестовая инфраструктура: адаптер `megaplan_api` (respx + конверт
  meta/data) и фабрики ресурсов в conftest; все ресурсные тесты
  мигрированы (−1600 строк шаблонного кода).

## [0.4.1] — 2026-06-26

### ⚠️ Изменения поведения (breaking)
- **#16** `Comment.work_time` и `Comment.work_date` теперь типизированы
  (`DateInterval | None` и `DateTime | None`) вместо сырых `dict`. Доступ
  `comment.work_time["value"]` больше не работает — используйте
  `comment.work_time.value` (плюс `.seconds` / `.minutes` / `.hours`).
- **#26 / #27** Параметры `department_id` и `status` убраны из сигнатуры
  `employees.list()` — сервер их не поддерживает (422). Теперь любая попытка
  серверной фильтрации сотрудников (`filter` / `q` / `department_id` /
  `status`) кидает `NotImplementedError` с подсказкой фильтровать на клиенте.
- **#28** Параметр `filter` убран из сигнатуры `employees.list()` (он только
  кидал `NotImplementedError` — типизация была лживой).

### Fixed
- **#21** `tasks.create_comment(work=N)` больше не теряет трудозатраты: раньше
  поле сериализовалось как `{"seconds": ...}` (сервер молча писал 0), теперь
  — корректный `{"value": int(work * 3600)}`. **#22** Метод стал тонкой
  обёрткой над `comments.create`, поэтому naming и поведение `work` едины.
- **#24** `tasks.iterate()` теперь пробрасывает `fields` / `sort_by` /
  `expand` / `q` в `list()` (раньше итерация возвращала задачи без
  `time_created`).
- **#25** `TaskFullDetails` / `DealFullDetails` / `ProjectFullDetails`
  делегируют доступ к полям вложенной сущности, поэтому `tasks.list(expand=…)`
  больше не ломает `task.owner` — работают и `details.task.owner`, и
  `details.owner`.
- **#29** `FilterBuilder.field('x').equals(True/5)` теперь строит
  `FilterTermBool` / `FilterTermNumber` (как `field_eq`), а не отвергаемый
  сервером `FilterTermString`.
- **#15** Документация по единицам `work`: параметр — отработанное время **в
  часах** (`work=2.5` ⇒ 2 ч 30 мин), сериализуется как `value = int(work *
  3600)` секунд. Прежняя формулировка release notes («`value` в секундах»)
  вводила в заблуждение.

### Changed
- **#17** `comments.get()` и `comments.delete()` принимают (и игнорируют)
  `entity_type` — единый стиль с `list` / `create`.
- **#23** `page_after` / `page_before` / `page_with` теперь принимают `int`
  (id), Pydantic-модель или dict и сами оборачивают значение в entity-link
  `{contentType, id}`, который требует сервер.
- **#19** В docstring `comments.delete()` добавлено предупреждение, что на
  большинстве инсталляций Megaplan удаление комментариев запрещено политикой
  (403) даже автору.
- Документация: примеры комментариев в README и `examples/cli_app`
  переведены на `content=` вместо устаревшего `comment_data={"text": …}`
  (D-1 / D-2); добавлены заметки про `employees.get_current()`,
  статус-поля `Employee` и делегаты `KnowledgeSectionWithArticles`.

### Added
- `DateInterval` экспортируется из `megaplan_sdk` (модель интервала с
  `.value` / `.seconds` / `.minutes` / `.hours`).

## [0.4.0] — 2026-06-26

### ⚠️ Изменения поведения (breaking)
- **#14** `tasks.list()` / `deals.list()` без `sort_by` теперь сортируют по
  `timeCreated DESC` (как в UI Мегаплана). Раньше порядок был не определён.
  Отключить: `sort_by=[]`. Добавлена константа `DEFAULT_SORT_RECENT`.
- **#11** Параметр `q` у `tasks.list()` / `deals.list()` теперь
  преобразуется в серверный фильтр по полю `name` (раньше молча
  игнорировался и возвращал 0). `q_in=["name","statement"]` расширяет поиск;
  `description`/`subject` недоступны на сервере → `NotImplementedError`.

### Added
- **#FR-1** `tasks.get_many(ids)` / `deals.get_many(ids)` — батч-загрузка
  через `POST /api/v3/bulk/getEntitiesByLinks`, возвращают `dict[id -> сущность]`.
  `employees.get_many(ids)` — через параллельные одиночные get (bulk 500 для
  Employee). Сырой bulk-эндпоинт намеренно не публичный.
- **#9** Типизированный `comments.create(entity_id, *, content=..., work=...,
  attaches=...)`. Dict-форма `comment_data=` помечена deprecated.
- **#13** В модель `Employee` добавлены `is_working` / `fire_in_progress` /
  `can_login`.

### Changed / Fixed
- **#13** `employees.list(filter=...)` / `list(q=...)` теперь кидают
  `NotImplementedError` (сервер молча игнорирует фильтр на `/employee`).
- **#12** `KnowledgeSectionWithArticles` получил делегаты `id`/`name`/
  `content`/`last_updated` → ведёт себя как обычный `get`.
- **#10** `employees.get("me")` кидает понятный `ValueError` с указанием на
  `get_current()` (раньше — мутный 405).
- **#9** Исправлен docstring `comments.create` (`text` → `content`).

## [0.3.0] — 2026-06-21

### Добавлено
- Ресурсы Базы знаний: `client.knowledge_base` (`get` / `list` / `iterate`) и
  `client.knowledge_article` (`get`). Модели `KnowledgeBase`, `KnowledgeArticle`,
  `KnowledgeSectionWithArticles` экспортируются из `megaplan_sdk` (журнал #6).
- Экспериментальный helper `knowledge_base.get_with_articles(section_id)` —
  дискавери статей раздела через парсинг HTML-ссылок в `content` с кросс-проверкой
  по `KnowledgeArticle.base.id`.

### Известные ограничения (серверная сторона API)
- `GET /api/v3/knowledgeArticle` отсутствует (404) — нативного листинга статей нет
  (журнал #5); дискавери только через `get_with_articles` (парсинг HTML, хрупко).
- Фильтр `parent` на `GET /api/v3/knowledgeBase` игнорируется, а разделы плоские —
  иерархии разделов нет (журнал #4). Реальная связь — раздел → статьи через
  `KnowledgeArticle.base` (поле `parent` у статьи всегда `null`).

## [0.2.3] — 2026-06-21

### Исправлено
- `client.comments.create/list/iterate` теперь принимают `entity_type` (default `"task"`)
  и строят путь `/api/v3/<entity_type>/<id>/comments` вместо хардкода `/todo/` —
  убран тихий 404 для комментариев задач (журнал #1).
- `get_full_details` теперь кидает `ValueError`, если передан `comments_limit`/`history_limit`
  без соответствующего `include_*=True`, вместо тихого игнорирования (журнал #2).

### Добавлено
- В модель `Task` добавлены временные поля: `activity`, `last_comment_time_created`,
  `status_change_time`, `actual_start`, `last_view` (журнал #7).
- Понятная ошибка вместо сырого 422 при `tasks.list(sort_by=[{"fieldName": "timeUpdated"}])`
  с подсказкой использовать `activity` (журнал #7).
- Экспортируемая константа `DEFAULT_TASK_LIST_FIELDS` для запроса date-полей в `tasks.list`,
  плюс предупреждение в документации (журнал #8).
- `comments.list(expand=["owner"])` — батч-подгрузка авторов-сотрудников с кэшированием (журнал #3).

### Известные ограничения (серверные / отложено)
- Эндпоинт `/api/v3/task/<id>/comments` не раскрывает `owner` ни при каком `fields`/`expand` —
  это поведение API Мегаплана. SDK обходит через `expand=["owner"]` (доп. запросы, кэшируются).
  Однозапросный батч `employees.list(filter={"id":[...]})` возможен после проверки фильтра по id на API.
- Knowledge Base (`knowledgeBase`/`knowledgeArticle`): фильтр `parent` игнорируется сервером,
  публичного листинга статей нет (журнал #4/#5). Ресурсы SDK для KB запланированы в 0.3.0 (журнал #6).

## [0.2.2] - 2026-03-28

### Исправлено

- **[КРИТИЧНО]** Модель `Deal`: поле `responsible` переименовано в `manager` — теперь корректно соответствует полю `manager` в ответах Megaplan API (старое поле всегда возвращало `None`)
- **[КРИТИЧНО]** Модель `Deal`: поле `sum_base` (alias `sumBase`) заменено на `price: Money` — API возвращает объект `Money`, а не число
- **[КРИТИЧНО]** Модели `Deal`, `Project`, `Task`: поля `created_at`/`updated_at` (alias `createdAt`/`updatedAt`) переименованы в `time_created`/`time_updated` с алиасами `timeCreated`/`timeUpdated` — приведено в соответствие с реальными именами полей API
- **[КРИТИЧНО]** `DealsResource.list(fields=[...])`: параметр `fields` теперь документирован с реальными именами полей API (`manager`, `price`, `timeCreated` и др.), что предотвращает HTTP 422 ошибки при передаче старых имён

### Добавлено

- Модель `Money` (`contentType`, `currency`, `value`, `value_in_main`, `rate`) для корректного парсинга денежных полей API
- Новые поля в модели `Deal`: `number`, `short_description` (alias `shortDescription`), `cost: Money`, `debt: Money`, `result`, `state_time_updated` (alias `stateTimeUpdated`)
- Поле `name: str | None` в `BaseEntity` — API часто возвращает имена в ссылочных объектах, теперь они доступны (напр. `deal.program.name`)
- Параметр `filter` в `ProjectsResource.list()` и `ProjectsResource.iterate()` — `ProjectFilterBuilder` теперь полностью подключён к ресурсу проектов
- `Money` экспортируется из `megaplan_sdk` в `__all__`

### Изменено

- Все модели SDK: `extra="ignore"` → `extra="allow"` — неизвестные поля из API сохраняются в `model_extra` вместо молчаливого удаления, что обеспечивает прямую совместимость и помогает диагностировать несоответствия
- `DealFullDetails.responsible_details` переименовано в `manager_details` (соответствует переименованию `Deal.responsible` → `Deal.manager`)
- `DealsResource.get_full_details()`: параметр `include_responsible_details` переименован в `include_manager_details`
- `DealsResource.list(expand=...)`: поле `"responsible"` в expand заменено на `"manager"`

### BREAKING CHANGES

| Старое | Новое |
|--------|-------|
| `deal.responsible` | `deal.manager` |
| `deal.sum_base` | `deal.price` (тип `Money`) |
| `deal.created_at` / `deal.updated_at` | `deal.time_created` / `deal.time_updated` |
| `project.created_at` / `project.updated_at` | `project.time_created` / `project.time_updated` |
| `task.created_at` / `task.updated_at` | `task.time_created` / `task.time_updated` |
| `DealFullDetails.responsible_details` | `DealFullDetails.manager_details` |
| `get_full_details(include_responsible_details=...)` | `get_full_details(include_manager_details=...)` |
| `deals.list(expand=["responsible", ...])` | `deals.list(expand=["manager", ...])` |

## [0.2.1] - 2026-02-02

### Добавлено

- Поддержка HTTP/HTTPS/SOCKS5 прокси через параметр `proxy` в `MegaplanClient`
- Метод `get_deals()` для контрагентов — получение сделок контрагента через эндпоинт `GET /contractor/{id}/deals`
- Методы `get_available_parents()` и `get_available_parents_for()` для задач — получение доступных надзадач и надпроектов
- Методы `get_available_parents()` и `get_available_parents_for()` для проектов — получение доступных родительских проектов
- Метод `get_all_participants()` для задач, проектов и сделок — получение всех участников сущности одним запросом
- Модель `Group` — группа участников (отдел, роль)
- Union type `Participant` и функции `parse_participant()`, `parse_participants()` для парсинга участников

## [0.2.0] - 2026-01-11

### Добавлено

- Типизированная поддержка Milestones для задач и проектов (модель `Milestone`, методы `get_milestones()` и `add_milestone()`)
- Универсальная работа с фильтрами через FilterBuilder с fluent API (TaskFilterBuilder, TradeFilterBuilder, поддержка всех типов FilterTerm)
- Нормализация BaseEntity объектов (автоматическая конвертация строковых ID в int для параметров пагинации и baseOn)
- Валидация статусов задач через `VALID_TASK_STATUSES`
- Улучшения метода `check_exists()` для сделок (поддержка множественных параметров, нормализация BaseEntity)
- Утилиты валидации для интеграционных тестов
- Реорганизация интеграционных тестов (read_only/ и write/)

### Изменено

- Реорганизация README.md (оглавление, раздел "Общие паттерны", устранение дублирования ~800 строк)
- Улучшена безопасность (убрано логирование username, приватный access_token)
- Оптимизирован EntityCache (отслеживание типов через defaultdict)

### Исправлено

- Исправлена обработка Milestones API (опциональный id, обход ошибки 500, корректный формат DateTime)
- Исправлена нормализация BaseEntity объектов
- Исправлены ruff предупреждения UP038

### Улучшено (Рефакторинг)

- Устранены нарушения DRY (generic методы для milestones, сокращено ~160 строк кода)
- Упрощение кода KISS (`_normalize_base_entity()` -29%, `check_exists()` -16%, чистая функция `_normalize_datetime_field()`)
- Удален мёртвый код (неиспользуемые параметры пагинации в get_milestones(), ContractorsResource.delete())
- Применены замечания разработчика (ruff предупреждения, чистая функция, упрощение методов)

### Удалено

- Исключена директория docs/ из репозитория

## [0.1.0] - 2026-01-08

### Добавлено

- Основной клиент `MegaplanClient` с поддержкой async context manager
- OAuth2 авторизация с автоматическим обновлением токенов
- HTTP клиент с автоматическими повторами при ошибках сервера (5xx)
- Кэширование сущностей с LRU-алгоритмом и TTL
- Автоматическая подгрузка связанных сущностей через параметр `expand`
- Ресурсы API: задачи, проекты, сделки, сотрудники, контрагенты, отделы, комментарии
- Метод `get_full_details()` для задач, проектов и сделок с параллельной загрузкой связанных данных
- Типобезопасные модели на базе Pydantic v2 для всех сущностей
- Автоматическая пагинация через метод `iterate()`
- Иерархия исключений для обработки ошибок API
- Логирование с настраиваемым уровнем
- Полная типизация с поддержкой mypy strict mode
- Helper-функции для создания BaseEntity объектов (`make_entity`, `make_employee_entity`, `make_project_entity`, `make_task_entity`, `make_deal_entity`, `make_contractor_entity`)
- Комплексные unit-тесты для всех компонентов SDK (покрытие 80%+)
  - Тесты для FullDetailsMixin (8 тестов)
  - Тесты для EntityCache (9 тестов)
  - Тесты для BaseResource (13 тестов)
  - Тесты для expand-логики (8 тестов)
  - Тесты для обработки ошибок (7 тестов)
  - Интеграционные тесты (4 теста)