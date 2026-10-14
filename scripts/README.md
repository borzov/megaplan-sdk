# Скрипты для разработки

## verify_contractor_writes.py

Opt-in проверка записи на новых объектах «ТЕСТ SDK, не трогать»: частичный POST,
очистка необязательного банка, кастомное поле и замена контактов. Сценарий
удаляет своего плательщика, помечает компанию на удаление и проверяет состояние
автоматического плательщика. При ошибке аудит содержит созданные ID для сверки.

```bash
PYTHONPATH=src .venv/bin/python scripts/verify_contractor_writes.py --allow-test-writes --contractor-type-id 1 --audit-path /tmp/sdk-write-probe.jsonl --actor operator-id
```

Выберите существующий ContractorType ID своего аккаунта; 1 — пример.
Авторизация: MEGAPLAN_URL и MEGAPLAN_USERNAME/MEGAPLAN_PASSWORD либо
MEGAPLAN_ACCESS_TOKEN. Файл .env.local читается без shell source; другой файл
задаётся через --env-file. Секреты не печатаются.
[Контракты и ограничения](../examples/cookbook/contractor-profiles.md).

## check.sh - Локальный запуск проверок CI

Скрипт для запуска всех проверок, которые выполняются в GitHub Actions, локально перед коммитом.

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
ruff check megaplan_sdk

# Только проверка форматирования
ruff format --check megaplan_sdk

# Автоматическое исправление форматирования
ruff format megaplan_sdk

# Только mypy
mypy megaplan_sdk

# Только тесты
pytest --cov=megaplan_sdk --cov-report=term-missing
```
