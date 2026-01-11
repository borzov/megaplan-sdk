"""Integration tests for Deals resource with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from typing import Any

from megaplan_sdk import MegaplanClient, TradeFilterBuilder, setup_logging

from utils import (
    get_comment_owner_display,
    get_contractor_display,
    get_credentials,
    get_employee_display,
    load_env_file,
    print_header,
    print_success,
    print_warning,
)
from .utils_validation import (
    log_api_error,
    validate_base_entity_filter,
    validate_search_results,
)


async def test_list_deals():
    """Test listing deals."""
    print_header("TEST: Получение списка сделок")

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
            # Get first 10 deals with expanded responsible and contractor
            print("\n⏳ Загрузка первых 10 сделок (с автоматической подгрузкой данных)...")
            deals_full = await client.deals.list(limit=10, expand=["responsible", "contractor"])
            print_success(f"Загружено сделок: {len(deals_full)}")

            if deals_full:
                print("\n💼 Список сделок:")
                for i, deal_full in enumerate(deals_full, 1):
                    deal = deal_full.deal
                    print(f"  {i}. [{deal.id}] {deal.name}")
                    if deal.state:
                        print(f"     Статус: {deal.state}")  # Uses __str__ from ProgramState
                    if deal_full.responsible_details:
                        print(f"     Ответственный: {deal_full.responsible_details.display_name()}")
                    if deal_full.contractor_details:
                        print(f"     Контрагент: {deal_full.contractor_details.display_name()}")
            else:
                print_warning("Сделок не найдено")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке списка сделок: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_deal():
    """Test getting deal by ID."""
    print_header("TEST: Получение сделки по ID")

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
            # First get a deal from list
            deals = await client.deals.list(limit=1)
            if not deals:
                print_warning("Нет доступных сделок для тестирования")
                return False

            deal_id = deals[0].id
            print(f"\n⏳ Загрузка сделки с ID {deal_id}...")
            deal = await client.deals.get(deal_id)

            print(f"\n💼 Информация о сделке:")
            print(f"   ID: {deal.id}")
            print(f"   Название: {deal.name}")
            if deal.state:
                print(f"   Статус: {deal.state}")
            if deal.description:
                desc = deal.description[:100] + "..." if len(deal.description) > 100 else deal.description
                print(f"   Описание: {desc}")
            if deal.responsible:
                resp_name = await get_employee_display(client, deal.responsible)
                print(f"   Ответственный: {resp_name}")
            if deal.contractor:
                contractor_name = await get_contractor_display(client, deal.contractor)
                print(f"   Контрагент: {contractor_name}")
            if deal.sum_base:
                print(f"   Сумма: {deal.sum_base}")

            print_success(f"Сделка {deal_id} загружена")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке сделки: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_deal_comments():
    """Test getting deal comments."""
    print_header("TEST: Получение комментариев к сделке")

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
            # First get a deal from list
            deals = await client.deals.list(limit=5)
            if not deals:
                print_warning("Нет доступных сделок для тестирования")
                return False

            # Find deal with comments
            deal_id = None
            for deal in deals:
                try:
                    comments = await client.deals.get_comments(deal.id, limit=1)
                    if comments:
                        deal_id = deal.id
                        break
                except Exception:
                    continue

            if not deal_id:
                # Use first deal anyway
                deal_id = deals[0].id

            print(f"\n⏳ Загрузка комментариев для сделки #{deal_id}...")
            comments = await client.deals.get_comments(deal_id, limit=10)
            print_success(f"Загружено комментариев: {len(comments)}")

            if comments:
                print(f"\n💬 Комментарии к сделке #{deal_id}:")
                for i, comment in enumerate(comments[:5], 1):
                    print(f"\n  {i}. Комментарий #{comment.id}")
                    owner_name = await get_comment_owner_display(client, comment)
                    print(f"     Автор: {owner_name}")
                    if comment.content:
                        text_preview = comment.content[:80]
                        if len(comment.content) > 80:
                            text_preview += "..."
                        print(f"     Текст: {text_preview}")
            else:
                print("\n💬 Комментариев нет")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке комментариев: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_full_details():
    """Test getting full deal details."""
    print_header("TEST: Получение полной информации о сделке")

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
            # First get a deal from list
            deals = await client.deals.list(limit=1)
            if not deals:
                print_warning("Нет доступных сделок для тестирования")
                return False

            deal_id = deals[0].id
            print(f"\n⏳ Загрузка полной информации о сделке #{deal_id}...")

            details = await client.deals.get_full_details(
                deal_id=deal_id,
                include_comments=True,
                include_related_tasks=True,
                include_responsible_details=True,
                include_contractor_details=True,
                comments_limit=5
            )

            print(f"\n💼 Полная информация о сделке:")
            print(f"   ID: {details.deal.id}")
            print(f"   Название: {details.deal.name}")
            if details.deal.state:
                print(f"   Статус: {details.deal.state}")  # Uses __str__ from ProgramState

            if details.responsible_details:
                print(f"   Ответственный: {details.responsible_details.display_name()}")

            if details.contractor_details:
                print(f"   Контрагент: {details.contractor_details.display_name()}")

            if details.comments:
                print(f"\n💬 Комментарии ({len(details.comments)}):")
                for i, comment in enumerate(details.comments[:3], 1):
                    print(f"   {i}. Комментарий #{comment.id}")
                    owner_name = await get_comment_owner_display(client, comment)
                    print(f"      Автор: {owner_name}")

            if details.related_tasks:
                print(f"\n📋 Связанные задачи ({len(details.related_tasks)}):")
                for i, task in enumerate(details.related_tasks[:3], 1):
                    print(f"   {i}. [{task.id}] {task.name}")

            print_success(f"Полная информация о сделке {deal_id} загружена")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке полной информации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_iterate_deals():
    """Test iterating over deals."""
    print_header("TEST: Автоматическая пагинация сделок (iterate)")

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
            print("\n⏳ Итерация по сделкам (первые 15)...")
            count = 0
            async for deal in client.deals.iterate(limit=10):
                count += 1
                if count <= 5:
                    print(f"  {count}. [{deal.id}] {deal.name}")
                if count >= 15:
                    break

            print_success(f"Обработано сделок: {count}")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при итерации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_filter_builder():
    """Test filtering deals with FilterBuilder."""
    print_header("TEST: Фильтрация сделок через FilterBuilder")

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
            deals = await client.deals.list(limit=1)
            if not deals:
                print_warning("Нет доступных сделок для тестирования")
                return False

            deal_name = deals[0].name
            search_word = deal_name.split()[0] if deal_name else "тест"

            print(f"\n⏳ Поиск сделок с названием, содержащим '{search_word}'...")
            filter_obj = TradeFilterBuilder().field("name").contains(search_word).build()
            filtered_deals = await client.deals.list(filter=filter_obj, limit=10)

            print_success(f"Найдено сделок: {len(filtered_deals)}")
            if filtered_deals:
                print("\n💼 Найденные сделки:")
                for i, deal in enumerate(filtered_deals[:5], 1):
                    print(f"  {i}. [{deal.id}] {deal.name}")

                # Validate that all results contain the search term
                is_valid, errors = validate_search_results(
                    filtered_deals, search_word, field_name="name"
                )
                if not is_valid:
                    print_warning("Валидация результатов фильтрации провалилась:")
                    for error in errors:
                        print_warning(f"  - {error}")
                    return False
                print_success("Валидация результатов фильтрации: все результаты содержат поисковое слово")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при фильтрации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_list_with_base_on():
    """Test listing deals with base_on filter."""
    print_header("TEST: Фильтрация сделок по базовой сущности")

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
            # Get a contractor to filter by
            contractors = await client.contractors.list(limit=1)
            if not contractors:
                print_warning("Нет доступных контрагентов для тестирования")
                return False

            contractor_id = contractors[0].id
            print(f"\n⏳ Загрузка сделок для контрагента #{contractor_id}...")
            # Note: API may require base_on in a specific format
            deals = await client.deals.list(
                base_on={"contentType": "Contractor", "id": contractor_id},
                limit=10
            )

            print_success(f"Найдено сделок: {len(deals)}")
            if deals:
                print("\n💼 Сделки:")
                for i, deal in enumerate(deals[:5], 1):
                    print(f"  {i}. [{deal.id}] {deal.name}")

                # Validate that all deals are related to the specified contractor
                base_entity = {"contentType": "Contractor", "id": contractor_id}
                is_valid, errors = validate_base_entity_filter(
                    deals, base_entity, entity_field="contractor"
                )
                if not is_valid:
                    print_warning("Валидация результатов фильтрации по base_on провалилась:")
                    for error in errors:
                        print_warning(f"  - {error}")
                    return False
                print_success("Валидация результатов фильтрации: все сделки связаны с указанным контрагентом")

            return True

    except Exception as e:
        # Log API error with full details
        log_api_error(
            method="GET",
            url=f"{base_url}/api/v3/deal",
            params={"baseOn": {"contentType": "Contractor", "id": contractor_id}},
            error=e,
        )
        raise  # Re-raise to fail the test


async def test_list_with_pagination():
    """Test listing deals with pagination."""
    print_header("TEST: Пагинация сделок")

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
            print("\n⏳ Загрузка первой страницы (5 сделок)...")
            first_page = await client.deals.list(limit=5)
            if not first_page:
                print_warning("Нет доступных сделок для тестирования")
                return False

            print_success(f"Загружено сделок на первой странице: {len(first_page)}")

            if len(first_page) >= 5:
                last_deal = first_page[-1]
                print(f"\n⏳ Загрузка второй страницы (после сделки #{last_deal.id})...")
                second_page = await client.deals.list(
                    limit=5,
                    page_after={"contentType": "Deal", "id": last_deal.id}
                )
                print_success(f"Загружено сделок на второй странице: {len(second_page)}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при пагинации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_auditors():
    """Test getting deal auditors."""
    print_header("TEST: Получение аудиторов сделки")

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
            deals = await client.deals.list(limit=10)
            if not deals:
                print_warning("Нет доступных сделок для тестирования")
                return False

            deal_id = deals[0].id
            print(f"\n⏳ Загрузка аудиторов для сделки #{deal_id}...")
            auditors = await client.deals.get_auditors(deal_id)
            print_success(f"Найдено аудиторов: {len(auditors)}")

            if auditors:
                print("\n👥 Аудиторы:")
                for i, auditor in enumerate(auditors[:5], 1):
                    print(f"  {i}. {auditor}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке аудиторов: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_status_history():
    """Test getting deal status history."""
    print_header("TEST: Получение истории статусов сделки")

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
            deals = await client.deals.list(limit=10)
            if not deals:
                print_warning("Нет доступных сделок для тестирования")
                return False

            deal_id = deals[0].id
            print(f"\n⏳ Загрузка истории статусов для сделки #{deal_id}...")
            status_history = await client.deals.get_status_history(deal_id)
            print_success(f"Найдено записей истории: {len(status_history)}")

            if status_history:
                print("\n📜 История статусов:")
                for i, record in enumerate(status_history[:5], 1):
                    print(f"  {i}. {record}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке истории статусов: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_history():
    """Test getting deal history."""
    print_header("TEST: Получение истории изменений сделки")

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
            deals = await client.deals.list(limit=10)
            if not deals:
                print_warning("Нет доступных сделок для тестирования")
                return False

            deal_id = deals[0].id
            print(f"\n⏳ Загрузка истории для сделки #{deal_id}...")
            history = await client.deals.get_history(deal_id, limit=10)
            print_success(f"Найдено записей истории: {len(history)}")

            if history:
                print("\n📜 История изменений:")
                for i, record in enumerate(history[:5], 1):
                    print(f"  {i}. {record}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке истории: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_check_exists():
    """Test checking if deal exists."""
    print_header("TEST: Проверка существования сделки")

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
            deals = await client.deals.list(limit=1)
            if not deals:
                print_warning("Нет доступных сделок для тестирования")
                return False

            deal = deals[0]
            print(f"\n⏳ Проверка существования сделки '{deal.name}'...")
            
            # Use query parameter for name search
            try:
                exists = await client.deals.check_exists(query=deal.name)
                print_success(f"Сделка существует (поиск по имени): {exists}")
            except Exception as check_error:
                # Log API error with full details
                log_api_error(
                    method="GET",
                    url=f"{base_url}/api/v3/deal/checkDealExist",
                    params={"query": deal.name},
                    error=check_error,
                )
                raise  # Re-raise to fail the test
            
            # Also try with deal object if contractor is available
            if deal.contractor:
                try:
                    deal_obj = {
                        "name": deal.name,
                        "contractor": {
                            "contentType": deal.contractor.content_type,
                            "id": deal.contractor.id
                        }
                    }
                    exists2 = await client.deals.check_exists(deal=deal_obj)
                    print_success(f"Сделка существует (поиск по объекту): {exists2}")
                except Exception as check_error2:
                    # Log API error with full details
                    log_api_error(
                        method="GET",
                        url=f"{base_url}/api/v3/deal/checkDealExist",
                        params={"deal": deal_obj},
                        error=check_error2,
                    )
                    raise  # Re-raise to fail the test

            return True

    except Exception as e:
        # Only allow 405 (Method Not Allowed) as acceptable - means endpoint doesn't exist
        if "405" in str(e) or "Method Not Allowed" in str(e):
            print_warning(f"Метод check_exists не поддерживается API (405): {e}")
            return True  # Not a critical failure - endpoint doesn't exist
        
        # All other errors (422, 500, etc.) should be logged and fail the test
        log_api_error(
            method="GET",
            url=f"{base_url}/api/v3/deal/checkDealExist",
            error=e,
        )
        print(f"\n❌ Ошибка при проверке существования: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all deal tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: СДЕЛКИ (DEALS)")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: List deals
    results.append(await test_list_deals())

    # Test 2: Get deal by ID
    results.append(await test_get_deal())

    # Test 3: Get deal comments
    results.append(await test_get_deal_comments())

    # Test 4: Get full details
    results.append(await test_get_full_details())

    # Test 5: Iterate deals
    results.append(await test_iterate_deals())

    # Test 6: Filter builder
    results.append(await test_filter_builder())

    # Test 7: List with base_on
    results.append(await test_list_with_base_on())

    # Test 8: Pagination
    results.append(await test_list_with_pagination())

    # Test 9: Get auditors
    results.append(await test_get_auditors())

    # Test 10: Get status history
    results.append(await test_get_status_history())

    # Test 11: Get history
    results.append(await test_get_history())

    # Test 12: Check exists
    results.append(await test_check_exists())

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
