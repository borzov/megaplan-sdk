# Megaplan Python SDK

[![Tests](https://github.com/borzov/megaplan-sdk/actions/workflows/tests.yml/badge.svg)](https://github.com/borzov/megaplan-sdk/actions/workflows/tests.yml)

Профессиональная Python-библиотека для работы с API Мегаплана версии 3.

## О проекте

Современная библиотека для интеграции с CRM Мегаплан. Она предоставляет удобный и типобезопасный интерфейс для работы с задачами, проектами, сделками и другими сущностями через REST API.

### Зачем нужна эта библиотека?

Работа с API Мегаплана напрямую требует знания множества технических деталей: правильной настройки OAuth2-авторизации, обработки токенов, формирования JSON-параметров в query string, обработки ошибок и пагинации. Эта библиотека берет на себя всю рутинную работу, позволяя разработчикам сосредоточиться на бизнес-логике.

### Преимущества использования SDK

Вместо прямых HTTP-запросов вы получаете простой и понятный Python-интерфейс. Вместо ручной работы с токенами — автоматическую авторизацию и обновление токенов. Вместо парсинга JSON-ответов — типизированные Pydantic-модели с автодополнением в IDE. Вместо обработки ошибок вручную — понятные исключения с детальной информацией.

Библиотека полностью асинхронная, что позволяет эффективно работать с большими объемами данных и выполнять параллельные запросы. Встроенная логика повторных попыток при временных сбоях сервера делает интеграцию более надежной. Модульная архитектура позволяет легко расширять функциональность и добавлять поддержку новых модулей API.

## Возможности

- Полный CRUD для задач, проектов и сделок
- Метод `get_full_details()` — получение сущности со всеми связанными данными (комментарии, история, подзадачи и т.д.) за один вызов с параллельной загрузкой
- OAuth2-авторизация с автоматическим обновлением токенов
- Типобезопасность с Pydantic-моделями и полной типизацией
- Асинхронность — поддержка async/await во всех операциях
- Автоматические повторы при ошибках сервера (5xx)
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

## Работа с задачами

### Получение списка задач

```python
tasks = await client.tasks.list(
    filter=None,              # TaskFilter: ID фильтра (int) или конфигурация (dict)
    statuses=None,            # list[str]: Статусы задач для фильтрации
    limit=None,               # int: Количество элементов на странице
    page_after=None,          # dict: Загрузить страницу, начиная с этой сущности
    page_before=None,         # dict: Загрузить страницу строго до этой сущности
    page_with=None,           # dict: Загрузить страницу с наличием этой сущности
    fields=None,              # any: Набор дополнительных полей
    sort_by=None,             # list[dict]: Массив полей сортировки
    only_requested_fields=None # bool: Отдавать только перечисленные поля
)
# Возвращает: list[Task] - список объектов Task
```

**Примеры использования:**

```python
# Получить все задачи
tasks = await client.tasks.list()

# С фильтром по статусам
tasks = await client.tasks.list(
    statuses=["assigned", "in_progress"],
    limit=50
)

# С фильтром по ID
tasks = await client.tasks.list(filter=123)

# С фильтром по конфигурации
tasks = await client.tasks.list(filter={"status": "active"})

# Итерация по всем задачам с автоматической пагинацией
async for task in client.tasks.iterate(limit=100):
    print(task.name)
```

### Получение задачи по ID

```python
task = await client.tasks.get(task_id=42)
# Параметры:
#   task_id: int - Идентификатор задачи
# Возвращает: Task - объект задачи со всеми полями
```

**Поля объекта Task:**
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

### Создание задачи

```python
task = await client.tasks.create(task_data={
    "name": "Новая задача",                    # str: Название задачи (обязательно)
    "responsible": {                          # BaseEntity: Ответственный
        "contentType": "Employee",
        "id": 1
    },
    "deadline": "2024-12-31",                 # str: Срок выполнения
    "description": "Описание задачи",         # str: Описание
    "parent": {                               # BaseEntity: Родительская задача/проект
        "contentType": "Task",
        "id": 10
    },
    "project": {                              # BaseEntity: Проект
        "contentType": "Project",
        "id": 5
    },
    "priority": "high",                        # str: Приоритет
    "tags": [                                 # list[BaseEntity]: Теги
        {"contentType": "Tag", "id": 1}
    ],
    "attaches": [                             # list[BaseEntity]: Вложения
        {"contentType": "File", "id": 100}
    ]
})
# Возвращает: Task - созданная задача
```

### Обновление задачи

```python
task = await client.tasks.update(
    task_id=42,                               # int: Идентификатор задачи
    task_data={                               # dict: Данные для обновления
        "status": "completed",
        "actualFinish": "2024-01-15",
        "name": "Обновленное название"
    }
)
# Возвращает: Task - обновленная задача
```

### Удаление задачи

```python
await client.tasks.delete(task_id=42)
# Параметры:
#   task_id: int - Идентификатор задачи
# Возвращает: None
```

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

Метод `get_full_details()` позволяет получить задачу со всеми связанными данными за один вызов. Все запросы выполняются параллельно для максимальной производительности.

```python
from megaplan_sdk import MegaplanClient

async with MegaplanClient(...) as client:
    # Получить задачу со всей информацией
    details = await client.tasks.get_full_details(
        task_id=42,
        include_sub_tasks=True,                    # Загрузить подзадачи
        include_actual_sub_tasks=True,             # Загрузить актуальные подзадачи
        include_comments=True,                     # Загрузить комментарии
        include_history=True,                      # Загрузить историю изменений
        include_auditors=True,                     # Загрузить список аудиторов
        include_executors=True,                    # Загрузить соисполнителей
        include_milestones=True,                   # Загрузить вехи
        include_responsible_details=True,          # Загрузить полные данные ответственного
        include_owner_details=True,                # Загрузить полные данные постановщика
        comments_limit=50,                         # Лимит комментариев (опционально)
        history_limit=100                          # Лимит записей истории (опционально)
    )

    # Доступ к основным данным задачи
    print(f"Задача: {details.task.name}")
    print(f"Статус: {details.task.status}")

    # Доступ к связанным данным
    if details.comments:
        print(f"Комментариев: {len(details.comments)}")
        for comment in details.comments:
            print(f"  - {comment.text}")

    if details.sub_tasks:
        print(f"Подзадач: {len(details.sub_tasks)}")
        for subtask in details.sub_tasks:
            print(f"  - {subtask.name}")

    if details.responsible_details:
        print(f"Ответственный: {details.responsible_details.first_name} {details.responsible_details.last_name}")

    if details.owner_details:
        print(f"Постановщик: {details.owner_details.first_name} {details.owner_details.last_name}")
```

**Поля объекта TaskFullDetails:**
- `task: Task` - Основная задача
- `sub_tasks: list[Task] | None` - Подзадачи
- `actual_sub_tasks: list[Task] | None` - Актуальные подзадачи
- `comments: list[Comment] | None` - Комментарии
- `history: list[dict] | None` - История изменений
- `auditors: list[dict] | None` - Аудиторы
- `executors: list[dict] | None` - Соисполнители
- `milestones: list[dict] | None` - Вехи
- `responsible_details: Employee | None` - Полные данные ответственного
- `owner_details: Employee | None` - Полные данные постановщика

**Примеры использования:**

```python
# Минимальный вызов - только основная задача
details = await client.tasks.get_full_details(task_id=42)

# Задача с комментариями и историей
details = await client.tasks.get_full_details(
    task_id=42,
    include_comments=True,
    include_history=True,
    comments_limit=20
)

# Полная информация для отчета
details = await client.tasks.get_full_details(
    task_id=42,
    include_sub_tasks=True,
    include_comments=True,
    include_history=True,
    include_auditors=True,
    include_executors=True,
    include_responsible_details=True,
    include_owner_details=True
)
```

## Работа с проектами

### Получение списка проектов

```python
projects = await client.projects.list(
    limit=None,                               # int: Количество элементов на странице
    page_after=None,                          # dict: Загрузить страницу, начиная с этой сущности
    page_before=None,                         # dict: Загрузить страницу строго до этой сущности
    page_with=None,                           # dict: Загрузить страницу с наличием этой сущности
    fields=None,                              # any: Набор дополнительных полей
    sort_by=None,                             # list[dict]: Массив полей сортировки
    only_requested_fields=None                # bool: Отдавать только перечисленные поля
)
# Возвращает: list[Project] - список объектов Project
```

### Получение проекта по ID

```python
project = await client.projects.get(project_id=5)
# Параметры:
#   project_id: int - Идентификатор проекта
# Возвращает: Project - объект проекта со всеми полями
```

**Поля объекта Project:**
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

### Создание проекта

```python
project = await client.projects.create(project_data={
    "name": "Новый проект",                   # str: Название проекта (обязательно)
    "owner": {                                # BaseEntity: Владелец
        "contentType": "Employee",
        "id": 1
    },
    "responsible": {                          # BaseEntity: Ответственный
        "contentType": "Employee",
        "id": 2
    },
    "deadline": "2024-12-31",                 # str: Срок выполнения
    "description": "Описание проекта"         # str: Описание
})
# Возвращает: Project - созданный проект
```

### Обновление проекта

```python
project = await client.projects.update(
    project_id=5,                             # int: Идентификатор проекта
    project_data={                            # dict: Данные для обновления
        "name": "Обновленное название",
        "status": "in_progress"
    }
)
# Возвращает: Project - обновленный проект
```

### Удаление проекта

```python
await client.projects.delete(project_id=5)
# Параметры:
#   project_id: int - Идентификатор проекта
# Возвращает: None
```

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

Метод `get_full_details()` позволяет получить проект со всеми связанными данными за один вызов. Все запросы выполняются параллельно для максимальной производительности.

```python
from megaplan_sdk import MegaplanClient

async with MegaplanClient(...) as client:
    # Получить проект со всей информацией
    details = await client.projects.get_full_details(
        project_id=5,
        include_deals=True,                        # Загрузить связанные сделки
        include_issues=True,                       # Загрузить задачи проекта
        include_actual_issues=True,                # Загрузить актуальные задачи
        include_comments=True,                     # Загрузить комментарии
        include_history=True,                      # Загрузить историю изменений
        include_auditors=True,                     # Загрузить список аудиторов
        include_executors=True,                    # Загрузить соисполнителей
        include_milestones=True,                   # Загрузить вехи
        include_responsible_details=True,          # Загрузить полные данные ответственного
        include_owner_details=True,                # Загрузить полные данные владельца
        comments_limit=50,                         # Лимит комментариев (опционально)
        history_limit=100                          # Лимит записей истории (опционально)
    )

    # Доступ к основным данным проекта
    print(f"Проект: {details.project.name}")
    print(f"Статус: {details.project.status}")

    # Доступ к связанным данным
    if details.deals:
        print(f"Сделок: {len(details.deals)}")
        for deal in details.deals:
            print(f"  - {deal.name}")

    if details.issues:
        print(f"Задач: {len(details.issues)}")
        for task in details.issues:
            print(f"  - {task.name}")

    if details.comments:
        print(f"Комментариев: {len(details.comments)}")

    if details.responsible_details:
        print(f"Ответственный: {details.responsible_details.first_name} {details.responsible_details.last_name}")

    if details.owner_details:
        print(f"Владелец: {details.owner_details.first_name} {details.owner_details.last_name}")
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
- `milestones: list[dict] | None` - Вехи
- `responsible_details: Employee | None` - Полные данные ответственного
- `owner_details: Employee | None` - Полные данные владельца

**Примеры использования:**

```python
# Минимальный вызов - только основной проект
details = await client.projects.get_full_details(project_id=5)

# Проект со сделками и задачами
details = await client.projects.get_full_details(
    project_id=5,
    include_deals=True,
    include_issues=True
)

# Полная информация для отчета
details = await client.projects.get_full_details(
    project_id=5,
    include_deals=True,
    include_issues=True,
    include_comments=True,
    include_history=True,
    include_responsible_details=True,
    include_owner_details=True
)
```

## Работа со сделками

### Получение списка сделок

```python
deals = await client.deals.list(
    filter=None,                              # TradeFilter: ID фильтра (int) или конфигурация (dict)
    status=None,                              # ProgramState: Статус программы для фильтрации
    q=None,                                   # str: Поисковый запрос
    base_on=None,                             # BaseEntity: Базовая сущность для фильтрации
    limit=None,                               # int: Количество элементов на странице
    page_after=None,                           # dict: Пагинация после
    page_before=None,                          # dict: Пагинация до
    page_with=None,                            # dict: Пагинация с
    fields=None,                               # any: Дополнительные поля
    sort_by=None,                              # list[dict]: Сортировка
    only_requested_fields=None                 # bool: Только запрошенные поля
)
# Возвращает: list[Deal] - список объектов Deal
```

### Получение сделки по ID

```python
deal = await client.deals.get(deal_id=200)
# Параметры:
#   deal_id: int - Идентификатор сделки
# Возвращает: Deal - объект сделки со всеми полями
```

**Поля объекта Deal:**
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

### Создание сделки

```python
deal = await client.deals.create(deal_data={
    "program": {                              # BaseEntity: Программа (обязательно)
        "contentType": "Program",
        "id": 10
    },
    "name": "Новая сделка",                   # str: Название сделки (обязательно)
    "contractor": {                           # BaseEntity: Контрагент
        "contentType": "ContractorCompany",
        "id": 100
    },
    "responsible": {                          # BaseEntity: Ответственный
        "contentType": "Employee",
        "id": 1
    },
    "sum_base": 50000.0,                      # float: Сумма сделки
    "deadline": "2024-12-31",                 # str: Срок
    "description": "Описание сделки"          # str: Описание
})
# Возвращает: Deal - созданная сделка
```

### Обновление сделки

```python
deal = await client.deals.update(
    deal_id=200,                              # int: Идентификатор сделки
    deal_data={                               # dict: Данные для обновления
        "sum_base": 60000.0,
        "status": "active"
    }
)
# Возвращает: Deal - обновленная сделка
```

### Удаление сделки

```python
await client.deals.delete(deal_id=200)
# Параметры:
#   deal_id: int - Идентификатор сделки
# Возвращает: None
```

### Применение перехода (изменение статуса)

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

Метод `get_full_details()` позволяет получить сделку со всеми связанными данными за один вызов. Все запросы выполняются параллельно для максимальной производительности.

```python
from megaplan_sdk import MegaplanClient

async with MegaplanClient(...) as client:
    # Получить сделку со всей информацией
    details = await client.deals.get_full_details(
        deal_id=200,
        include_comments=True,                     # Загрузить комментарии
        include_history=True,                      # Загрузить историю изменений
        include_status_history=True,               # Загрузить историю статусов
        include_auditors=True,                     # Загрузить список аудиторов
        include_responsible_details=True,          # Загрузить полные данные ответственного
        include_contractor_details=True,           # Загрузить полные данные контрагента
        include_related_tasks=True,                # Загрузить связанные задачи
        comments_limit=50,                         # Лимит комментариев (опционально)
        history_limit=100                          # Лимит записей истории (опционально)
    )

    # Доступ к основным данным сделки
    print(f"Сделка: {details.deal.name}")
    print(f"Сумма: {details.deal.sum_base}")
    print(f"Статус: {details.deal.state.name if details.deal.state else 'Не указан'}")

    # Доступ к связанным данным
    if details.comments:
        print(f"Комментариев: {len(details.comments)}")
        for comment in details.comments:
            print(f"  - {comment.text}")

    if details.history:
        print(f"Записей в истории: {len(details.history)}")

    if details.status_history:
        print(f"Изменений статуса: {len(details.status_history)}")

    if details.responsible_details:
        print(f"Ответственный: {details.responsible_details.first_name} {details.responsible_details.last_name}")
        print(f"Email: {details.responsible_details.email}")

    if details.contractor_details:
        print(f"Контрагент: {details.contractor_details.name}")

    if details.related_tasks:
        print(f"Связанных задач: {len(details.related_tasks)}")
        for task in details.related_tasks:
            print(f"  - {task.name}")
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

**Примеры использования:**

```python
# Минимальный вызов - только основная сделка
details = await client.deals.get_full_details(deal_id=200)

# Сделка с комментариями и историей
details = await client.deals.get_full_details(
    deal_id=200,
    include_comments=True,
    include_history=True,
    include_status_history=True,
    comments_limit=20
)

# Полная информация для отчета
details = await client.deals.get_full_details(
    deal_id=200,
    include_comments=True,
    include_history=True,
    include_status_history=True,
    include_auditors=True,
    include_responsible_details=True,
    include_contractor_details=True,
    include_related_tasks=True
)

# Только данные о людях
details = await client.deals.get_full_details(
    deal_id=200,
    include_responsible_details=True,
    include_contractor_details=True
)
```

## Работа с файлами

### Загрузка файла

```python
# Из файла на диске
file = await client.files.upload(
    file_path="/path/to/document.pdf",        # str | Path: Путь к файлу
    filename=None                             # str: Имя файла (опционально, по умолчанию берется из пути)
)
# Возвращает: File - объект файла с id и contentType

# Из байтов
file = await client.files.upload_bytes(
    file_bytes=b"...",                        # bytes: Содержимое файла
    filename="document.pdf"                  # str: Имя файла
)
# Возвращает: File - объект файла

# Использование файла в задаче или другой сущности
task = await client.tasks.create({
    "name": "Задача с файлом",
    "attaches": [{"contentType": "File", "id": file.id}]
})
```

**Поля объекта File:**
- `id: int` - Идентификатор файла
- `content_type: str` - Тип контента (обычно "File")
- `path: str` - Путь к файлу
- `mime_type: str` - MIME-тип файла
- `name: str` - Имя файла
- `size: int` - Размер файла в байтах

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

## Продвинутое использование

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

## Кэширование сущностей

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

- **LRU (Least Recently Used)**: При достижении `cache_max_size` удаляются наименее используемые сущности
- **TTL (Time To Live)**: Сущности автоматически удаляются из кэша через `cache_ttl` секунд
- **Прозрачность**: Кэш работает автоматически, не требуя изменений в коде
- **Батчевая загрузка**: При использовании `expand` уникальные сущности загружаются параллельно

## Автоматическая подгрузка связанных сущностей

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

## Известные ограничения API

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
deals = await client.deals.list(
    base_on={"contentType": "Contractor", "id": 123}
)
for deal in deals:
    comments = await client.deals.get_comments(deal.id)
```

### Поиск сотрудников

Поиск сотрудников по имени или телефону может работать некорректно и возвращать 0 результатов. Для надежного поиска используйте точный email:

```python
# Может не работать
employees = await client.employees.list(q="Иван Иванов")

# Рекомендуется - поиск по точному email
employees = await client.employees.list(q="ivan@example.com")

# Или загрузите всех сотрудников и фильтруйте локально
all_employees = []
async for emp in client.employees.iterate():
    if "Иван" in emp.first_name:
        all_employees.append(emp)
```

## Архитектура

SDK спроектирован с учетом модульности:

- **Resources** (`TasksResource`, `ProjectsResource`, etc.) - Обработка операций API
- **Models** (Pydantic) - Типобезопасные структуры данных
- **HTTPClient** - Низкоуровневые HTTP-операции с retry и авторизацией
- **AuthManager** - Управление OAuth2-токенами

### Расширение SDK

Для добавления нового ресурса:

1. Создайте модель в `megaplan_sdk/models/`
2. Создайте ресурс в `megaplan_sdk/resources/`, наследуя от `BaseResource`
3. Добавьте ресурс в `MegaplanClient`:

```python
class MegaplanClient:
    def __init__(self, ...):
        # ... существующий код ...
        self.new_resource = NewResource(self._http)
```

## Требования

- Python 3.11+
- httpx >= 0.25.0
- pydantic >= 2.0.0

## Разработка

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
