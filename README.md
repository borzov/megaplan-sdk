# Megaplan Python SDK

[![Python versions](https://img.shields.io/pypi/pyversions/megaplan-sdk)](https://pypi.org/project/megaplan-sdk/)
[![PyPI version](https://badge.fury.io/py/megaplan-sdk.svg)](https://pypi.org/project/megaplan-sdk/)
[![Tests](https://github.com/borzov/megaplan-sdk/actions/workflows/tests.yml/badge.svg)](https://github.com/borzov/megaplan-sdk/actions/workflows/tests.yml)
[![Coverage](https://codecov.io/gh/borzov/megaplan-sdk/graph/badge.svg)](https://codecov.io/gh/borzov/megaplan-sdk)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/charliermarsh/ruff)

Профессиональная Python-библиотека для работы с API Мегаплана версии 3.

## О проекте

Современная библиотека для интеграции с CRM Мегаплан. Она предоставляет удобный и типобезопасный интерфейс для работы с задачами, проектами, сделками и другими сущностями через REST API.

### Зачем нужна эта библиотека?

Работа с API Мегаплана напрямую требует знания множества технических деталей: правильной настройки OAuth2-авторизации, обработки токенов, формирования JSON-параметров в query string, обработки ошибок и пагинации. Эта библиотека берет на себя всю рутинную работу, позволяя разработчикам сосредоточиться на бизнес-логике.

### Преимущества использования SDK

Вместо прямых HTTP-запросов вы получаете простой и понятный Python-интерфейс. Вместо ручной работы с токенами — автоматическую авторизацию и обновление токенов. Вместо парсинга JSON-ответов — типизированные Pydantic-модели с автодополнением в IDE. Вместо обработки ошибок вручную — понятные исключения с детальной информацией.

Библиотека полностью асинхронная, что позволяет эффективно работать с большими объемами данных и выполнять параллельные запросы. Встроенная логика повторных попыток при временных сбоях сервера делает интеграцию более надежной. Модульная архитектура позволяет легко расширять функциональность и добавлять поддержку новых модулей API.

## Содержание

### Основы
- [Быстрый старт](#быстрый-старт)
- [Авторизация](#авторизация)
- [Helper-функции](#helper-функции)
- [Обработка ошибок](#обработка-ошибок)

### Работа с сущностями
- [Общие паттерны](#общие-паттерны-работы-с-сущностями)
- [Задачи](#работа-с-задачами)
- [Проекты](#работа-с-проектами)
- [Сделки](#работа-со-сделками)

### Продвинутые возможности
- [Кэширование сущностей](#кэширование-сущностей)
- [Глобальные дефолтные лимиты](#глобальные-дефолтные-лимиты)
- [Автоматическая подгрузка связанных сущностей](#автоматическая-подгрузка-связанных-сущностей)
- [Работа с фильтрами](#работа-с-фильтрами)
- [Настройка HTTP-клиента](#настройка-http-клиента)
- [Работа через прокси](#работа-через-прокси)
- [Ручное управление токенами](#ручное-управление-токенами)

### Справочная информация
- [Известные ограничения API](#известные-ограничения-api)
- [Архитектура](#архитектура)
- [Требования](#требования)
- [Разработка](#разработка)

## Возможности

- Полный CRUD для задач, проектов и сделок
- Метод `get_full_details()` — получение сущности со всеми связанными данными (комментарии, история, подзадачи и т.д.) за один вызов с параллельной загрузкой
- OAuth2-авторизация с автоматическим обновлением токенов
- Типобезопасность с Pydantic-моделями и полной типизацией
- Асинхронность — поддержка async/await во всех операциях
- Автоматические повторы при ошибках сервера (5xx)
- Кэширование сущностей с LRU и TTL для оптимизации запросов
- FilterBuilder для создания фильтров с fluent API
- Параметр `expand` для автоматической подгрузки связанных сущностей
- Метод `iterate()` для автоматической пагинации больших списков
- Helper-функции для создания BaseEntity объектов
- Глобальные дефолтные лимиты для комментариев и истории
- Модульная архитектура для легкого расширения
- Комплексные тесты с покрытием 80%+

## Установка

```bash
pip install megaplan-sdk
```

Или из исходников:

```bash
git clone https://github.com/borzov/megaplan-sdk.git
cd megaplan-sdk
pip install -e .
```

## Быстрый старт

```python
import asyncio
from megaplan_sdk import MegaplanClient

async def main():
    # Создание клиента с учетными данными
    async with MegaplanClient(
        base_url="https://my.megaplan.ru",
        username="user@example.com",
        password="your_password"
    ) as client:

        # Получение списка задач
        tasks = await client.tasks.list(limit=10)
        for task in tasks:
            print(f"Задача: {task.name}")

        # Получение конкретной задачи
        task = await client.tasks.get(task_id=42)
        print(f"Детали задачи: {task.name}, Статус: {task.status}")

        # Упрощенное создание задачи
        new_task = await client.tasks.create_simple(
            "Новая задача",
            employees_resource=client.employees
        )
        print(f"Создана задача: {new_task.name}")

        # Получение задачи со всеми связанными данными за один вызов
        details = await client.tasks.get_full_details(
            task_id=42,
            include_comments=True,
            include_sub_tasks=True,
            include_responsible_details=True
        )
        print(f"Комментариев: {len(details.comments) if details.comments else 0}")
        print(f"Подзадач: {len(details.sub_tasks) if details.sub_tasks else 0}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Авторизация

SDK поддерживает OAuth2-авторизацию. Вы можете передать учетные данные или использовать предварительно полученный токен доступа:

```python
# С логином и паролем (автоматическая авторизация)
client = MegaplanClient(
    base_url="https://my.megaplan.ru",
    username="user@example.com",
    password="password"
)

# С токеном доступа
client = MegaplanClient(
    base_url="https://my.megaplan.ru",
    access_token="your_access_token"
)
```

## Helper-функции

SDK предоставляет удобные функции для создания BaseEntity объектов:

```python
from megaplan_sdk import (
    make_employee_entity,
    make_project_entity,
    make_task_entity,
    make_deal_entity,
    make_contractor_entity,
)

# Вместо ручного создания {"contentType": "Employee", "id": 123}
employee_ref = make_employee_entity(123)
project_ref = make_project_entity(456)
task_ref = make_task_entity(789)
deal_ref = make_deal_entity(101)
contractor_ref = make_contractor_entity(202)
```

## Обработка ошибок

SDK предоставляет специфичные типы исключений для различных сценариев ошибок:

```python
from megaplan_sdk import (
    AuthenticationError,      # 401 - Ошибка аутентификации
    AuthorizationError,        # 403 - Ошибка авторизации (нет прав)
    NotFoundError,            # 404 - Ресурс не найден
    ValidationError,          # 422 - Ошибка валидации запроса
    RateLimitError,           # 429 - Превышен лимит запросов
    ServerError               # 5xx - Ошибка сервера
)

try:
    task = await client.tasks.get(task_id=999)
except NotFoundError:
    print("Задача не найдена")
except AuthenticationError:
    print("Ошибка аутентификации")
except ValidationError as e:
    print(f"Ошибки валидации: {e.errors}")
    # e.errors содержит список ошибок из API
```

## Общие паттерны работы с сущностями

Большинство сущностей (задачи, проекты, сделки) поддерживают одинаковые операции CRUD и паттерны работы. В этом разделе описаны общие методы, которые применяются ко всем типам сущностей.

### Базовые операции CRUD

Все ресурсы поддерживают стандартные операции:

#### Получение списка (`list`)

```python
# Общий формат для всех ресурсов
entities = await client.{resource}.list(
    limit=None,              # int: Количество элементов на странице
    page_after=None,        # dict: Загрузить страницу, начиная с этой сущности
    page_before=None,       # dict: Загрузить страницу строго до этой сущности
    page_with=None,         # dict: Загрузить страницу с наличием этой сущности
    fields=None,            # any: Набор дополнительных полей
    sort_by=None,           # list[dict]: Массив полей сортировки
    only_requested_fields=None  # bool: Отдавать только перечисленные поля
)
```

**Примеры:**
```python
# Получить все задачи
tasks = await client.tasks.list()

# Получить проекты с лимитом
projects = await client.projects.list(limit=50)

# Получить сделки с пагинацией
deals = await client.deals.list(limit=100, page_after={"contentType": "Deal", "id": 100})
```

#### Получение по ID (`get`)

```python
entity = await client.{resource}.get({resource}_id=42)
# Возвращает: объект сущности со всеми полями
```

**Примеры:**
```python
task = await client.tasks.get(task_id=42)
project = await client.projects.get(project_id=5)
deal = await client.deals.get(deal_id=200)
```

#### Создание (`create`)

```python
entity = await client.{resource}.create({resource}_data={
    "name": "Название",  # Обязательное поле
    # ... другие поля
})
# Возвращает: созданная сущность
```

**Примеры:**
```python
# Простое создание задачи
task = await client.tasks.create({"name": "Новая задача"})

# Создание проекта
project = await client.projects.create({"name": "Новый проект"})

# Создание сделки (требует program)
deal = await client.deals.create({
    "name": "Новая сделка",
    "program": {"contentType": "Program", "id": 10}
})
```

#### Обновление (`update`)

```python
entity = await client.{resource}.update(
    {resource}_id=42,
    {resource}_data={
        "name": "Обновленное название",
        # ... другие поля для обновления
    }
)
# Возвращает: обновленная сущность
```

**Примеры:**
```python
task = await client.tasks.update(task_id=42, task_data={"status": "completed"})
project = await client.projects.update(project_id=5, project_data={"name": "Новое название"})
deal = await client.deals.update(deal_id=200, deal_data={"sum_base": 60000.0})
```

#### Удаление (`delete`)

```python
await client.{resource}.delete({resource}_id=42)
# Возвращает: None
```

**Примеры:**
```python
await client.tasks.delete(task_id=42)
await client.projects.delete(project_id=5)
await client.deals.delete(deal_id=200)
```

### Пагинация

SDK поддерживает несколько способов работы с большими списками:

#### Ручная пагинация

```python
# Пагинация "после" определенной сущности
entities = await client.tasks.list(
    limit=50,
    page_after={"contentType": "Task", "id": 100}
)

# Пагинация "до" определенной сущности
entities = await client.tasks.list(
    limit=50,
    page_before={"contentType": "Task", "id": 200}
)

# Пагинация "с" определенной сущностью
entities = await client.tasks.list(
    limit=50,
    page_with={"contentType": "Task", "id": 150}
)
```

#### Автоматическая пагинация с `iterate()`

Метод `iterate()` автоматически обрабатывает пагинацию и возвращает все элементы:

```python
# Итерация по всем задачам
async for task in client.tasks.iterate(limit=100):
    print(task.name)

# Итерация по всем проектам
async for project in client.projects.iterate(limit=50):
    print(project.name)

# Итерация по всем сделкам
async for deal in client.deals.iterate(limit=200):
    print(deal.name)
```

### Получение полной информации (`get_full_details`)

Метод `get_full_details()` позволяет получить сущность со всеми связанными данными за один вызов. Все запросы выполняются параллельно для максимальной производительности.

**Общий формат:**
```python
details = await client.{resource}.get_full_details(
    {resource}_id=42,
    include_comments=True,          # Загрузить комментарии
    include_history=True,            # Загрузить историю изменений
    comments_limit=50,               # Лимит комментариев (опционально)
    history_limit=100                # Лимит записей истории (опционально)
    # ... другие специфичные параметры для каждого типа
)
```

**Примеры для разных типов:**

```python
# Задача со всеми данными
task_details = await client.tasks.get_full_details(
    task_id=42,
    include_comments=True,
    include_sub_tasks=True,
    include_responsible_details=True
)

# Проект со всеми данными
project_details = await client.projects.get_full_details(
    project_id=5,
    include_deals=True,
    include_issues=True,
    include_comments=True
)

# Сделка со всеми данными
deal_details = await client.deals.get_full_details(
    deal_id=200,
    include_comments=True,
    include_status_history=True,
    include_contractor_details=True
)
```

**Доступ к данным:**
```python
# Основная сущность
print(details.task.name)      # для задач
print(details.project.name)   # для проектов
print(details.deal.name)      # для сделок

# Связанные данные
if details.comments:
    for comment in details.comments:
        print(comment.text)

if details.history:
    print(f"Записей в истории: {len(details.history)}")
```

Подробнее о специфичных параметрах для каждого типа сущностей см. в соответствующих разделах:
- [Задачи](#работа-с-задачами)
- [Проекты](#работа-с-проектами)
- [Сделки](#работа-со-сделками)

## Работа с задачами

> **Примечание:** Базовые операции CRUD (list, get, create, update, delete) и пагинация описаны в разделе [Общие паттерны работы с сущностями](#общие-паттерны-работы-с-сущностями).

### Специфичные параметры для задач

#### Получение списка задач с фильтрацией

Метод `list()` поддерживает дополнительные параметры для задач:

```python
tasks = await client.tasks.list(
    filter=None,              # TaskFilter: ID фильтра (int/str) или FilterBuilder объект
    statuses=None,            # list[str]: Статусы задач для фильтрации
    # ... остальные параметры из общих паттернов
)
```

**Примеры использования фильтров:**

```python
# С фильтром по статусам
tasks = await client.tasks.list(
    statuses=["assigned", "in_progress"],
    limit=50
)

# С фильтром по ID (int или str)
tasks = await client.tasks.list(filter=123)
tasks = await client.tasks.list(filter="incoming")

# С FilterBuilder для текстового поиска (рекомендуется)
from megaplan_sdk import TaskFilterBuilder

# Простой поиск по названию
filter_obj = TaskFilterBuilder().field("name").contains("договор").build()
tasks = await client.tasks.list(filter=filter_obj)

# Несколько условий с AND
filter_obj = (
    TaskFilterBuilder()
    .field("name").contains("договор")
    .and_()
    .field("name").starts_with("Важный")
    .build()
)
tasks = await client.tasks.list(filter=filter_obj)

# Условия с OR
filter_obj = (
    TaskFilterBuilder()
    .field("name").contains("договор")
    .or_()
    .field("name").contains("соглашение")
    .build()
)
tasks = await client.tasks.list(filter=filter_obj)
```

Подробнее о работе с фильтрами см. раздел [Работа с фильтрами](#работа-с-фильтрами).

### Поля модели Task

- `id: int` - Идентификатор задачи
- `name: str` - Название задачи
- `description: str` - Описание
- `status: str` - Статус задачи
- `responsible: BaseEntity` - Ответственный (Employee)
- `owner: BaseEntity` - Владелец (Employee)
- `deadline: str` - Срок выполнения
- `actual_finish: str` - Фактическая дата завершения
- `parent: BaseEntity` - Родительская задача/проект
- `project: BaseEntity` - Проект
- `priority: str` - Приоритет
- `tags: list[BaseEntity]` - Теги
- `attaches: list[BaseEntity]` - Вложения (файлы)
- `todos: list[BaseEntity]` - Подзадачи-чеклисты
- `created_at: str` - Дата создания
- `updated_at: str` - Дата обновления

### Упрощенные методы создания

Помимо стандартного `create()`, задачи поддерживают упрощенные методы:

```python
# Создание задачи с текущим пользователем как ответственным
task = await client.tasks.create_simple(
    "Новая задача",
    employees_resource=client.employees  # Автоматически определит текущего пользователя
)

# Создание задачи с указанным ответственным
task = await client.tasks.create_simple(
    "Новая задача",
    responsible_id=123
)

# Создание задачи внутри проекта (автоматически устанавливает связь)
task = await client.tasks.create_in_project(
    "Задача в проекте",
    project_id=456,
    employees_resource=client.employees
)
```

**Примечание:** Стандартный метод `create()` также поддерживается. При создании задачи автоматически устанавливаются `isUrgent=False` и `isTemplate=False`, если они не указаны явно.

### Получение подзадач

```python
subtasks = await client.tasks.get_sub_tasks(
    task_id=10,                               # int: Идентификатор задачи
    filters=None,                             # list[dict]: Фильтры типов результатов
    limit=None,                               # int: Количество элементов
    page_after=None,                          # dict: Пагинация после
    page_before=None,                         # dict: Пагинация до
    page_with=None,                           # dict: Пагинация с
    fields=None,                              # any: Дополнительные поля
    sort_by=None,                             # list[dict]: Сортировка
    only_requested_fields=None                # bool: Только запрошенные поля
)
# Возвращает: list[Task] - список подзадач

# Получение актуальных подзадач
actual_subtasks = await client.tasks.get_actual_sub_tasks(
    task_id=10,
    # ... те же параметры
)
# Возвращает: list[Task] - список актуальных подзадач
```

### Получение задач на уровне дерева

```python
tasks = await client.tasks.tree_level(
    filter=None,                              # TaskFilter: Фильтр
    limit=None,                               # int: Количество элементов
    page_after=None,                          # dict: Пагинация
    page_before=None,                         # dict: Пагинация
    page_with=None,                           # dict: Пагинация
    fields=None,                              # any: Дополнительные поля
    sort_by=None,                             # list[dict]: Сортировка
    only_requested_fields=None                # bool: Только запрошенные поля
)
# Возвращает: list[Task | Project] - список задач/проектов текущего уровня
```

### Получение полной информации о задаче

Метод `get_full_details()` для задач поддерживает следующие специфичные параметры:

```python
details = await client.tasks.get_full_details(
    task_id=42,
    include_sub_tasks=True,              # Загрузить подзадачи
    include_actual_sub_tasks=True,       # Загрузить актуальные подзадачи
    include_comments=True,                # Загрузить комментарии
    include_history=True,                 # Загрузить историю изменений
    include_auditors=True,                # Загрузить список аудиторов
    include_executors=True,               # Загрузить соисполнителей
    include_milestones=True,              # Загрузить вехи
    include_responsible_details=True,     # Загрузить полные данные ответственного
    include_owner_details=True,           # Загрузить полные данные постановщика
    comments_limit=50,                    # Лимит комментариев (опционально)
    history_limit=100                    # Лимит записей истории (опционально)
)
```

**Поля объекта TaskFullDetails:**
- `task: Task` - Основная задача
- `sub_tasks: list[Task] | None` - Подзадачи
- `actual_sub_tasks: list[Task] | None` - Актуальные подзадачи
- `comments: list[Comment] | None` - Комментарии
- `history: list[dict] | None` - История изменений
- `auditors: list[dict] | None` - Аудиторы
- `executors: list[dict] | None` - Соисполнители
- `milestones: list[Milestone] | None` - Вехи
- `responsible_details: Employee | None` - Полные данные ответственного
- `owner_details: Employee | None` - Полные данные постановщика

> **Примечание:** Общее описание метода `get_full_details()` и примеры использования см. в разделе [Общие паттерны работы с сущностями](#общие-паттерны-работы-с-сущностями).

### Работа с вехами (Milestones)

Вехи можно получать и создавать для задач и проектов.

#### Получение вех

```python
# Получить вехи задачи
milestones = await client.tasks.get_milestones(
    task_id=123,
    limit=50  # Опционально
)

# Получить вехи проекта
milestones = await client.projects.get_milestones(
    project_id=456,
    limit=50  # Опционально
)

# Вехи также доступны через get_full_details()
details = await client.tasks.get_full_details(
    task_id=123,
    include_milestones=True
)
if details.milestones:
    for milestone in details.milestones:
        print(f"{milestone.name}: {milestone.type}")
```

#### Создание вехи

```python
from megaplan_sdk.models.milestone import Milestone

# Создать веху для задачи
milestone = await client.tasks.add_milestone(
    task_id=123,
    milestone_data={
        "name": "Release 1.0",
        "description": "Release milestone description",  # Обязательное поле
        "type": "report",  # Обязательное: "report", "reminder", или "note"
        "date": "2026-02-01T10:00:00Z"  # Обязательное: ISO 8601 формат
    }
)

# Или использовать модель Milestone
milestone = await client.tasks.add_milestone(
    task_id=123,
    milestone_data=Milestone(
        name="Release 1.0",
        description="Release milestone description",
        type="report",
        date="2026-02-01T10:00:00Z"
    )
)

# Создать веху для проекта
milestone = await client.projects.add_milestone(
    project_id=456,
    milestone_data={
        "description": "Phase 1 completion",
        "type": "reminder",
        "date": "2026-03-15T14:00:00Z"
    }
)
```

**Обязательные поля при создании вехи:**
- `description: str` - Описание вехи
- `type: str` - Тип вехи: `"report"`, `"reminder"`, или `"note"`
- `date: str | DateTime | dict` - Дата и время вехи (ISO 8601 строка или объект DateTime)

**Поля модели Milestone:**
- `id: int` - Идентификатор вехи
- `name: str | None` - Название вехи
- `description: str | None` - Описание
- `completed: bool | None` - Признак завершенности
- `type: str | None` - Тип вехи
- `date: str | DateTime | dict | None` - Дата и время
- `owner: BaseEntity | None` - Создатель (Employee)
- `responsible: BaseEntity | None` - Ответственный (Employee)
- `task: BaseEntity | None` - Связанная задача
- `project: BaseEntity | None` - Связанный проект

**Примечание:** Метод `get_milestones()` может вернуть пустой список для некоторых задач/проектов из-за ограничений API (ошибка 500). Это обрабатывается автоматически.

## Работа с проектами

> **Примечание:** Базовые операции CRUD (list, get, create, update, delete) описаны в разделе [Общие паттерны работы с сущностями](#общие-паттерны-работы-с-сущностями).

**Важно:** Проекты не поддерживают фильтрацию через API (параметр `filter` недоступен).

### Поля модели Project
- `id: int` - Идентификатор проекта
- `name: str` - Название проекта
- `description: str` - Описание
- `status: str` - Статус проекта
- `owner: BaseEntity` - Владелец (Employee)
- `responsible: BaseEntity` - Ответственный (Employee)
- `deadline: str` - Срок выполнения
- `actual_finish: str` - Фактическая дата завершения
- `parent: BaseEntity` - Родительский проект
- `priority: str` - Приоритет
- `tags: list[BaseEntity]` - Теги
- `attaches: list[BaseEntity]` - Вложения
- `todos: list[BaseEntity]` - Подзадачи-чеклисты
- `created_at: str` - Дата создания
- `updated_at: str` - Дата обновления

### Упрощенные методы создания

Помимо стандартного `create()`, проекты поддерживают упрощенный метод:

```python
# Создание проекта с текущим пользователем как владельцем и ответственным
project = await client.projects.create_simple(
    "Новый проект",
    employees_resource=client.employees  # Автоматически определит текущего пользователя
)

# Создание проекта с указанными владельцем и ответственным
project = await client.projects.create_simple(
    "Новый проект",
    owner_id=123,
    responsible_id=123
)
```

**Примечание:** При создании проекта автоматически устанавливается `isTemplate=False`, если не указано явно.

### Получение сделок проекта

```python
deals = await client.projects.get_deals(
    project_id=5,                             # int: Идентификатор проекта
    limit=None,                               # int: Количество элементов
    page_after=None,                          # dict: Пагинация после
    page_before=None,                         # dict: Пагинация до
    page_with=None,                           # dict: Пагинация с
    fields=None,                              # any: Дополнительные поля
    sort_by=None,                             # list[dict]: Сортировка
    only_requested_fields=None                # bool: Только запрошенные поля
)
# Возвращает: list[Deal] - список связанных сделок
```

### Получение задач проекта

```python
issues = await client.projects.get_issues(
    project_id=5,                             # int: Идентификатор проекта
    limit=None,                               # int: Количество элементов
    page_after=None,                          # dict: Пагинация
    page_before=None,                         # dict: Пагинация
    page_with=None,                           # dict: Пагинация
    fields=None,                              # any: Дополнительные поля
    sort_by=None,                             # list[dict]: Сортировка
    only_requested_fields=None                # bool: Только запрошенные поля
)
# Возвращает: list[Task] - список задач проекта

# Получение актуальных задач проекта
actual_issues = await client.projects.get_actual_issues(
    project_id=5,
    # ... те же параметры
)
# Возвращает: list[Task] - список актуальных задач проекта
```

### Получение полной информации о проекте

Метод `get_full_details()` для проектов поддерживает следующие специфичные параметры:

```python
details = await client.projects.get_full_details(
    project_id=5,
    include_deals=True,                    # Загрузить связанные сделки
    include_issues=True,                    # Загрузить задачи проекта
    include_actual_issues=True,            # Загрузить актуальные задачи
    include_comments=True,                  # Загрузить комментарии
    include_history=True,                   # Загрузить историю изменений
    include_auditors=True,                  # Загрузить список аудиторов
    include_executors=True,                 # Загрузить соисполнителей
    include_milestones=True,                # Загрузить вехи
    include_responsible_details=True,        # Загрузить полные данные ответственного
    include_owner_details=True,             # Загрузить полные данные владельца
    comments_limit=50,                      # Лимит комментариев (опционально)
    history_limit=100                      # Лимит записей истории (опционально)
)
```

**Поля объекта ProjectFullDetails:**
- `project: Project` - Основной проект
- `deals: list[Deal] | None` - Связанные сделки
- `issues: list[Task] | None` - Задачи проекта
- `actual_issues: list[Task] | None` - Актуальные задачи
- `comments: list[Comment] | None` - Комментарии
- `history: list[dict] | None` - История изменений
- `auditors: list[dict] | None` - Аудиторы
- `executors: list[dict] | None` - Соисполнители
- `milestones: list[Milestone] | None` - Вехи
- `responsible_details: Employee | None` - Полные данные ответственного
- `owner_details: Employee | None` - Полные данные владельца

> **Примечание:** Общее описание метода `get_full_details()` и примеры использования см. в разделе [Общие паттерны работы с сущностями](#общие-паттерны-работы-с-сущностями).

### Работа с вехами (Milestones)

Вехи для проектов работают аналогично вехам для задач. См. раздел [Работа с вехами](#работа-с-вехами-milestones) в разделе "Работа с задачами" для подробностей.

## Работа со сделками

> **Примечание:** Базовые операции CRUD (list, get, create, update, delete) описаны в разделе [Общие паттерны работы с сущностями](#общие-паттерны-работы-с-сущностями).

### Специфичные параметры для сделок

#### Получение списка сделок с фильтрацией

Метод `list()` поддерживает дополнительные параметры для сделок:

```python
deals = await client.deals.list(
    filter=None,              # TradeFilter: ID фильтра (int/str) или FilterBuilder объект
    status=None,              # ProgramState: Статус программы для фильтрации
    base_on=None,             # BaseEntity: Базовая сущность для фильтрации
    # ... остальные параметры из общих паттернов
)
```

**Примеры использования фильтров:**

```python
# С фильтром по ID
deals = await client.deals.list(filter=123)
deals = await client.deals.list(filter="active")

# С FilterBuilder для текстового поиска (рекомендуется)
from megaplan_sdk import TradeFilterBuilder

# Простой поиск по названию
filter_obj = TradeFilterBuilder().field("name").contains("Leader").build()
deals = await client.deals.list(filter=filter_obj)

# Несколько условий
filter_obj = (
    TradeFilterBuilder()
    .field("name").contains("Leader")
    .and_()
    .field("name").starts_with("Важная")
    .build()
)
deals = await client.deals.list(filter=filter_obj)
```

Подробнее о работе с фильтрами см. раздел [Работа с фильтрами](#работа-с-фильтрами).

### Поля модели Deal
- `id: int` - Идентификатор сделки
- `name: str` - Название сделки
- `program: BaseEntity` - Программа (схема сделки)
- `state: ProgramState` - Текущий статус в программе
- `contractor: BaseEntity` - Контрагент (ContractorCompany/ContractorHuman)
- `responsible: BaseEntity` - Ответственный (Employee)
- `sum_base: float` - Сумма сделки
- `currency: BaseEntity` - Валюта
- `deadline: str` - Срок
- `description: str` - Описание
- `tags: list[BaseEntity]` - Теги
- `attaches: list[BaseEntity]` - Вложения
- `created_at: str` - Дата создания
- `updated_at: str` - Дата обновления

**Важно:** При создании сделки обязательно указывать поле `program` (программа/схема сделки).

### Специфичные методы сделок

#### Применение перехода (изменение статуса)

```python
deal = await client.deals.apply_transition(
    deal_id=200,                              # int: Идентификатор сделки
    transition_id=5                           # int: Идентификатор перехода
)
# Возвращает: Deal - обновленная сделка с новым статусом
```

### Применение триггера

```python
deal = await client.deals.apply_trigger(
    deal_id=200,                              # int: Идентификатор сделки
    trigger_id=3                               # int: Идентификатор триггера
)
# Возвращает: Deal - обновленная сделка
```

### Получение аудиторов сделки

```python
auditors = await client.deals.get_auditors(deal_id=200)
# Параметры:
#   deal_id: int - Идентификатор сделки
# Возвращает: list[dict] - список аудиторов
```

### Получение истории изменения статуса

```python
history = await client.deals.get_status_history(deal_id=200)
# Параметры:
#   deal_id: int - Идентификатор сделки
# Возвращает: list[dict] - список записей истории статусов
```

### Проверка существования сделки

```python
exists = await client.deals.check_exists(deal_params={
    "name": "Название сделки",
    "contractor": {"contentType": "ContractorCompany", "id": 100}
    # ... другие параметры для проверки
})
# Параметры:
#   deal_params: dict - Параметры для проверки
# Возвращает: bool - True если сделка существует, False иначе
```

### Получение полной информации о сделке

Метод `get_full_details()` для сделок поддерживает следующие специфичные параметры:

```python
details = await client.deals.get_full_details(
    deal_id=200,
    include_comments=True,                # Загрузить комментарии
    include_history=True,                  # Загрузить историю изменений
    include_status_history=True,           # Загрузить историю статусов
    include_auditors=True,                  # Загрузить список аудиторов
    include_responsible_details=True,      # Загрузить полные данные ответственного
    include_contractor_details=True,       # Загрузить полные данные контрагента
    include_related_tasks=True,            # Загрузить связанные задачи
    comments_limit=50,                     # Лимит комментариев (опционально)
    history_limit=100                      # Лимит записей истории (опционально)
)
```

**Поля объекта DealFullDetails:**
- `deal: Deal` - Основная сделка
- `comments: list[Comment] | None` - Комментарии
- `history: list[dict] | None` - История изменений
- `status_history: list[dict] | None` - История статусов
- `auditors: list[dict] | None` - Аудиторы
- `responsible_details: Employee | None` - Полные данные ответственного
- `contractor_details: Contractor | None` - Полные данные контрагента
- `related_tasks: list[Task] | None` - Связанные задачи

> **Примечание:** Общее описание метода `get_full_details()` и примеры использования см. в разделе [Общие паттерны работы с сущностями](#общие-паттерны-работы-с-сущностями).

## Продвинутые возможности

### Кэширование сущностей

SDK автоматически кэширует справочные сущности (сотрудники, контрагенты, отделы) для уменьшения количества API запросов и повышения производительности.

### Включение кэша

```python
async with MegaplanClient(
    base_url="https://my.megaplan.ru",
    username="user@example.com",
    password="password",
    enable_cache=True,      # Включить кэш (по умолчанию True)
    cache_ttl=300,          # Время жизни кэша: 5 минут (по умолчанию)
    cache_max_size=1000,    # Макс. размер кэша: 1000 сущностей (по умолчанию)
) as client:
    # Кэш работает автоматически при использовании expand
    tasks_full = await client.tasks.list(limit=10, expand=["responsible", "owner"])

    # Повторная загрузка тех же сотрудников использует кэш
    tasks_full_2 = await client.tasks.list(limit=10, expand=["responsible"])
```

### Управление кэшем

```python
# Очистить весь кэш
client.clear_cache()

# Очистить кэш для конкретного типа сущностей
client.clear_cache_type("Employee")
client.clear_cache_type("Department")
client.clear_cache_type("Contractor")

# Получить статистику кэша
if client._cache:
    stats = client._cache.stats()
    print(f"Кэшировано сущностей: {stats['size']}")
    print(f"Типы: {stats['types']}")  # {"Employee": 15, "Department": 3}
```

### Особенности кэширования

- При достижении `cache_max_size` удаляются наименее используемые сущности
- Сущности автоматически удаляются из кэша через `cache_ttl` секунд
- Кэш работает автоматически, не требуя изменений в коде
- При использовании `expand` уникальные сущности загружаются параллельно

### Глобальные дефолтные лимиты

SDK позволяет задать глобальные дефолтные значения для параметров `comments_limit` и `history_limit` на уровне клиента. Эти значения будут применяться ко всем вызовам `get_full_details()` для задач, проектов и сделок, если не переопределены явно.

### Установка глобальных дефолтов

```python
async with MegaplanClient(
    base_url="https://my.megaplan.ru",
    username="user@example.com",
    password="password",
    default_comments_limit=50,     # Дефолт для комментариев
    default_history_limit=100,     # Дефолт для истории
) as client:
    # Использует дефолты (50 комментариев, 100 записей истории)
    details = await client.tasks.get_full_details(
        task_id=123,
        include_comments=True,
        include_history=True,
    )

    # Явный параметр переопределяет глобальный дефолт
    details = await client.tasks.get_full_details(
        task_id=456,
        include_comments=True,
        comments_limit=10,  # Используется 10, а не дефолт 50
    )

    # Без указания лимита API использует свой дефолт
    details = await client.projects.get_full_details(
        project_id=5,
        include_comments=True,
        # comments_limit не указан, используется глобальный дефолт 50
    )
```

### Приоритет значений

Система применяет лимиты в следующем порядке (от высшего к низшему приоритету):

1. **Явно указанный параметр** в методе `get_full_details()` - всегда имеет наивысший приоритет
2. **Глобальный дефолт** из `MegaplanClient` - применяется если параметр не указан явно
3. **API default** (`None`) - API использует свои дефолты (обычно без ограничения) если не установлен глобальный дефолт

```python
# Пример приоритетов
client = MegaplanClient(
    base_url="https://my.megaplan.ru",
    access_token="token",
    default_comments_limit=50,  # Глобальный дефолт
)

# Приоритет 1: Явный параметр (загрузит 100)
details = await client.tasks.get_full_details(
    task_id=1,
    include_comments=True,
    comments_limit=100,  # Явно указано
)

# Приоритет 2: Глобальный дефолт (загрузит 50)
details = await client.tasks.get_full_details(
    task_id=2,
    include_comments=True,
    # comments_limit не указан, используется дефолт 50
)

# Приоритет 3: API default без глобального дефолта
client_no_defaults = MegaplanClient(
    base_url="https://my.megaplan.ru",
    access_token="token",
    # default_comments_limit не установлен
)
details = await client_no_defaults.tasks.get_full_details(
    task_id=3,
    include_comments=True,
    # API использует свой дефолт (обычно без ограничения)
)
```

### Когда использовать глобальные дефолты

Глобальные дефолты полезны в следующих случаях:

- Ограничение объема загружаемых данных для ускорения запросов
- Уменьшение размера ответов API для экономии трафика
- Применение одинаковых лимитов ко всем операциям без дублирования кода
- Предотвращение загрузки слишком большого количества комментариев/истории

```python
# Пример для высоконагруженного приложения
client = MegaplanClient(
    base_url="https://my.megaplan.ru",
    access_token="token",
    default_comments_limit=20,   # Ограничение для быстрых ответов
    default_history_limit=50,    # Контроль объема данных
)

# Все вызовы автоматически используют лимиты
tasks_details = await client.tasks.get_full_details(
    task_id=100,
    include_comments=True,
    include_history=True,
)

deals_details = await client.deals.get_full_details(
    deal_id=200,
    include_comments=True,
    include_history=True,
)

projects_details = await client.projects.get_full_details(
    project_id=300,
    include_comments=True,
    include_history=True,
)
```

### Автоматическая подгрузка связанных сущностей

Параметр `expand` позволяет автоматически подгружать связанные сущности (сотрудников, контрагентов, отделы) вместо получения только ID.

### Использование expand в задачах

```python
# Без expand - получаем только базовую информацию
tasks = await client.tasks.list(limit=10)
for task in tasks:
    print(task.responsible)  # BaseEntity(id=123, contentType='Employee')

# С expand - автоматически подгружаются сотрудники
tasks_full = await client.tasks.list(limit=10, expand=["responsible", "owner"])
for task_full in tasks_full:
    task = task_full.task
    if task_full.responsible_details:
        # Доступ к полным данным сотрудника
        print(task_full.responsible_details.display_name())
        # Вывод: "Максим Борзов (Генеральный директор)"
```

**Поддерживаемые поля для expand в задачах:**
- `responsible` - ответственный сотрудник
- `owner` - автор/постановщик задачи

### Использование expand в сделках

```python
deals_full = await client.deals.list(limit=10, expand=["responsible", "contractor"])

for deal_full in deals_full:
    deal = deal_full.deal
    print(f"Сделка: {deal.name}")

    if deal_full.responsible_details:
        print(f"Ответственный: {deal_full.responsible_details.display_name()}")

    if deal_full.contractor_details:
        print(f"Контрагент: {deal_full.contractor_details.display_name()}")

    # Статус сделки с читаемым выводом
    if deal.state:
        print(f"Статус: {deal.state}")  # Использует __str__ из ProgramState
```

**Поддерживаемые поля для expand в сделках:**
- `responsible` - ответственный сотрудник
- `contractor` - контрагент

### Использование expand в проектах

```python
projects_full = await client.projects.list(limit=10, expand=["responsible", "owner"])

for project_full in projects_full:
    if project_full.responsible_details:
        print(f"Ответственный: {project_full.responsible_details.display_name()}")
```

**Поддерживаемые поля для expand в проектах:**
- `responsible` - ответственный сотрудник
- `owner` - владелец проекта

### Использование expand в сотрудниках

```python
employees = await client.employees.list(limit=10, expand=["department", "manager"])

for employee in employees:
    # Используем helper метод для форматированного вывода
    print(f"Сотрудник: {employee.display_name()}")

    # Отдел подгружен как полный объект Department
    if employee.department and hasattr(employee.department, 'name'):
        print(f"Отдел: {employee.department.name}")

    # Руководитель подгружен как полный объект Employee
    if employee.manager and hasattr(employee.manager, 'display_name'):
        print(f"Руководитель: {employee.manager.display_name()}")
```

**Поддерживаемые поля для expand в сотрудниках:**
- `department` - отдел сотрудника
- `manager` - непосредственный руководитель

### Helper методы для читаемого вывода

Модели содержат удобные методы для форматированного вывода:

```python
# Employee
employee.full_name()           # "Максим Борзов"
employee.full_name(include_middle=True)  # "Максим Александрович Борзов"
employee.display_name()        # "Максим Борзов (Генеральный директор)"
str(employee)                  # То же, что display_name()

# Contractor
contractor.display_name()      # "ООО Рога и Копыта" или "Contractor#123"
str(contractor)                # То же, что display_name()

# Department
str(department)                # "IT отдел" или "Department#5"

# ProgramState (статус сделки)
str(deal.state)                # "Переговоры" или "State#10"
```

### Производительность

Использование `expand` значительно сокращает количество API запросов:

```python
# БЕЗ expand: 1 запрос на список + N запросов на каждого уникального сотрудника
tasks = await client.tasks.list(limit=100)  # 1 запрос
for task in tasks:
    if task.responsible:
        # Нужно загрузить сотрудника отдельно (100+ запросов)
        employee = await client.employees.get(task.responsible.id)

# С expand: 1 запрос на список + 1 батч запросов на уникальных сотрудников
tasks_full = await client.tasks.list(limit=100, expand=["responsible"])
# Всего: 2 запроса (список задач + батч сотрудников)
# Повторные сотрудники берутся из кэша!
```

**Пример**:
- 100 задач с 5 уникальными ответственными
- Без expand: 101 запрос (1 список + 100 запросов на сотрудников)
- С expand: 2 запроса (1 список + 1 батч на 5 сотрудников)
- **Экономия: 99 запросов (98%)**

### Работа с фильтрами

SDK предоставляет удобный `FilterBuilder` для создания фильтров с использованием fluent API. Фильтры поддерживаются для задач (`TaskFilter`) и сделок (`TradeFilter`). **Проекты не поддерживают фильтрацию через API.**

### Базовое использование

```python
from megaplan_sdk import TaskFilterBuilder, TradeFilterBuilder

# Простой текстовый поиск в задачах
filter_obj = TaskFilterBuilder().field("name").contains("договор").build()
tasks = await client.tasks.list(filter=filter_obj)

# Простой текстовый поиск в сделках
filter_obj = TradeFilterBuilder().field("name").contains("Leader").build()
deals = await client.deals.list(filter=filter_obj)
```

### Доступные операции для строковых полей

```python
# Поиск подстроки (рекомендуется для текстового поиска)
filter_obj = TaskFilterBuilder().field("name").contains("договор").build()

# Поиск по началу строки
filter_obj = TaskFilterBuilder().field("name").starts_with("Важный").build()

# Точное совпадение
filter_obj = TaskFilterBuilder().field("status").equals("active").build()

# Исключение подстроки
filter_obj = TaskFilterBuilder().field("name").not_contains("архив").build()

# Не равно
filter_obj = TaskFilterBuilder().field("status").not_equals("completed").build()
```

### Комбинирование условий

```python
# Несколько условий с AND
filter_obj = (
    TaskFilterBuilder()
    .field("name").contains("договор")
    .and_()
    .field("name").starts_with("Важный")
    .build()
)

# Условия с OR
filter_obj = (
    TaskFilterBuilder()
    .field("name").contains("договор")
    .or_()
    .field("name").contains("соглашение")
    .build()
)
```

### Использование фильтров по ID

Помимо `FilterBuilder`, можно использовать сохраненные фильтры по их ID:

```python
# Фильтр по числовому ID
tasks = await client.tasks.list(filter=123)

# Фильтр по строковому ID
tasks = await client.tasks.list(filter="incoming")
deals = await client.deals.list(filter="active")
```

### Управление фильтрами

SDK предоставляет методы для работы с сохраненными фильтрами:

```python
# Получить список всех фильтров для задач
filters = await client.filters.list("task")

# Получить конкретный фильтр
filter_obj = await client.filters.get("task", filter_id=123)

# Создать новый фильтр
new_filter = await client.filters.create(
    "task",
    filter_id="my_custom_filter",
    filter_config={
        "config": {
            "contentType": "FilterConfig",
            "termGroup": {
                "contentType": "FilterTermGroup",
                "join": "and",
                "terms": [
                    {
                        "contentType": "FilterTermString",
                        "field": "name",
                        "comparison": "contains",
                        "value": "договор"
                    }
                ]
            }
        }
    }
)

# Обновить существующий фильтр
updated = await client.filters.update("task", filter_id=123, filter_config={...})

# Экспортировать фильтр
export_data = await client.filters.export("task", filter_id=123)
```

### Настройка HTTP-клиента

```python
client = MegaplanClient(
    base_url="https://my.megaplan.ru",
    username="user@example.com",
    password="password",
    timeout=60.0,                             # float: Таймаут запросов в секундах (по умолчанию 30.0)
    max_retries=5                              # int: Максимальное количество повторов при 5xx ошибках (по умолчанию 3)
)
```

### Работа через прокси

SDK поддерживает работу через HTTP/HTTPS/SOCKS5 прокси-серверы. Это полезно для корпоративных сетей, где все запросы должны проходить через прокси.

```python
# HTTP прокси с аутентификацией
async with MegaplanClient(
    base_url="https://my.megaplan.ru",
    username="user@example.com",
    password="password",
    proxy="http://login:pass@proxy.corp.local:8080",
) as client:
    tasks = await client.tasks.list()

# HTTP прокси без аутентификации
client = MegaplanClient(
    base_url="https://my.megaplan.ru",
    access_token="token",
    proxy="http://proxy.corp.local:8080",
)

# HTTPS прокси
client = MegaplanClient(
    base_url="https://my.megaplan.ru",
    access_token="token",
    proxy="https://proxy.corp.local:8080",
)

# SOCKS5 прокси (требует httpx[socks])
client = MegaplanClient(
    base_url="https://my.megaplan.ru",
    access_token="token",
    proxy="socks5://user:pass@proxy.corp.local:1080",
)
```

**Поддерживаемые форматы прокси:**
- `http://proxy:port` - HTTP прокси без аутентификации
- `http://user:password@proxy:port` - HTTP прокси с аутентификацией
- `https://proxy:port` - HTTPS прокси
- `socks5://user:password@proxy:port` - SOCKS5 прокси (требует `pip install httpx[socks]`)

### Ручное управление токенами

```python
# Получить токен доступа
token = await client.auth.authenticate("user@example.com", "password")
# Возвращает: str - access_token

# Обновить токен
new_token = await client.auth.refresh_token(refresh_token="refresh_token")
# Параметры:
#   refresh_token: str | None - Токен обновления (опционально, используется сохраненный)
# Возвращает: str - новый access_token

# Установить токен вручную
client.set_access_token("your_token")

# Очистить токены
client.auth.clear_tokens()
```

## Справочная информация

### Известные ограничения API

Некоторые эндпоинты Megaplan API имеют ограничения или известные проблемы:

### Комментарии контрагентов

API возвращает ошибку 500 при попытке получить или создать комментарии для контрагентов. Для отслеживания взаимодействия с контрагентами используйте:
- Журнал действий (action history)
- Комментарии в связанных сделках
- Комментарии в связанных задачах

```python
# Это НЕ работает - вернет 500 ошибку
# comments = await client.contractors.get_comments(contractor_id=123)

# Вместо этого используйте комментарии в сделках контрагента
deals = await client.contractors.get_deals(contractor_id=123)
for deal in deals:
    comments = await client.deals.get_comments(deal.id)
```

### Получение сделок контрагента

SDK предоставляет удобный метод `get_deals()` для получения сделок контрагента:

```python
# Получить все сделки контрагента
deals = await client.contractors.get_deals(
    contractor_id=123,
    limit=50  # Опционально
)

for deal in deals:
    print(f"[{deal.id}] {deal.name}")
    if deal.state:
        print(f"  Статус: {deal.state}")
```

Это удобнее, чем использование `FilterBuilder`:

```python
# Альтернатива через FilterBuilder (более сложный способ)
from megaplan_sdk import TradeFilterBuilder
filter_obj = TradeFilterBuilder().field("contractor").equals(
    {"contentType": "Contractor", "id": 123}
).build()
deals = await client.deals.list(filter=filter_obj)
```

### Поиск сотрудников

Поиск сотрудников по имени или телефону может работать некорректно и возвращать 0 результатов. Для надежного поиска используйте точный email:

```python
# Может не работать
employees = await client.employees.list(q="Иван Иванов")

# Рекомендуется - поиск по точному email
employees = await client.employees.list(q="ivan@example.com")

# Или загрузите всех сотрудников и фильтруйте локально
```

### Проверка существования сделки (check_exists)

Метод `check_exists()` для сделок может возвращать ошибки 500 или 422 из-за ограничений API. SDK автоматически обрабатывает эти ошибки и возвращает `False`. Для проверки существования сделки рекомендуется использовать альтернативные методы:

```python
# Может вернуть 500/422 ошибку
# exists = await client.deals.check_exists(query="Deal name")

# Альтернатива: используйте поиск через list()
deals = await client.deals.list(q="Deal name", limit=1)
exists = len(deals) > 0

# Или используйте FilterBuilder
from megaplan_sdk import TradeFilterBuilder
filter_obj = TradeFilterBuilder().field("name").equals("Deal name").build()
deals = await client.deals.list(filter=filter_obj, limit=1)
exists = len(deals) > 0
```

**Примечание:** SDK автоматически нормализует BaseEntity объекты (конвертирует строковые ID в int), но это не решает проблему багов API.

### Параметр statuses для задач

Параметр `statuses` для фильтрации задач по статусам может возвращать ошибку 422 ValidationError из-за ограничений API. Рекомендуется использовать FilterBuilder для надежной фильтрации:

```python
# Может вернуть 422 ошибку
# tasks = await client.tasks.list(statuses=["assigned", "in_progress"])

# Рекомендуется: используйте FilterBuilder
from megaplan_sdk import TaskFilterBuilder
filter_obj = TaskFilterBuilder().field_enum("status").in_list(["assigned", "in_progress"]).build()
tasks = await client.tasks.list(filter=filter_obj)
```

### Параметр baseOn для сделок

Параметр `baseOn` для фильтрации сделок по связанной сущности может возвращать ошибку 422 ValidationError из-за ограничений API. SDK автоматически нормализует BaseEntity объекты (конвертирует строковые ID в int), но это не всегда решает проблему:

```python
# Может вернуть 422 ошибку
# deals = await client.deals.list(base_on={"contentType": "Contractor", "id": 123})

# Альтернатива: используйте FilterBuilder
from megaplan_sdk import TradeFilterBuilder
filter_obj = TradeFilterBuilder().field("contractor").equals({"contentType": "Contractor", "id": 123}).build()
deals = await client.deals.list(filter=filter_obj)
```

### Пагинация контрагентов

Пагинация через `page_after`, `page_before`, `page_with` для контрагентов может возвращать ошибку 422 ValidationError из-за ограничений API. SDK автоматически нормализует BaseEntity объекты, но рекомендуется использовать `limit` и ручную итерацию:

```python
# Может вернуть 422 ошибку
# contractors = await client.contractors.list(page_after={"contentType": "Contractor", "id": 123})

# Рекомендуется: используйте limit и iterate()
async for contractor in client.contractors.iterate(limit=50):
    # Обработка контрагента
    pass
```

### Нормализация BaseEntity

SDK автоматически нормализует BaseEntity объекты во всех параметрах:
- Конвертирует строковые ID в int (где возможно)
- Обеспечивает правильный формат `contentType` и `id`
- Применяется к параметрам: `page_after`, `page_before`, `page_with`, `baseOn`, вложенным объектам в `deal` для `check_exists()`

Это помогает избежать некоторых ошибок валидации, но не решает все проблемы API.
all_employees = []
async for emp in client.employees.iterate():
    if "Иван" in emp.first_name:
        all_employees.append(emp)
```

### Архитектура

SDK спроектирован с учетом модульности:

- Resources (`TasksResource`, `ProjectsResource`, etc.) - Обработка операций API
- Models (Pydantic) - Типобезопасные структуры данных
- HTTPClient - Низкоуровневые HTTP-операции с retry и авторизацией
- AuthManager - Управление OAuth2-токенами

### Расширение SDK

Для добавления нового ресурса:

1. Создайте модель в `src/megaplan_sdk/models/`
2. Создайте ресурс в `src/megaplan_sdk/resources/`, наследуя от `BaseResource`
3. Добавьте ресурс в `MegaplanClient`:

```python
class MegaplanClient:
    def __init__(self, ...):
        # ... существующий код ...
        self.new_resource = NewResource(self._http)
```

### Требования

- Python 3.11+
- httpx >= 0.25.0
- pydantic >= 2.0.0

### Разработка

### Установка для разработки

```bash
git clone https://github.com/borzov/megaplan-sdk.git
cd megaplan-sdk
pip install -e ".[dev]"
```

### Запуск тестов

```bash
pytest
```

С покрытием:

```bash
pytest --cov=megaplan_sdk --cov-report=html
```

### Проверка типов

```bash
mypy megaplan_sdk
```

### Линтинг

```bash
ruff check megaplan_sdk
ruff format megaplan_sdk
```

## Лицензия

MIT License

## Ссылки

- [Документация API Мегаплана](https://dev.megaplan.ru/apiv3/index.html)
- [Официальный PHP SDK](https://github.com/megaplan/megaplansdk)

## Вклад в проект

Вклад приветствуется! Пожалуйста, не стесняйтесь отправлять Pull Request.
