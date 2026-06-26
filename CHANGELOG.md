# Журнал изменений

Все значимые изменения в этом проекте будут документироваться в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и этот проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [Не выпущено]

## [0.4.0] — 2026-06-25

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