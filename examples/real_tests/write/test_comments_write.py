"""Write tests for Comments resource (update/delete)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from megaplan_sdk import MegaplanClient, setup_logging

from utils import get_credentials, load_env_file, print_header, print_success, print_warning
from .utils import TestObjectTracker, generate_test_name


async def test_update_comment():
    """Test updating a comment."""
    print_header("TEST: Обновление комментария")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials
    tracker = TestObjectTracker()

    try:
        async with MegaplanClient(base_url=base_url, username=username, password=password) as client:
            # Create task and comment
            task = await client.tasks.create({"name": generate_test_name("COMMENT")})
            tracker.add_task(task.id)

            comment = await client.comments.create(
                entity_id=task.id, content=generate_test_name("ORIGINAL"), entity_type="task"
            )
            tracker.add_comment(comment.id)

            # Update comment
            new_content = generate_test_name("UPDATED")
            print(f"\n⏳ Обновление комментария #{comment.id}...")
            updated = await client.comments.update(comment.id, {"content": new_content})

            if updated.content == new_content:
                print_success("Комментарий успешно обновлен")
                return True
            return False

    except Exception as e:
        print(f"\n❌ Ошибка при обновлении комментария: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await tracker.cleanup_all(client)


async def test_delete_comment():
    """Test deleting a comment."""
    print_header("TEST: Удаление комментария")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials
    tracker = TestObjectTracker()

    try:
        async with MegaplanClient(base_url=base_url, username=username, password=password) as client:
            # Create task and comment
            task = await client.tasks.create({"name": generate_test_name("COMMENT")})
            tracker.add_task(task.id)

            comment = await client.comments.create(
                entity_id=task.id, content=generate_test_name("DELETE"), entity_type="task"
            )
            comment_id = comment.id

            print(f"\n⏳ Удаление комментария #{comment_id}...")
            await client.comments.delete(comment_id)
            print_success("Комментарий удален")

            # Verify deletion
            comments = await client.tasks.get_comments(task.id)
            if not any(c.id == comment_id for c in comments):
                print_success("Удаление проверено")
                return True
            return False

    except Exception as e:
        print(f"\n❌ Ошибка при удалении комментария: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await tracker.cleanup_all(client)


async def run_all_tests():
    """Run all comment write tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: КОММЕНТАРИИ (WRITE OPERATIONS)")
    print("=" * 70)

    setup_logging("INFO")
    results = []

    results.append(await test_update_comment())
    results.append(await test_delete_comment())

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
