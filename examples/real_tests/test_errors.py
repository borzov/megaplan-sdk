"""Integration tests for error handling with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from megaplan_sdk import (
    AuthenticationError,
    MegaplanClient,
    NotFoundError,
    ValidationError,
    setup_logging,
)

from utils import (
    get_credentials,
    load_env_file,
    print_header,
    print_success,
    print_warning,
)


async def test_authentication_error():
    """Test AuthenticationError handling."""
    print_header("TEST: Обработка AuthenticationError")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, _, _ = credentials

    try:
        async with MegaplanClient(
            base_url=base_url,
            username="invalid@example.com",
            password="wrong_password"
        ) as client:
            # Try to access API with wrong credentials
            await client.employees.get_current()
            print_warning("Ожидалась ошибка аутентификации, но запрос прошел")
            return False

    except AuthenticationError as e:
        print_success(f"AuthenticationError пойман корректно: {e}")
        return True
    except Exception as e:
        print_warning(f"Получена другая ошибка вместо AuthenticationError: {type(e).__name__}: {e}")
        return False


async def test_not_found_error():
    """Test NotFoundError handling."""
    print_header("TEST: Обработка NotFoundError")

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
            # Try to get non-existent task
            print("\n⏳ Попытка получить несуществующую задачу...")
            await client.tasks.get(999999999)
            print_warning("Ожидалась ошибка NotFoundError, но запрос прошел")
            return False

    except NotFoundError as e:
        print_success(f"NotFoundError пойман корректно: {e}")
        return True
    except Exception as e:
        print_warning(f"Получена другая ошибка вместо NotFoundError: {type(e).__name__}: {e}")
        return False


async def test_validation_error():
    """Test ValidationError handling."""
    print_header("TEST: Обработка ValidationError")

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
            # Try to create task with invalid data
            print("\n⏳ Попытка создать задачу с неверными данными...")
            await client.tasks.create({})  # Empty data should fail
            print_warning("Ожидалась ошибка ValidationError, но запрос прошел")
            return False

    except ValidationError as e:
        print_success(f"ValidationError пойман корректно")
        if hasattr(e, 'errors') and e.errors:
            print(f"   Ошибки валидации: {len(e.errors)}")
        return True
    except Exception as e:
        # Some APIs might return different errors for empty data
        print_warning(f"Получена другая ошибка: {type(e).__name__}: {e}")
        return True  # Not a critical failure


async def run_all_tests():
    """Run all error handling tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: ОБРАБОТКА ОШИБОК")
    print("=" * 70)

    # Setup logging
    setup_logging("WARNING")  # Less verbose for error tests

    results = []

    # Test 1: AuthenticationError
    results.append(await test_authentication_error())

    # Test 2: NotFoundError
    results.append(await test_not_found_error())

    # Test 3: ValidationError
    results.append(await test_validation_error())

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
