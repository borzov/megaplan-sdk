# Журнал изменений

Все значимые изменения в этом проекте будут документироваться в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и этот проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [Не выпущено]

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