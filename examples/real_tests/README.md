# Integration Tests for Megaplan SDK

Интеграционные тесты для проверки работы SDK с реальным API Megaplan.

## Структура тестов

Тесты разделены на две группы:

### Read-only тесты (`read_only/`)

Тесты, которые только читают данные и не изменяют их. Безопасны для запуска на любом аккаунте.

- **test_tasks.py** - тесты для работы с задачами (Tasks)
- **test_projects.py** - тесты для работы с проектами (Projects)
- **test_deals.py** - тесты для работы со сделками (Deals)
- **test_employees.py** - тесты для работы с сотрудниками (Employees)
- **test_contractors.py** - тесты для работы с контрагентами (Contractors)
- **test_filters.py** - тесты для работы с фильтрами (Filters)
- **test_departments.py** - тесты для работы с отделами (Departments)
- **test_cache.py** - тесты кэширования сущностей
- **test_helpers.py** - тесты helper-функций
- **test_errors.py** - тесты обработки ошибок
- **test_client_config.py** - тесты настройки клиента
- **test_auth.py** - тесты авторизации

### Write тесты (`write/`)

Тесты, которые создают, модифицируют и удаляют объекты. **Требуют подтверждения перед запуском.**

- **test_tasks_write.py** - тесты создания/обновления/удаления задач
- **test_projects_write.py** - тесты создания/обновления/удаления проектов
- **test_deals_write.py** - тесты создания/обновления/удаления сделок
- **test_comments_write.py** - тесты обновления/удаления комментариев
- **utils.py** - утилиты для отслеживания и очистки созданных объектов

## Настройка

### 1. Создайте файл `.env`

Создайте файл `.env` в папке `examples/real_tests/`:

```bash
MEGAPLAN_BASE_URL=https://yourcompany.megaplan.ru
MEGAPLAN_USERNAME=your@email.com
MEGAPLAN_PASSWORD=your_password
```

**ВАЖНО:**
- Файл `.env` не должен попадать в git (уже добавлен в .gitignore)
- Если в пароле есть спецсимволы, они будут корректно обработаны
- Для write тестов используйте **тестовый аккаунт**, не production!

### 2. Убедитесь, что SDK установлен

```bash
cd /Users/borzov/Develop/Public/megaplan-sdk
pip install -e .
```

## Запуск тестов

### Запуск всех тестов

```bash
cd examples/real_tests
python3 run_all.py
```

Этот скрипт:
1. Запустит все read-only тесты автоматически
2. Спросит подтверждение перед запуском write тестов

### Запуск только read-only тестов

```bash
cd examples/real_tests
python3 run_read_only.py
```

Безопасно для любого аккаунта - только чтение данных.

### Запуск только write тестов

```bash
cd examples/real_tests
python3 run_write.py
```

**⚠️ ВНИМАНИЕ:** Эти тесты создают, модифицируют и удаляют объекты! Требуется подтверждение.

### Запуск отдельных тестов

Вы можете запустить тесты для конкретного ресурса:

```bash
# Read-only тесты
cd examples/real_tests/read_only
python3 test_tasks.py
python3 test_projects.py
python3 test_deals.py
python3 test_employees.py
python3 test_contractors.py
python3 test_filters.py
python3 test_departments.py
python3 test_cache.py
python3 test_helpers.py
python3 test_errors.py
python3 test_client_config.py
python3 test_auth.py

# Write тесты (требуют подтверждения)
cd examples/real_tests/write
python3 test_tasks_write.py
python3 test_projects_write.py
python3 test_deals_write.py
python3 test_comments_write.py
```

## Что тестируется

### Read-only тесты

#### Employees (Сотрудники)
- ✅ Получение текущего пользователя (`get_current`)
- ✅ Получение списка сотрудников (`list`)
- ✅ Получение сотрудника по ID (`get`)
- ✅ Поиск сотрудников (`list` с параметром `q`)
- ✅ Автоматическая пагинация (`iterate`)
- ✅ Пагинация (`page_after`, `page_before`, `page_with`)
- ✅ Автоматическая подгрузка связанных сущностей (`expand`)

