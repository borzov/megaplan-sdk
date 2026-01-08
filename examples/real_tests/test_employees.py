"""Integration tests for Employee resource with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from megaplan_sdk import MegaplanClient, setup_logging

from utils import (
    get_credentials,
    get_department_display,
    get_employee_display,
    load_env_file,
    print_header,
    print_success,
    print_warning,
)


async def test_get_current_user():
    """Test getting current authenticated user."""
    print_header("TEST: Получение текущего пользователя")

    # Load credentials
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
            # Get current user
            current_user = await client.employees.get_current()

            print(f"\n👤 Текущий пользователь:")
            print(f"   ID: {current_user.id}")
            print(f"   Имя: {current_user.first_name} {current_user.last_name}")
            if current_user.email:
                print(f"   Email: {current_user.email}")
            if current_user.position:
                print(f"   Должность: {current_user.position}")
            if current_user.department:
                dept_name = await get_department_display(client, current_user.department)
                print(f"   Отдел: {dept_name}")

            print_success("Текущий пользователь загружен")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при получении текущего пользователя: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_list_employees():
    """Test listing employees."""
    print_header("TEST: Получение списка сотрудников")

    # Load credentials
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
            # Get first 10 employees with expanded department
            print("\n⏳ Загрузка первых 10 сотрудников (с автоматической подгрузкой отделов)...")
            employees = await client.employees.list(limit=10, expand=["department", "manager"])
            print_success(f"Загружено сотрудников: {len(employees)}")

            print("\n👥 Список сотрудников:")
            for i, employee in enumerate(employees, 1):
                # Use display_name() helper method
                print(f"  {i}. [{employee.id}] {employee.display_name()}")
                if employee.email:
                    print(f"     Email: {employee.email}")
                if employee.department and hasattr(employee.department, 'name'):
                    print(f"     Отдел: {employee.department.name}")
                if employee.manager and hasattr(employee.manager, 'display_name'):
                    print(f"     Руководитель: {employee.manager.display_name()}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке списка сотрудников: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_employee():
    """Test getting employee by ID."""
    print_header("TEST: Получение сотрудника по ID")

    # Load credentials
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
            # First get current user to have a valid ID
            current_user = await client.employees.get_current()
            employee_id = current_user.id

            print(f"\n⏳ Загрузка сотрудника с ID {employee_id}...")
            employee = await client.employees.get(employee_id)

            print(f"\n👤 Информация о сотруднике:")
            print(f"   ID: {employee.id}")
            print(f"   Имя: {employee.first_name} {employee.last_name}")
            if employee.middle_name:
                print(f"   Отчество: {employee.middle_name}")
            if employee.email:
                print(f"   Email: {employee.email}")
            if employee.phone:
                print(f"   Телефон: {employee.phone}")
            if employee.position:
                print(f"   Должность: {employee.position}")
            if employee.department:
                dept_name = await get_department_display(client, employee.department)
                print(f"   Отдел: {dept_name}")
            if employee.manager:
                manager_name = await get_employee_display(client, employee.manager)
                print(f"   Руководитель: {manager_name}")

            print_success(f"Сотрудник {employee_id} загружен")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке сотрудника: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_search_employees():
    """Test searching employees by query."""
    print_header("TEST: Поиск сотрудников")

    # Load credentials
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
            # Get current user to search for their name
            current_user = await client.employees.get_current()
            search_query = current_user.first_name or "test"

            print(f"\n⏳ Поиск сотрудников по запросу: '{search_query}'...")
            employees = await client.employees.list(q=search_query, limit=5)
            print_success(f"Найдено сотрудников: {len(employees)}")

            if employees:
                print(f"\n🔍 Результаты поиска по '{search_query}':")
                for i, employee in enumerate(employees, 1):
                    name = f"{employee.first_name or ''} {employee.last_name or ''}".strip()
                    position = employee.position or "Должность не указана"
                    print(f"  {i}. [{employee.id}] {name} - {position}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при поиске сотрудников: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all employee tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: СОТРУДНИКИ (EMPLOYEES)")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: Get current user
    results.append(await test_get_current_user())

    # Test 2: List employees
    results.append(await test_list_employees())

    # Test 3: Get employee by ID
    results.append(await test_get_employee())

    # Test 4: Search employees
    results.append(await test_search_employees())

    # Print summary
    print_header("ИТОГОВАЯ СТАТИСТИКА")
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Результаты тестирования:")
    print(f"   Всего тестов: {total}")
    print(f"   Успешно: {passed}")
    print(f"   Провалено: {total - passed}")

    if passed == total:
        print_success("ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО! 🎉")
        return True
    else:
        print_warning(f"Некоторые тесты провалились ({total - passed}/{total})")
        return False


if __name__ == "__main__":
    print("\n💡 Способы запуска:\n")
    print("1️⃣  Используя .env файл (рекомендуется):")
    print("   Создайте файл examples/real_tests/.env со следующим содержимым:")
    print("   MEGAPLAN_BASE_URL=https://company.megaplan.ru")
    print("   MEGAPLAN_USERNAME=user@example.com")
    print("   MEGAPLAN_PASSWORD=your_password")
    print("   Затем запустите: python3 test_employees.py\n")
    print("2️⃣  Через переменные окружения:")
    print("   MEGAPLAN_BASE_URL='https://company.megaplan.ru' \\")
    print("   MEGAPLAN_USERNAME='user@example.com' \\")
    print("   MEGAPLAN_PASSWORD='your_password' \\")
    print("   python3 test_employees.py\n")

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
