"""Integration tests for entity caching with real Megaplan API."""

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


async def test_cache_basic():
    """Test basic cache functionality."""
    print_header("TEST: Базовая работа кэша")

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
            enable_cache=True,
            cache_ttl=300,
            cache_max_size=1000
        ) as client:
            # Get current user (will be cached)
            print("\n⏳ Первая загрузка текущего пользователя...")
            user1 = await client.employees.get_current()
            print_success(f"Пользователь загружен: {user1.display_name()}")

            # Get same user again (should use cache)
            print("\n⏳ Вторая загрузка текущего пользователя (должен использоваться кэш)...")
            user2 = await client.employees.get_current()
            print_success(f"Пользователь загружен: {user2.display_name()}")

            # Check cache stats
            if client._cache:
                stats = client._cache.stats()
                print(f"\n📊 Статистика кэша:")
                print(f"   Размер: {stats['size']}")
                print(f"   Типы: {stats['types']}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании кэша: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_with_expand():
    """Test cache with expand parameter."""
    print_header("TEST: Кэш при использовании expand")

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
            enable_cache=True
        ) as client:
            # Load tasks with expand (will cache employees)
            print("\n⏳ Загрузка задач с expand (responsible, owner)...")
            tasks1 = await client.tasks.list(limit=10, expand=["responsible", "owner"])
            print_success(f"Загружено задач: {len(tasks1)}")

            # Load more tasks with same expand (should use cached employees)
            print("\n⏳ Загрузка еще задач с тем же expand (должны использоваться закэшированные сотрудники)...")
            tasks2 = await client.tasks.list(limit=10, expand=["responsible"])
            print_success(f"Загружено задач: {len(tasks2)}")

            # Check cache stats
            if client._cache:
                stats = client._cache.stats()
                print(f"\n📊 Статистика кэша:")
                print(f"   Размер: {stats['size']}")
                print(f"   Типы: {stats['types']}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании кэша с expand: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_clear_cache():
    """Test clearing cache."""
    print_header("TEST: Очистка кэша")

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
            enable_cache=True
        ) as client:
            # Load some entities to populate cache
            print("\n⏳ Загрузка данных для заполнения кэша...")
            await client.employees.get_current()
            await client.employees.list(limit=5)
            await client.departments.list(limit=5)

            if client._cache:
                stats_before = client._cache.stats()
                print(f"   Кэш до очистки: {stats_before['size']} сущностей")

            # Clear all cache
            print("\n⏳ Очистка всего кэша...")
            client.clear_cache()

            if client._cache:
                stats_after = client._cache.stats()
                print_success(f"Кэш после очистки: {stats_after['size']} сущностей")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при очистке кэша: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_clear_cache_type():
    """Test clearing cache for specific type."""
    print_header("TEST: Очистка кэша для конкретного типа")

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
            enable_cache=True
        ) as client:
            # Load different entity types
            print("\n⏳ Загрузка разных типов сущностей...")
            await client.employees.get_current()
            await client.employees.list(limit=5)
            await client.departments.list(limit=5)
            await client.contractors.list(limit=5)

            if client._cache:
                stats_before = client._cache.stats()
                print(f"   Кэш до очистки: {stats_before}")

            # Clear only Employee cache
            print("\n⏳ Очистка кэша для Employee...")
            client.clear_cache_type("Employee")

            if client._cache:
                stats_after = client._cache.stats()
                print_success(f"Кэш после очистки Employee: {stats_after}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при очистке кэша по типу: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_disabled():
    """Test behavior with cache disabled."""
    print_header("TEST: Работа без кэша")

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
            enable_cache=False
        ) as client:
            # Load same entity twice
            print("\n⏳ Первая загрузка текущего пользователя...")
            user1 = await client.employees.get_current()
            print_success(f"Пользователь загружен: {user1.display_name()}")

            print("\n⏳ Вторая загрузка текущего пользователя (без кэша)...")
            user2 = await client.employees.get_current()
            print_success(f"Пользователь загружен: {user2.display_name()}")

            # Cache should be None
            if client._cache is None:
                print_success("Кэш отключен (как и ожидалось)")
            else:
                print_warning("Кэш не отключен, хотя должен быть")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании без кэша: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all cache tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: КЭШИРОВАНИЕ (CACHE)")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: Basic cache
    results.append(await test_cache_basic())

    # Test 2: Cache with expand
    results.append(await test_cache_with_expand())

    # Test 3: Clear cache
    results.append(await test_clear_cache())

    # Test 4: Clear cache type
    results.append(await test_clear_cache_type())

    # Test 5: Cache disabled
    results.append(await test_cache_disabled())

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