#### Tasks (Задачи)
- ✅ Получение списка задач (`list`)
- ✅ Получение задачи по ID (`get`)
- ✅ Получение комментариев к задаче (`get_comments`)
- ✅ Получение полной информации о задаче (`get_full_details`)
- ✅ Автоматическая пагинация (`iterate`)
- ✅ Фильтрация через FilterBuilder (`filter`)
- ✅ Фильтрация по статусам (`statuses`)
- ✅ Пагинация
- ✅ Получение подзадач (`get_sub_tasks`, `get_actual_sub_tasks`)
- ✅ Получение задач на уровне дерева (`tree_level`)
- ✅ Получение аудиторов, соисполнителей, вех, истории

#### Deals (Сделки)
- ✅ Получение списка сделок (`list`)
- ✅ Получение сделки по ID (`get`)
- ✅ Получение комментариев к сделке (`get_comments`)
- ✅ Получение полной информации о сделке (`get_full_details`)
- ✅ Автоматическая пагинация (`iterate`)
- ✅ Фильтрация через FilterBuilder (`filter`)
- ✅ Фильтрация по базовой сущности (`base_on`)
- ✅ Пагинация
- ✅ Получение аудиторов, истории статусов, истории изменений
- ✅ Проверка существования (`check_exists`)

#### Projects (Проекты)
- ✅ Получение списка проектов (`list`)
- ✅ Получение проекта по ID (`get`)
- ✅ Получение задач проекта (`get_issues`, `get_actual_issues`)
- ✅ Получение сделок проекта (`get_deals`)
- ✅ Получение полной информации о проекте (`get_full_details`)
- ✅ Автоматическая пагинация (`iterate`)
- ✅ Автоматическая подгрузка связанных сущностей (`expand`)
- ✅ Пагинация
- ✅ Получение аудиторов, соисполнителей, вех, истории

#### Contractors (Контрагенты)
- ✅ Получение списка контрагентов (`list`)
- ✅ Получение контрагента по ID (`get`)
- ✅ Поиск контрагентов (`list` с параметром `q`)
- ✅ Автоматическая пагинация (`iterate`)
- ✅ Пагинация

#### Departments (Отделы)
- ✅ Получение списка отделов (`list`)
- ✅ Получение отдела по ID (`get`)

#### Filters (Фильтры)
- ✅ Получение списка фильтров (`list`)
- ✅ Получение фильтра по ID (`get`)
- ✅ Создание фильтра (`create`)
- ✅ Получение настроек фильтра (`get_settings`)
- ✅ Получение доступных ответственных (`get_available_responsibles`)
- ✅ Получение переменных формул (`get_formula_variables`)

#### Общие возможности
- ✅ Кэширование сущностей (базовая работа, TTL, LRU, очистка)
- ✅ Helper-функции (`make_employee_entity`, `make_task_entity`, etc.)
- ✅ Обработка ошибок (`AuthenticationError`, `NotFoundError`, `ValidationError`)
- ✅ Настройка клиента (`timeout`, `max_retries`, дефолтные лимиты)
- ✅ Ручное управление токенами (`authenticate`, `refresh_token`, `set_access_token`)

### Write тесты

#### Tasks (Задачи)
- ✅ Создание задачи (`create`)
- ✅ Упрощенное создание (`create_simple`)
- ✅ Обновление задачи (`update`)
- ✅ Удаление задачи (`delete`)
- ✅ Создание комментария (`comments.create`)

#### Projects (Проекты)
- ✅ Создание проекта (`create`)
- ✅ Упрощенное создание (`create_simple`)
- ✅ Обновление проекта (`update`)
- ✅ Удаление проекта (`delete`)
- ✅ Создание комментария (`comments.create`)

#### Deals (Сделки)
- ✅ Создание сделки (`create`)
- ✅ Обновление сделки (`update`)
- ✅ Удаление сделки (`delete`)
- ✅ Создание комментария (`comments.create`)

