"""Run all write integration tests with real Megaplan API (create/update/delete)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from megaplan_sdk import setup_logging

from utils import load_env_file, print_header, print_success, print_warning

# Import all write test modules
from write.test_comments_write import run_all_tests as run_comments_write_tests
from write.test_deals_write import run_all_tests as run_deals_write_tests
from write.test_projects_write import run_all_tests as run_projects_write_tests
from write.test_tasks_write import run_all_tests as run_tasks_write_tests


async def run_all_write_tests():
    """Run all write integration tests."""
    print("\n" + "=" * 70)
    print("  ЗАПУСК WRITE ИНТЕГРАЦИОННЫХ ТЕСТОВ MEGAPLAN SDK")
    print("=" * 70)

    print("\n⚠️  ВНИМАНИЕ: Эти тесты создают, модифицируют и удаляют объекты!")
    print("   Убедитесь, что вы используете тестовый аккаунт Megaplan.\n")

    response = input("Продолжить? (yes/no): ")
    if response.lower() not in ("yes", "y", "да", "д"):
        print("Тесты отменены.")
        return False

    load_env_file()
    setup_logging("INFO")

    results = {}

    print("\n🚀 Запуск write тестов...\n")

    print("📋 Тестирование: Tasks (write)...")
    results["Tasks"] = await run_tasks_write_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Projects (write)...")
    results["Projects"] = await run_projects_write_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Deals (write)...")
    results["Deals"] = await run_deals_write_tests()
    print("\n" + "-" * 70 + "\n")

    print("📋 Тестирование: Comments (write)...")
    results["Comments"] = await run_comments_write_tests()

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
        print_success("ВСЕ WRITE ТЕСТЫ ПРОШЛИ УСПЕШНО! 🎉🎉🎉")
    else:
        print_warning(f"Некоторые тесты провалились ({total_resources - passed_resources}/{total_resources})")

    return all_passed


if __name__ == "__main__":
    print("\n💡 Убедитесь, что создан файл .env в examples/real_tests/ с настройками:")
    print("   MEGAPLAN_BASE_URL=https://company.megaplan.ru")
    print("   MEGAPLAN_USERNAME=user@example.com")
    print("   MEGAPLAN_PASSWORD=your_password\n")

    success = asyncio.run(run_all_write_tests())
    sys.exit(0 if success else 1)
