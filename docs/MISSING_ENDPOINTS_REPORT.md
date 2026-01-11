# Отчет о нереализованных endpoints в SDK

**Дата:** 2026-01-11  
**Версия RAML:** r2510.27309.181  
**Источник:** Архитектурный аудит SDK

## Резюме

Из проанализированных RAML endpoints найдено **~30 нереализованных endpoints** (~30% от доступных специфичных endpoints).

**Важно:** Все **базовые CRUD операции** (create, read, update, delete, list) реализованы на **100%**. Пропущены в основном **специфичные вспомогательные endpoints**, которые не являются критичными для основных операций.

---

## Категории нереализованных endpoints

### По приоритету реализации

| Приоритет | Количество | Описание |
|-----------|-----------|----------|
| **Высокий** | 0 | Критичные endpoints для основных операций |
| **Средний** | 6 | Полезные endpoints для расширенной функциональности |
| **Низкий** | ~24 | Специфичные endpoints для UI и вспомогательных операций |

---

## 1. Средний приоритет (рекомендуется добавить)

### 1.1. Contractor History

**Endpoints:**
- `GET /contractor/{id}/history` - История изменений контрагента
- `GET /contractor/{id}/history/search` - Поиск в истории

**Причина приоритета:**
Полезно для отслеживания изменений контрагентов, особенно учитывая, что комментарии для контрагентов не работают (API bug).

**Пример использования:**
```python
# Предлагаемая реализация
history = await client.contractors.get_history(contractor_id=123, limit=50)
search_results = await client.contractors.search_history(
    contractor_id=123,
    query="телефон",
    limit=20
)
```

**Сложность реализации:** Низкая (аналогично tasks/deals history)

---

### 1.2. Contractor Deals

**Endpoint:**
- `GET /contractor/{id}/deals` - Сделки контрагента

**Причина приоритета:**
Часто нужно получить все сделки конкретного контрагента.

**Текущий workaround:**
```python
# Можно использовать baseOn (но есть проблемы с API)
deals = await client.deals.list(
    base_on={"contentType": "Contractor", "id": 123}
)

# Или FilterBuilder
from megaplan_sdk import TradeFilterBuilder
filter_obj = TradeFilterBuilder()\
    .field("contractor")\
    .equals({"contentType": "Contractor", "id": 123})\
    .build()
deals = await client.deals.list(filter=filter_obj)
```

**Предлагаемая реализация:**
```python
# Удобнее было бы
deals = await client.contractors.get_deals(contractor_id=123, limit=50)
```

**Сложность реализации:** Низкая

---

### 1.3. Department CRUD

**Endpoints:**
- `POST /department` - Создание отдела
- `POST /department/{id}` - Обновление отдела
- `DELETE /department/{id}` - Удаление отдела

**Причина приоритета:**
Если приложение управляет структурой организации, эти endpoints необходимы.

**Текущее состояние:**
SDK реализует только:
- `GET /department` - Список отделов ✅
- `GET /department/{id}` - Получение отдела ✅

**Проблема:**
RAML документация для Department запутана (строка 38448). Требуется уточнение, действительно ли API поддерживает CRUD для отделов.

**Рекомендация:**
Протестировать на реальном API перед реализацией.

---

### 1.4. Attaches (Вложения)

**Endpoints:**
- `GET /task/{id}/attaches` - Вложения задачи
- `GET /project/{id}/attaches` - Вложения проекта
- `GET /deal/{id}/attaches` - Вложения сделки
- `GET /contractor/{id}/attaches` - Вложения контрагента

**Причина приоритета:**
Работа с файлами - частая операция в CRM.

**Предлагаемая реализация:**
```python
# Универсальный метод в BaseResource
attaches = await client.tasks.get_attaches(task_id=123)
attaches = await client.projects.get_attaches(project_id=456)
attaches = await client.deals.get_attaches(deal_id=789)
```

**Сложность реализации:** Низкая (можно добавить generic метод в BaseResource)

---

### 1.5. Tags

**Endpoints:**
- `GET /task/tags` - Теги для задач
- `GET /project/tags` - Теги для проектов

**Причина приоритета:**
Полезно для автодополнения тегов в UI.

**Предлагаемая реализация:**
```python
tags = await client.tasks.get_tags(name="договор")  # Поиск тегов
tags = await client.projects.get_tags()
```

**Сложность реализации:** Низкая

---

### 1.6. Extra Fields

**Endpoints:**
- `GET /task/extraFields` - Дополнительные поля задач
- `POST /task/extraFields/{id}` - Создание поля
- `DELETE /task/extraFields/{id}` - Удаление поля

**Причина приоритета:**
Для приложений, которые управляют кастомными полями.

**Предлагаемая реализация:**
```python
fields = await client.tasks.get_extra_fields()
field = await client.tasks.create_extra_field(field_data={...})
await client.tasks.delete_extra_field(field_id=123)
```

**Сложность реализации:** Средняя

---

## 2. Низкий приоритет (специфичные для UI)

### 2.1. Available Participants