#### Comments (Комментарии)
- ✅ Обновление комментария (`update`)
- ✅ Удаление комментария (`delete`)

## Особенности write тестов

Write тесты автоматически:
1. **Создают** тестовые объекты с уникальными именами (префикс `[TEST]`)
2. **Проверяют** создание и модификацию
3. **Удаляют** все созданные объекты в конце (cleanup)

Если тест падает, cleanup все равно выполняется благодаря `try/finally`.

Для очистки оставшихся тестовых объектов можно использовать функцию `cleanup_orphaned_test_objects()` из `write/utils.py`.

## Примеры вывода

### Успешный тест
```
======================================================================
  ТЕСТИРОВАНИЕ: СОТРУДНИКИ (EMPLOYEES)
======================================================================

👤 Текущий пользователь:
   ID: 1000003
   Имя: Максим Борзов
   Email: m.borzov@example.com
   Должность: Генеральный директор

✅ Текущий пользователь загружен

======================================================================
  ИТОГОВАЯ СТАТИСТИКА
======================================================================

📊 Результаты тестирования:
   Всего тестов: 6
   Успешно: 6
   Провалено: 0

✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО! 🎉
```

## Устранение неполадок

### Ошибка 401 (Unauthorized)
Проверьте правильность учетных данных в `.env` файле.

### Ошибка 404 (Not Found)
Убедитесь, что в вашем аккаунте Megaplan есть данные для тестирования (задачи, проекты, сделки и т.д.).

### Тайм-аут соединения
Проверьте доступность вашего Megaplan инстанса по URL из `MEGAPLAN_BASE_URL`.

### Тесты падают с ValidationError
Это может означать несоответствие модели SDK и реальных данных API. Откройте issue в репозитории с подробным описанием ошибки.

### Write тесты не удаляют объекты
Если write тесты падают, некоторые объекты могут остаться. Используйте функцию `cleanup_orphaned_test_objects()` для очистки.

## Логирование

По умолчанию тесты используют уровень логирования `INFO`. Вы можете изменить уровень в коде тестов:

```python
setup_logging("DEBUG")  # Подробное логирование
setup_logging("WARNING")  # Только предупреждения и ошибки
```

## Безопасность

**⚠️ ВАЖНО:**
- Никогда не коммитьте файл `.env` в git
- **Не используйте production аккаунт для write тестов**
- Read-only тесты безопасны для любого аккаунта
- Write тесты требуют подтверждения перед запуском
- Все созданные write тестами объекты имеют префикс `[TEST]` для легкой идентификации

## Разработка новых тестов

### Добавление read-only теста

1. Создайте функцию в соответствующем файле `read_only/test_*.py`
2. Добавьте вызов функции в `run_all_tests()`
3. Используйте утилиты из `utils.py` для единообразного вывода

Пример:
```python
async def test_my_feature():
    """Test description."""
    print_header("TEST: My Feature")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password
        ) as client:
            # Your test code here
            result = await client.resource.method()
            print_success("Test passed")
            return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
```

### Добавление write теста

1. Создайте функцию в соответствующем файле `write/test_*_write.py`
2. Используйте `TestObjectTracker` для отслеживания созданных объектов
3. Всегда используйте `try/finally` для cleanup
4. Используйте `generate_test_name()` для уникальных имен

Пример:
```python
async def test_create_entity():
    """Test creating an entity."""
    print_header("TEST: Создание сущности")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials
    tracker = TestObjectTracker()

    try:
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password
        ) as client:
            entity_name = generate_test_name("ENTITY")
            entity = await client.resource.create({"name": entity_name})
            tracker.add_entity(entity.id)

            # Verify creation
            retrieved = await client.resource.get(entity.id)
            if retrieved.name == entity_name:
                print_success("Сущность создана")
                return True
            return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        await tracker.cleanup_all(client)
```

## Лицензия

Тесты распространяются под той же лицензией, что и Megaplan SDK.
