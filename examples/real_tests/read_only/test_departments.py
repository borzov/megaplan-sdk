"""Integration tests for Departments resource with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from megaplan_sdk import MegaplanClient, setup_logging

from utils import (
    get_credentials,
    load_env_file,
    print_header,
    print_success,
    print_warning,
)


async def test_list_departments():
    """Test listing departments."""
    print_header("TEST: Получение списка отделов")

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
            print("\n⏳ Загрузка первых 10 отделов...")
            departments = await client.departments.list(limit=10)
            print_success(f"Загружено отделов: {len(departments)}")

            if departments:
                print("\n🏢 Список отделов:")
                for i, department in enumerate(departments, 1):
                    print(f"  {i}. [{department.id}] {department.name}")
            else:
                print_warning("Отделов не найдено")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке списка отделов: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_department():
    """Test getting department by ID."""
    print_header("TEST: Получение отдела по ID")

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
            departments = await client.departments.list(limit=1)
            if not departments:
                print_warning("Нет доступных отделов для тестирования")
                return False

            department_id = departments[0].id
            print(f"\n⏳ Загрузка отдела с ID {department_id}...")
            department = await client.departments.get(department_id)

            print(f"\n🏢 Информация об отделе:")
            print(f"   ID: {department.id}")
            print(f"   Название: {department.name}")
            if department.parent:
                print(f"   Родительский отдел: {department.parent.id}")

            print_success(f"Отдел {department_id} загружен")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке отдела: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all department tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: ОТДЕЛЫ (DEPARTMENTS)")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: List departments
    results.append(await test_list_departments())

    # Test 2: Get department by ID
    results.append(await test_get_department())

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
