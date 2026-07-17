"""Integration tests for authentication with real Megaplan API."""

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


async def test_authenticate():
    """Test manual authentication."""
    print_header("TEST: Ручная аутентификация")

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
            print("\n⏳ Выполнение аутентификации...")
            token = await client.auth.authenticate(username, password)
            print_success(f"Токен получен: {token.access_token[:20]}...")

            # Verify token works
            print("\n⏳ Проверка работы токена...")
            user = await client.employees.get_current()
            print_success(f"Токен работает, пользователь: {user.display_name()}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при аутентификации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_refresh_token():
    """Test token refresh."""
    print_header("TEST: Обновление токена")

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
            # First authenticate to get refresh_token
            print("\n⏳ Первичная аутентификация...")
            await client.auth.authenticate(username, password)

            # Get refresh token from auth manager
            refresh_token = client.auth._auth_manager._refresh_token
            if not refresh_token:
                print_warning("Refresh token не получен, пропускаем тест")
                return True  # Not a failure

            print("\n⏳ Обновление токена...")
            new_token = await client.auth.refresh_token(refresh_token)
            print_success(f"Новый токен получен: {new_token.access_token[:20]}...")

            # Verify new token works
            print("\n⏳ Проверка работы нового токена...")
            user = await client.employees.get_current()
            print_success(f"Новый токен работает, пользователь: {user.display_name()}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при обновлении токена: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_set_access_token():
    """Test setting access token manually."""
    print_header("TEST: Установка токена доступа вручную")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        # First get a token
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password
        ) as client1:
            token = await client1.auth.authenticate(username, password)

        # Now use that token in a new client
        async with MegaplanClient(
            base_url=base_url,
            access_token=token.access_token
        ) as client2:
            print("\n⏳ Использование установленного токена...")
            user = await client2.employees.get_current()
            print_success(f"Токен работает, пользователь: {user.display_name()}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при установке токена: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_clear_tokens():
    """Test clearing tokens."""
    print_header("TEST: Очистка токенов")

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
            # Authenticate first
            print("\n⏳ Аутентификация...")
            await client.auth.authenticate(username, password)

            # Clear tokens
            print("\n⏳ Очистка токенов...")
            client.auth.clear_tokens()

            # Verify tokens are cleared
            if client.auth._auth_manager._access_token is None and client.auth._auth_manager._refresh_token is None:
                print_success("Токены очищены")
                return True
            else:
                print_warning("Токены не очищены полностью")
                return False

    except Exception as e:
        print(f"\n❌ Ошибка при очистке токенов: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all authentication tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: АВТОРИЗАЦИЯ")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: Authenticate
    results.append(await test_authenticate())

    # Test 2: Refresh token
    results.append(await test_refresh_token())

    # Test 3: Set access token
    results.append(await test_set_access_token())

    # Test 4: Clear tokens
    results.append(await test_clear_tokens())

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