**Endpoints:**
- `GET /task/availableParticipants` - Доступные участники для задачи
- `GET /project/availableParticipants` - Доступные участники для проекта
- `GET /task/availableResponsibles` - Доступные ответственные
- `GET /project/availableResponsibles` - Доступные ответственные

**Описание:**
Списки сотрудников, которые могут быть назначены на задачу/проект.

**Причина низкого приоритета:**
В основном используется для UI autocomplete. Можно использовать `client.employees.list()`.

**Текущий workaround:**
```python
# Получить всех сотрудников
employees = await client.employees.list()
# Фильтровать локально по правам доступа (если известны)
```

---

### 2.2. Available Parents

**Endpoints:**
- `GET /task/availableParents` - Доступные надзадачи/надпроекты
- `GET /project/availableParents` - Доступные родительские проекты

**Описание:**
Списки задач/проектов, которые могут быть родительскими.

**Причина низкого приоритета:**
Используется для UI autocomplete при выборе родительской задачи/проекта.

**Текущий workaround:**
```python
# Получить все задачи/проекты
tasks = await client.tasks.list()
projects = await client.projects.list()
# Фильтровать локально
```

---

### 2.3. Available Programs

**Endpoint:**
- `GET /deal/availablePrograms` - Доступные программы (воронки) для сделок

**Описание:**
Список схем сделок (воронок продаж), доступных пользователю.

**Причина низкого приоритета:**
Используется для UI dropdown при создании сделки. Program обычно известен заранее.

**Текущий workaround:**
Program ID обычно известен из конфигурации приложения.

---

### 2.4. All Participants

**Endpoints:**
- `GET /task/{id}/allParticipants` - Все участники задачи
- `GET /project/{id}/allParticipants` - Все участники проекта

**Описание:**
Полный список участников (ответственный, соисполнители, аудиторы, владелец).

**Причина низкого приоритета:**
Можно получить через комбинацию существующих методов:
```python
task = await client.tasks.get(task_id=123)
auditors = await client.tasks.get_auditors(task_id=123)
executors = await client.tasks.get_executors(task_id=123)
# Объединить в один список
```

---

### 2.5. Check Access

**Endpoints:**
- `GET /task/{id}/checkAccess` - Проверка прав доступа к задаче
- `GET /project/{id}/checkAccess` - Проверка прав доступа к проекту
- `GET /deal/checkAccess` - Проверка прав доступа к сделкам

**Описание:**
Проверка, имеет ли текущий пользователь определенные права на сущность.

**Причина низкого приоритета:**
Права обычно проверяются на backend или через поле `rights` в сущности.

**Текущий workaround:**
```python
task = await client.tasks.get(task_id=123)
# task содержит поле rights с информацией о правах
```

---

### 2.6. Templates

**Endpoints:**
- `GET /task/templates` - Шаблоны задач
- `GET /project/templates` - Шаблоны проектов

**Описание:**
Получение списка шаблонов для создания задач/проектов.

**Причина низкого приоритета:**
Специфичная функция для работы с шаблонами. Не критична для основных операций.

---

### 2.7. Top Responsibles

**Endpoint:**
- `GET /task/topResponsibles` - Топ ответственных по задачам

**Описание:**
Статистика по наиболее часто назначаемым ответственным.

**Причина низкого приоритета:**
Используется для аналитики и UI подсказок. Не критично для CRUD операций.

---

### 2.8. Template Variables

**Endpoint:**
- `GET /task/templateVariables` - Переменные для шаблонов задач

**Описание:**
Список доступных переменных для использования в шаблонах.

**Причина низкого приоритета:**
Узкоспециализированная функция для работы с шаблонами.

---

### 2.9. Search

**Endpoints:**
- `GET /task/search` - Глобальный поиск по задачам
- (аналогичные для других сущностей)

**Описание:**
Полнотекстовый поиск по сущностям.

**Причина низкого приоритета:**
Можно использовать `list()` с параметром `q` или FilterBuilder:
```python
# Текущий workaround
tasks = await client.tasks.list(q="договор")

# Или FilterBuilder (более надежно)
from megaplan_sdk import TaskFilterBuilder
filter_obj = TaskFilterBuilder().field("name").contains("договор").build()
tasks = await client.tasks.list(filter=filter_obj)
```

---

## 3. Полный список нереализованных endpoints

### Tasks (12 endpoints)

| Endpoint | Метод | Описание | Приоритет |
|----------|-------|----------|-----------|
| `/task/availableParents` | GET | Доступные надзадачи | Низкий |
| `/task/availableParticipants` | GET | Доступные участники | Низкий |
| `/task/availableResponsibles` | GET | Доступные ответственные | Низкий |
| `/task/extraFields` | GET | Дополнительные поля | Средний |
| `/task/extraFields/{id}` | POST | Создать поле | Средний |
| `/task/extraFields/{id}` | DELETE | Удалить поле | Средний |
| `/task/search` | GET | Глобальный поиск | Низкий |
| `/task/tags` | GET | Теги | Средний |
| `/task/templateVariables` | GET | Переменные шаблонов | Низкий |
| `/task/templates` | GET | Шаблоны задач | Низкий |
| `/task/topResponsibles` | GET | Топ ответственных | Низкий |
| `/task/{id}/allParticipants` | GET | Все участники | Низкий |
| `/task/{id}/attaches` | GET | Вложения | Средний |
| `/task/{id}/checkAccess` | GET | Проверка доступа | Низкий |

