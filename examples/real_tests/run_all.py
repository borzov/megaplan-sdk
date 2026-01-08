"""Run all integration tests with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from megaplan_sdk import setup_logging

from utils import load_env_file, print_header, print_success, print_warning

# Import all test modules
from test_employees import run_all_tests as run_employee_tests
from test_tasks import run_all_tests as run_task_tests
from test_deals import run_all_tests as run_deal_tests
from test_projects import run_all_tests as run_project_tests
from test_contractors import run_all_tests as run_contractor_tests


async def run_all_integration_tests():
    """Run all integration tests for all resources."""
    print("\n" + "=" * 70)
    print("  ЗАПУСК ВСЕХ ИНТЕГРАЦИОННЫХ ТЕСТОВ MEGAPLAN SDK")
    print("=" * 70)

    # Load environment
    load_env_file()

    # Setup logging
    setup_logging("WARNING")  # Less verbose for full test run

    results = {}

    # Run tests for each resource
    print("\n🚀 Запуск тестов для всех ресурсов...\n")

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

    # Print overall summary
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
        print_success("ВСЕ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ПРОШЛИ УСПЕШНО! 🎉🎉🎉")
    else:
        print_warning(
            f"Некоторые тесты провалились ({total_resources - passed_resources}/{total_resources})"
        )

    return all_passed


if __name__ == "__main__":
    print("\n💡 Убедитесь, что создан файл .env в examples/real_tests/ с настройками:")
    print("   MEGAPLAN_BASE_URL=https://company.megaplan.ru")
    print("   MEGAPLAN_USERNAME=user@example.com")
    print("   MEGAPLAN_PASSWORD=your_password\n")
    print("⏱️  Тестирование может занять несколько минут...\n")

    success = asyncio.run(run_all_integration_tests())
    sys.exit(0 if success else 1)
