#!/bin/bash
# Скрипт для локального запуска всех проверок CI

set -e  # Остановка при первой ошибке

echo "🔍 Запуск проверок CI локально..."
echo ""

# Проверка версий
echo "📋 Версии инструментов:"
python3 --version
ruff --version
mypy --version
pytest --version
echo ""

# Ruff check
echo "✅ Запуск ruff check..."
ruff check megaplan_sdk
echo "✓ ruff check пройден"
echo ""

# Ruff format check
echo "✅ Запуск ruff format check..."
ruff format --check megaplan_sdk
echo "✓ ruff format check пройден"
echo ""

# MyPy
echo "✅ Запуск mypy..."
mypy megaplan_sdk
echo "✓ mypy пройден"
echo ""

# Pytest с coverage
echo "✅ Запуск pytest с coverage..."
pytest --cov=megaplan_sdk --cov-report=term-missing
echo "✓ pytest пройден"
echo ""

echo "🎉 Все проверки пройдены успешно!"
