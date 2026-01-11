"""Integration tests for helper functions with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from megaplan_sdk import (
    MegaplanClient,
    make_contractor_entity,
    make_deal_entity,
    make_employee_entity,
    make_project_entity,
    make_task_entity,
    setup_logging,
)

from utils import (
    get_credentials,
    load_env_file,
    print_header,
    print_success,
    print_warning,
)


async def test_make_employee_entity():
    """Test make_employee_entity helper."""
    print_header("TEST: Helper функция make_employee_entity")

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
            # Get a real employee ID
            employees = await client.employees.list(limit=1)
            if not employees:
                print_warning("Нет доступных сотрудников для тестирования")
                return False

            employee_id = employees[0].id
            print(f"\n⏳ Создание BaseEntity для сотрудника #{employee_id}...")
            entity = make_employee_entity(employee_id)

            print(f"   contentType: {entity.contentType}")
            print(f"   id: {entity.id}")

            if entity.contentType == "Employee" and entity.id == employee_id:
                print_success("Helper функция работает корректно")
                return True
            else:
                print_warning("Helper функция вернула неверные данные")
                return False

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании helper функции: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_make_task_entity():
    """Test make_task_entity helper."""
    print_header("TEST: Helper функция make_task_entity")

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
            tasks = await client.tasks.list(limit=1)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            task_id = tasks[0].id
            print(f"\n⏳ Создание BaseEntity для задачи #{task_id}...")
            entity = make_task_entity(task_id)

            print(f"   contentType: {entity.contentType}")
            print(f"   id: {entity.id}")

            if entity.contentType == "Task" and entity.id == task_id:
                print_success("Helper функция работает корректно")
                return True
            else:
                print_warning("Helper функция вернула неверные данные")
                return False

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании helper функции: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_make_project_entity():
    """Test make_project_entity helper."""
    print_header("TEST: Helper функция make_project_entity")

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
            projects = await client.projects.list(limit=1)
            if not projects:
                print_warning("Нет доступных проектов для тестирования")
                return False

            project_id = projects[0].id
            print(f"\n⏳ Создание BaseEntity для проекта #{project_id}...")
            entity = make_project_entity(project_id)

            print(f"   contentType: {entity.contentType}")
            print(f"   id: {entity.id}")

            if entity.contentType == "Project" and entity.id == project_id:
                print_success("Helper функция работает корректно")
                return True
            else:
                print_warning("Helper функция вернула неверные данные")
                return False

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании helper функции: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_make_deal_entity():
    """Test make_deal_entity helper."""
    print_header("TEST: Helper функция make_deal_entity")

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
            deals = await client.deals.list(limit=1)
            if not deals:
                print_warning("Нет доступных сделок для тестирования")
                return False

            deal_id = deals[0].id
            print(f"\n⏳ Создание BaseEntity для сделки #{deal_id}...")
            entity = make_deal_entity(deal_id)

            print(f"   contentType: {entity.contentType}")
            print(f"   id: {entity.id}")

            if entity.contentType == "Deal" and entity.id == deal_id:
                print_success("Helper функция работает корректно")
                return True
            else:
                print_warning("Helper функция вернула неверные данные")
                return False

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании helper функции: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_make_contractor_entity():
    """Test make_contractor_entity helper."""
    print_header("TEST: Helper функция make_contractor_entity")

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
            contractors = await client.contractors.list(limit=1)
            if not contractors:
                print_warning("Нет доступных контрагентов для тестирования")
                return False

            contractor_id = contractors[0].id
            print(f"\n⏳ Создание BaseEntity для контрагента #{contractor_id}...")
            entity = make_contractor_entity(contractor_id)

            print(f"   contentType: {entity.contentType}")
            print(f"   id: {entity.id}")

            # Contractor can be ContractorCompany or ContractorHuman
            if entity.contentType in ("ContractorCompany", "ContractorHuman") and entity.id == contractor_id:
                print_success("Helper функция работает корректно")
                return True
            else:
                print_warning("Helper функция вернула неверные данные")
                return False

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании helper функции: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all helper function tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: HELPER ФУНКЦИИ")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: make_employee_entity
    results.append(await test_make_employee_entity())

    # Test 2: make_task_entity
    results.append(await test_make_task_entity())

    # Test 3: make_project_entity
    results.append(await test_make_project_entity())

    # Test 4: make_deal_entity
    results.append(await test_make_deal_entity())

    # Test 5: make_contractor_entity
    results.append(await test_make_contractor_entity())

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
    print("\n💡 Для запуска создайте файл .env в examples/real_tests/ с настройками:\n")
    print("   MEGAPLAN_BASE_URL=https://company.megaplan.ru")
    print("   MEGAPLAN_USERNAME=user@example.com")
    print("   MEGAPLAN_PASSWORD=your_password\n")

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
