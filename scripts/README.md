# Скрипты для разработки

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
