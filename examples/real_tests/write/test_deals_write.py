"""Write tests for Deals resource (create/update/delete)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from megaplan_sdk import MegaplanClient, setup_logging

from utils import get_credentials, load_env_file, print_header, print_success, print_warning
from .utils import TestObjectTracker, generate_test_name


async def test_create_deal():
    """Test creating a deal."""
    print_header("TEST: Создание сделки")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials
    tracker = TestObjectTracker()

    try:
        async with MegaplanClient(base_url=base_url, username=username, password=password) as client:
            # Get a program for the deal
            deals = await client.deals.list(limit=1)
            if not deals:
                print_warning("Нет доступных сделок для получения программы")
                return False

            program = deals[0].program
            if not program:
                print_warning("Нет доступной программы для создания сделки")
                return False

            deal_name = generate_test_name("DEAL")
            print(f"\n⏳ Создание сделки '{deal_name}'...")

            deal = await client.deals.create({"name": deal_name, "program": {"contentType": program.contentType, "id": program.id}})
            tracker.add_deal(deal.id)

            print_success(f"Сделка создана: ID={deal.id}, Name={deal.name}")

            retrieved = await client.deals.get(deal.id)
            if retrieved.name == deal_name:
                print_success("Сделка успешно создана и проверена")
                return True
            return False

    except Exception as e:
        print(f"\n❌ Ошибка при создании сделки: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await tracker.cleanup_all(client)


async def test_update_deal():
    """Test updating a deal."""
    print_header("TEST: Обновление сделки")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials
    tracker = TestObjectTracker()

    try:
        async with MegaplanClient(base_url=base_url, username=username, password=password) as client:
            # Get program
            deals = await client.deals.list(limit=1)
            if not deals or not deals[0].program:
                print_warning("Нет доступной программы")
                return False

            program = deals[0].program
            deal = await client.deals.create({
                "name": generate_test_name("UPDATE"),
                "program": {"contentType": program.contentType, "id": program.id}
            })
            tracker.add_deal(deal.id)

            new_name = generate_test_name("UPDATED")
            print(f"\n⏳ Обновление сделки #{deal.id}...")
            updated = await client.deals.update(deal.id, {"name": new_name})

            if updated.name == new_name:
                retrieved = await client.deals.get(deal.id)
                if retrieved.name == new_name:
                    print_success("Сделка успешно обновлена")
                    return True
            return False

    except Exception as e:
        print(f"\n❌ Ошибка при обновлении сделки: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await tracker.cleanup_all(client)


async def test_delete_deal():
    """Test deleting a deal."""
    print_header("TEST: Удаление сделки")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        async with MegaplanClient(base_url=base_url, username=username, password=password) as client:
            deals = await client.deals.list(limit=1)
            if not deals or not deals[0].program:
                print_warning("Нет доступной программы")
                return False

            program = deals[0].program
            deal = await client.deals.create({
                "name": generate_test_name("DELETE"),
                "program": {"contentType": program.contentType, "id": program.id}
            })
            deal_id = deal.id

            print(f"\n⏳ Удаление сделки #{deal_id}...")
            await client.deals.delete(deal_id)
            print_success("Сделка удалена")

            try:
                await client.deals.get(deal_id)
                print_warning("Сделка все еще существует")
                return False
            except Exception:
                print_success("Удаление проверено")
                return True

    except Exception as e:
        print(f"\n❌ Ошибка при удалении сделки: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all deal write tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: СДЕЛКИ (WRITE OPERATIONS)")
    print("=" * 70)

    setup_logging("INFO")
    results = []

    results.append(await test_create_deal())
    results.append(await test_update_deal())
    results.append(await test_delete_deal())

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
    print("\n⚠️  ВНИМАНИЕ: Эти тесты создают, модифицируют и удаляют объекты!")
    print("💡 Для запуска создайте файл .env в examples/real_tests/ с настройками:\n")
    print("   MEGAPLAN_BASE_URL=https://company.megaplan.ru")
    print("   MEGAPLAN_USERNAME=user@example.com")
    print("   MEGAPLAN_PASSWORD=your_password\n")

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
