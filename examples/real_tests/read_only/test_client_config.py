"""Integration tests for client configuration with real Megaplan API."""

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


async def test_timeout_config():
    """Test timeout configuration."""
    print_header("TEST: Настройка timeout")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password,
            timeout=60.0
        ) as client:
            print("\n⏳ Загрузка данных с timeout=60.0...")
            employees = await client.employees.list(limit=5)
            print_success(f"Загружено сотрудников: {len(employees)}")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании timeout: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_max_retries_config():
    """Test max_retries configuration."""
    print_header("TEST: Настройка max_retries")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password,
            max_retries=5
        ) as client:
            print("\n⏳ Загрузка данных с max_retries=5...")
            employees = await client.employees.list(limit=5)
            print_success(f"Загружено сотрудников: {len(employees)}")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании max_retries: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_default_limits():
    """Test default comments and history limits."""
    print_header("TEST: Глобальные дефолтные лимиты")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password,
            default_comments_limit=10,
            default_history_limit=20
        ) as client:
            print("\n⏳ Загрузка задачи с полной информацией (должны использоваться дефолтные лимиты)...")
            tasks = await client.tasks.list(limit=1)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            details = await client.tasks.get_full_details(
                task_id=tasks[0].id,
                include_comments=True,
                include_history=True
            )

            print_success(f"Загружено комментариев: {len(details.comments) if details.comments else 0}")
            print_success(f"Загружено записей истории: {len(details.history) if details.history else 0}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании дефолтных лимитов: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_default_limits_override():
    """Test that explicit limits override defaults."""
    print_header("TEST: Переопределение дефолтных лимитов")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password,
            default_comments_limit=10,
            default_history_limit=20
        ) as client:
            print("\n⏳ Загрузка задачи с явным лимитом комментариев (должен переопределить дефолт)...")
            tasks = await client.tasks.list(limit=1)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            details = await client.tasks.get_full_details(
                task_id=tasks[0].id,
                include_comments=True,
                comments_limit=5  # Should override default_comments_limit=10
            )

            print_success(f"Загружено комментариев: {len(details.comments) if details.comments else 0}")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании переопределения лимитов: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all client configuration tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: НАСТРОЙКА КЛИЕНТА")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: Timeout config
    results.append(await test_timeout_config())

    # Test 2: Max retries config
    results.append(await test_max_retries_config())

    # Test 3: Default limits
    results.append(await test_default_limits())

    # Test 4: Default limits override
    results.append(await test_default_limits_override())

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
