#!/bin/bash
# Convenience script to run integration tests

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Use virtual environment Python if available
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="python3"
fi

cd "$SCRIPT_DIR"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Создайте файл .env на основе .env.template:"
    echo "  cp .env.template .env"
    echo "И заполните ваши учетные данные Megaplan"
    exit 1
fi

# Run tests based on argument
case "$1" in
    employees)
        echo "🧑 Запуск тестов: Сотрудники (Employees)"
        $PYTHON test_employees.py
        ;;
    tasks)
        echo "📋 Запуск тестов: Задачи (Tasks)"
        $PYTHON test_tasks.py
        ;;
    deals)
        echo "💼 Запуск тестов: Сделки (Deals)"
        $PYTHON test_deals.py
        ;;
    projects)
        echo "📁 Запуск тестов: Проекты (Projects)"
        $PYTHON test_projects.py
        ;;
    contractors)
        echo "🏢 Запуск тестов: Контрагенты (Contractors)"
        $PYTHON test_contractors.py
        ;;
    all|"")
        echo "🚀 Запуск всех интеграционных тестов"
        $PYTHON run_all.py
        ;;
    *)
        echo "Использование: $0 [employees|tasks|deals|projects|contractors|all]"
        echo ""
        echo "Примеры:"
        echo "  $0              # Запустить все тесты"
        echo "  $0 all          # Запустить все тесты"
        echo "  $0 employees    # Только тесты сотрудников"
        echo "  $0 tasks        # Только тесты задач"
        echo "  $0 deals        # Только тесты сделок"
        echo "  $0 projects     # Только тесты проектов"
        echo "  $0 contractors  # Только тесты контрагентов"
        exit 1
        ;;
esac