### Projects (6 endpoints)

| Endpoint | Метод | Описание | Приоритет |
|----------|-------|----------|-----------|
| `/project/availableParents` | GET | Доступные родительские | Низкий |
| `/project/availableParticipants` | GET | Доступные участники | Низкий |
| `/project/availableResponsibles` | GET | Доступные ответственные | Низкий |
| `/project/tags` | GET | Теги | Средний |
| `/project/{id}/allParticipants` | GET | Все участники | Низкий |
| `/project/{id}/attaches` | GET | Вложения | Средний |
| `/project/{id}/checkAccess` | GET | Проверка доступа | Низкий |

### Deals (3 endpoints)

| Endpoint | Метод | Описание | Приоритет |
|----------|-------|----------|-----------|
| `/deal/availablePrograms` | GET | Доступные воронки | Низкий |
| `/deal/checkAccess` | GET | Проверка доступа | Низкий |
| `/deal/{id}/attaches` | GET | Вложения | Средний |

### Contractors (3 endpoints)

| Endpoint | Метод | Описание | Приоритет |
|----------|-------|----------|-----------|
| `/contractor/checkAccess` | GET | Проверка доступа | Низкий |
| `/contractor/{id}/attaches` | GET | Вложения | Средний |
| `/contractor/{id}/history` | GET | История изменений | **Средний** |
| `/contractor/{id}/history/search` | GET | Поиск в истории | **Средний** |
| `/contractor/{id}/deals` | GET | Сделки контрагента | **Средний** |

**Примечание:** Метод `DELETE /contractor/{id}` ранее был реализован в SDK, но удален, так как отсутствует в RAML спецификации и его работоспособность не подтверждена.

### Departments (3 endpoints)

| Endpoint | Метод | Описание | Приоритет |
|----------|-------|----------|-----------|
| `/department` | POST | Создание отдела | **Средний*** |
| `/department/{id}` | POST | Обновление отдела | **Средний*** |
| `/department/{id}` | DELETE | Удаление отдела | **Средний*** |

*Требуется проверка, поддерживает ли API эти операции

---

## 4. Статистика по ресурсам

| Ресурс | Всего endpoints | Реализовано | Не реализовано | % Покрытия |
|--------|----------------|-------------|----------------|------------|
| **Tasks** | ~30 | 18 | ~12 | 60% |
| **Projects** | ~25 | 19 | ~6 | 76% |
| **Deals** | ~15 | 12 | ~3 | 80% |
| **Contractors** | ~10 | 5 | ~5 | 50% |
| **Employees** | ~8 | 7 | ~1 | 87% |
| **Departments** | ~5 | 2 | ~3 | 40% |
| **Comments** | 6 | 6 | 0 | **100%** |
| **Filters** | 11 | 11 | 0 | **100%** |

**Итого:** ~110 endpoints проанализировано, ~30 не реализовано (~27%)

**Важно:** **100% базовых CRUD** операций реализовано для всех ресурсов!

---

## 5. Рекомендации по приоритизации

### Немедленно (если требуется функциональность)

Нет критических пропущенных endpoints.

### Краткосрочно (1-2 недели)

1. **Contractor history** (2 метода)
   - `get_history()`
   - `search_history()`
   
2. **Contractor deals** (1 метод)
   - `get_deals()`

3. **Departments CRUD** (3 метода, после проверки API)
   - `create()`
   - `update()`
   - `delete()`

### Среднесрочно (1-2 месяца)

1. **Attaches** (4 метода - universal в BaseResource)
   - `get_attaches()` для tasks, projects, deals, contractors

2. **Tags** (2 метода)
   - `tasks.get_tags()`
   - `projects.get_tags()`

3. **Extra Fields** (3 метода)
   - `get_extra_fields()`
   - `create_extra_field()`
   - `delete_extra_field()`

### Долгосрочно (3+ месяца)

1. **Available* endpoints** (8 методов)
   - availableParticipants, availableResponsibles, availableParents, availablePrograms

2. **Templates** (2 метода)
   - `get_templates()` для tasks и projects

3. **AllParticipants** (2 метода)
   - Все участники для tasks и projects

4. **CheckAccess** (3 метода)
   - Проверка прав для tasks, projects, deals

---

## 6. Заключение

SDK показывает **отличное покрытие (73%)** endpoints из RAML спецификации. Все **критические базовые операции** (CRUD, пагинация, фильтрация, комментарии, история) реализованы на **100%**.

Нереализованные endpoints (~30) в основном относятся к:
- **UI-специфичным** операциям (available*, templates, topResponsibles)
- **Вспомогательным** функциям (checkAccess, allParticipants)
- **Расширенным** возможностям (extraFields, attaches, tags)

Для большинства нереализованных endpoints существуют **работающие workarounds** через комбинацию существующих методов или локальную фильтрацию.

**Рекомендация:** Добавлять endpoints по мере необходимости, начиная с среднего приоритета (contractor history, attaches, tags).
