# Скрипты для разработки

## verify_contractor_writes.py

Сценарий создаёт тестовую компанию и плательщиков Legal и Natural на выделенном стенде. Для каждого доступного реквизита и поля подписанта он отдельно меняет значение, сравнивает остальные деловые поля и проверяет восстановление. В отчёт попадают также недоступные поля и результат очистки тестовых объектов.

```bash
PYTHONPATH=src .venv/bin/python scripts/verify_contractor_writes.py --env-file /path/to/test.env --allow-test-writes --contractor-type-id 1 --audit-path /tmp/sdk-write-probe.jsonl --actor operator-id
```

Подставьте ID типа контрагента со своего стенда. Авторизация поддерживает MEGAPLAN_URL с MEGAPLAN_USERNAME и MEGAPLAN_PASSWORD либо с MEGAPLAN_ACCESS_TOKEN. [Контракты и ограничения](../examples/cookbook/contractor-profiles.md).

## Проверки чтения 0.8.0

Экспортируйте параметры авторизации для аккаунта с завершёнными задачами, сотрудниками и плательщиками. Набор выбирает контрольные записи из данных этого аккаунта.

```bash
MEGAPLAN_LIVE_READ_080=1 .venv/bin/python -m pytest -o addopts= tests/integration/test_sdk_080_reads.py
```

Для проверки полей конкретного списка запустите `PYTHONPATH=src .venv/bin/python scripts/probe_list_fields.py --help`.

## check.sh - Локальный запуск проверок CI

### Использование

```bash
# Запуск всех проверок
./scripts/check.sh
```

Скрипт выполняет те же проверки, что и CI:
1. ✅ `ruff check` - проверка стиля кода
2. ✅ `ruff format --check` - проверка форматирования
3. ✅ `mypy` - проверка типов
4. ✅ `pytest` - запуск тестов с coverage

### Требования

Убедитесь, что установлены все зависимости:

```bash
pip install -e ".[dev]"
```

### Отдельные команды

Если нужно запустить только одну проверку:

```bash
# Только ruff check
ruff check src/megaplan_sdk

# Только проверка форматирования
ruff format --check src/megaplan_sdk

# Автоматическое исправление форматирования
ruff format src/megaplan_sdk

# Только mypy
mypy src/megaplan_sdk

# Только тесты
pytest --cov=megaplan_sdk --cov-report=term-missing
```
