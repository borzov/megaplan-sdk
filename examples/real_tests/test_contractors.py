"""Integration tests for Contractors resource with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from megaplan_sdk import MegaplanClient, setup_logging

from utils import get_credentials, load_env_file, print_header, print_success, print_warning


async def test_list_contractors():
    """Test listing contractors."""
    print_header("TEST: Получение списка контрагентов")

    # Load credentials
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
            # Get first 10 contractors
            print("\n⏳ Загрузка первых 10 контрагентов...")
            contractors = await client.contractors.list(limit=10)
            print_success(f"Загружено контрагентов: {len(contractors)}")

            if contractors:
                print("\n🏢 Список контрагентов:")
                for i, contractor in enumerate(contractors, 1):
                    print(f"  {i}. [{contractor.id}] {contractor.name}")
                    if contractor.category:
                        print(f"     Категория: {contractor.category}")
                    if contractor.manager:
                        print(f"     Менеджер: {contractor.manager}")
            else:
                print_warning("Контрагентов не найдено")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке списка контрагентов: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_contractor():
    """Test getting contractor by ID."""
    print_header("TEST: Получение контрагента по ID")

    # Load credentials
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
            # First get a contractor from list
            contractors = await client.contractors.list(limit=1)
            if not contractors:
                print_warning("Нет доступных контрагентов для тестирования")
                return False

            contractor_id = contractors[0].id
            print(f"\n⏳ Загрузка контрагента с ID {contractor_id}...")
            contractor = await client.contractors.get(contractor_id)

            print(f"\n🏢 Информация о контрагенте:")
            print(f"   ID: {contractor.id}")
            print(f"   Название: {contractor.name}")
            if contractor.description:
                desc = contractor.description[:100] + "..." if len(contractor.description) > 100 else contractor.description
                print(f"   Описание: {desc}")
            if contractor.category:
                print(f"   Категория: {contractor.category}")
            if contractor.manager:
                print(f"   Менеджер: {contractor.manager}")
            if contractor.inn:
                print(f"   ИНН: {contractor.inn}")
            if contractor.email:
                print(f"   Email: {contractor.email}")
            if contractor.phone:
                print(f"   Телефон: {contractor.phone}")

            print_success(f"Контрагент {contractor_id} загружен")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке контрагента: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_search_contractors():
    """Test searching contractors by query."""
    print_header("TEST: Поиск контрагентов")

    # Load credentials
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
            # Get a contractor to search for
            contractors_list = await client.contractors.list(limit=1)
            if not contractors_list:
                print_warning("Нет контрагентов для поиска")
                return False

            # Use first word from contractor name as search query
            search_query = contractors_list[0].name.split()[0] if contractors_list[0].name else "test"

            print(f"\n⏳ Поиск контрагентов по запросу: '{search_query}'...")
            contractors = await client.contractors.list(q=search_query, limit=5)
            print_success(f"Найдено контрагентов: {len(contractors)}")

            if contractors:
                print(f"\n🔍 Результаты поиска по '{search_query}':")
                for i, contractor in enumerate(contractors, 1):
                    print(f"  {i}. [{contractor.id}] {contractor.name}")
                    if contractor.category:
                        print(f"     Категория: {contractor.category}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при поиске контрагентов: {e}")
        import traceback
        traceback.print_exc()
        return False


# NOTE: Contractor comments are not supported by Megaplan API (returns 500 error)
# The get_comments() and create_comment() methods have been removed from ContractorsResource
# Use comments on related deals or tasks instead

# async def test_get_contractor_comments():
#     """Test getting contractor comments."""
#     print_header("TEST: Получение комментариев контрагента")
#
#     # Load credentials
#     load_env_file()
#     credentials = get_credentials()
#     if not credentials:
#         return False
#
#     base_url, username, password = credentials
#
#     try:
#         async with MegaplanClient(
#             base_url=base_url,
#             username=username,
#             password=password
#         ) as client:
#             # First get a contractor from list
#             contractors = await client.contractors.list(limit=5)
#             if not contractors:
#                 print_warning("Нет доступных контрагентов для тестирования")
#                 return False
#
#             # Find contractor with comments
#             contractor_id = None
#             for contractor in contractors:
#                 try:
#                     comments = await client.contractors.get_comments(contractor.id, limit=1)
#                     if comments:
#                         contractor_id = contractor.id
#                         break
#                 except Exception:
#                     continue
#
#             if not contractor_id:
#                 # Use first contractor anyway
#                 contractor_id = contractors[0].id
#
#             print(f"\n⏳ Загрузка комментариев для контрагента #{contractor_id}...")
#             comments = await client.contractors.get_comments(contractor_id, limit=10)
#             print_success(f"Загружено комментариев: {len(comments)}")
#
#             if comments:
#                 print(f"\n💬 Комментарии контрагента #{contractor_id}:")
#                 for i, comment in enumerate(comments[:5], 1):
#                     print(f"\n  {i}. Комментарий #{comment.id}")
#                     if comment.owner:
#                         print(f"     Автор: {comment.owner}")
#                     if comment.content:
#                         text_preview = comment.content[:60]
#                         if len(comment.content) > 60:
#                             text_preview += "..."
#                         print(f"     Текст: {text_preview}")
#             else:
#                 print("\n💬 Комментариев нет")
#
#             return True
#
#     except Exception as e:
#         print(f"\n❌ Ошибка при загрузке комментариев контрагента: {e}")
#         import traceback
#         traceback.print_exc()
#         return False


async def run_all_tests():
    """Run all contractor tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: КОНТРАГЕНТЫ (CONTRACTORS)")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: List contractors
    results.append(await test_list_contractors())

    # Test 2: Get contractor by ID
    results.append(await test_get_contractor())

    # Test 3: Search contractors
    results.append(await test_search_contractors())

    # Test 4: Get contractor comments - DISABLED (API returns 500 error)
    # results.append(await test_get_contractor_comments())

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
