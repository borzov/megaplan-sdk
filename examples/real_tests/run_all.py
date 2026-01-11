"""Run all integration tests with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from megaplan_sdk import setup_logging

from utils import load_env_file, print_header, print_success, print_warning

# Import read-only test runner
from run_read_only import run_all_read_only_tests

# Import write test runner
from run_write import run_all_write_tests


async def run_all_integration_tests():
    """Run all integration tests (read-only and optionally write)."""
    print("\n" + "=" * 70)
    print("  ЗАПУСК ВСЕХ ИНТЕГРАЦИОННЫХ ТЕСТОВ MEGAPLAN SDK")
    print("=" * 70)

    load_env_file()
    setup_logging("WARNING")

    # Always run read-only tests
    print("\n📖 Запуск READ-ONLY тестов...\n")
    read_only_success = await run_all_read_only_tests()

    # Ask about write tests
    print("\n" + "=" * 70)
    print("\n⚠️  WRITE тесты создают, модифицируют и удаляют объекты!")
    print("   Хотите запустить write тесты? (yes/no): ", end="")
    response = input().strip().lower()

    write_success = True
    if response in ("yes", "y", "да", "д"):
        print("\n✏️  Запуск WRITE тестов...\n")
        write_success = await run_all_write_tests()
    else:
        print("\n⏭️  WRITE тесты пропущены.")

    # Final summary
    print_header("ФИНАЛЬНАЯ СТАТИСТИКА")

    print("\n📊 Результаты:")
    print(f"   Read-only тесты: {'✅ УСПЕШНО' if read_only_success else '❌ ПРОВАЛЕНО'}")
    if response in ("yes", "y", "да", "д"):
        print(f"   Write тесты: {'✅ УСПЕШНО' if write_success else '❌ ПРОВАЛЕНО'}")

    all_passed = read_only_success and write_success
    if all_passed:
        print_success("\nВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО! 🎉🎉🎉")
    else:
        print_warning("\nНекоторые тесты провалились")

    return all_passed


if __name__ == "__main__":
    print("\n💡 Убедитесь, что создан файл .env в examples/real_tests/ с настройками:")
    print("   MEGAPLAN_BASE_URL=https://company.megaplan.ru")
    print("   MEGAPLAN_USERNAME=user@example.com")
    print("   MEGAPLAN_PASSWORD=your_password\n")
    print("⏱️  Тестирование может занять несколько минут...\n")

    success = asyncio.run(run_all_integration_tests())
    sys.exit(0 if success else 1)
