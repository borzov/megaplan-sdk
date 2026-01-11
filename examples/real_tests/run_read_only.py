"""Run all read-only integration tests with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from megaplan_sdk import setup_logging

from utils import load_env_file, print_header, print_success, print_warning

# Import all read-only test modules
from read_only.test_auth import run_all_tests as run_auth_tests
from read_only.test_cache import run_all_tests as run_cache_tests
from read_only.test_client_config import run_all_tests as run_client_config_tests
from read_only.test_contractors import run_all_tests as run_contractor_tests
from read_only.test_deals import run_all_tests as run_deal_tests
from read_only.test_departments import run_all_tests as run_department_tests
from read_only.test_employees import run_all_tests as run_employee_tests
from read_only.test_errors import run_all_tests as run_error_tests
from read_only.test_filters import run_all_tests as run_filter_tests
from read_only.test_helpers import run_all_tests as run_helper_tests
from read_only.test_projects import run_all_tests as run_project_tests
from read_only.test_tasks import run_all_tests as run_task_tests


async def run_all_read_only_tests():
    """Run all read-only integration tests."""
    print("\n" + "=" * 70)
    print("  ЗАПУСК READ-ONLY ИНТЕГРАЦИОННЫХ ТЕСТОВ MEGAPLAN SDK")
    print("=" * 70)

    load_env_file()
    setup_logging("WARNING")

    results = {}

    print("\n🚀 Запуск read-only тестов...\n")

    print("📋 Тестирование: Employees...")
    results["Employees"] = await run_employee_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Tasks...")
    results["Tasks"] = await run_task_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Deals...")
    results["Deals"] = await run_deal_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Projects...")
    results["Projects"] = await run_project_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Contractors...")
    results["Contractors"] = await run_contractor_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Departments...")
    results["Departments"] = await run_department_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Filters...")
    results["Filters"] = await run_filter_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Cache...")
    results["Cache"] = await run_cache_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Helpers...")
    results["Helpers"] = await run_helper_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Errors...")
    results["Errors"] = await run_error_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Client Config...")
    results["ClientConfig"] = await run_client_config_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Auth...")
    results["Auth"] = await run_auth_tests()

    print_header("ОБЩАЯ ИТОГОВАЯ СТАТИСТИКА")

    print("\n📊 Результаты по ресурсам:")
    passed_resources = 0
    for resource, success in results.items():
        status = "✅ УСПЕШНО" if success else "❌ ПРОВАЛЕНО"
        print(f"   {resource:15} - {status}")
        if success:
            passed_resources += 1

    total_resources = len(results)
    print(f"\n📈 Итого:")
    print(f"   Всего ресурсов протестировано: {total_resources}")
    print(f"   Успешно: {passed_resources}")
    print(f"   Провалено: {total_resources - passed_resources}")

    all_passed = passed_resources == total_resources
    if all_passed:
        print_success("ВСЕ READ-ONLY ТЕСТЫ ПРОШЛИ УСПЕШНО! 🎉🎉🎉")
    else:
        print_warning(f"Некоторые тесты провалились ({total_resources - passed_resources}/{total_resources})")

    return all_passed


if __name__ == "__main__":
    print("\n💡 Убедитесь, что создан файл .env в examples/real_tests/ с настройками:")
    print("   MEGAPLAN_BASE_URL=https://company.megaplan.ru")
    print("   MEGAPLAN_USERNAME=user@example.com")
    print("   MEGAPLAN_PASSWORD=your_password\n")
    print("⏱️  Тестирование может занять несколько минут...\n")

    success = asyncio.run(run_all_read_only_tests())
    sys.exit(0 if success else 1)
