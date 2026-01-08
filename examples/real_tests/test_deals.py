"""Integration tests for Deals resource with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from megaplan_sdk import MegaplanClient, setup_logging

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
                include_related_tasks=False,  # TODO: Fix HTTP 422 error
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
