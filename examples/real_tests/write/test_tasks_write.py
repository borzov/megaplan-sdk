"""Write tests for Tasks resource (create/update/delete)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from megaplan_sdk import MegaplanClient, setup_logging

from utils import (
    get_credentials,
    load_env_file,
    print_header,
    print_success,
    print_warning,
)

from .utils import TestObjectTracker, generate_test_name


async def test_create_task():
    """Test creating a task."""
    print_header("TEST: Создание задачи")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials
    tracker = TestObjectTracker()

    try:
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password
        ) as client:
            task_name = generate_test_name("TASK")
            print(f"\n⏳ Создание задачи '{task_name}'...")

            task = await client.tasks.create({"name": task_name})
            tracker.add_task(task.id)

            print_success(f"Задача создана: ID={task.id}, Name={task.name}")

            # Verify creation
            retrieved = await client.tasks.get(task.id)
            if retrieved.name == task_name:
                print_success("Задача успешно создана и проверена")
                return True
            else:
                print_warning(f"Имя задачи не совпадает: ожидалось '{task_name}', получено '{retrieved.name}'")
                return False

    except Exception as e:
        print(f"\n❌ Ошибка при создании задачи: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await tracker.cleanup_all(client)


async def test_create_simple_task():
    """Test creating a simple task."""
    print_header("TEST: Упрощенное создание задачи")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials
    tracker = TestObjectTracker()

    try:
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password
        ) as client:
            task_name = generate_test_name("SIMPLE")
            print(f"\n⏳ Упрощенное создание задачи '{task_name}'...")

            task = await client.tasks.create_simple(task_name, employees_resource=client.employees)
            tracker.add_task(task.id)

            print_success(f"Задача создана: ID={task.id}, Name={task.name}")

            # Verify creation
            retrieved = await client.tasks.get(task.id)
            if retrieved.name == task_name:
                print_success("Задача успешно создана")
                return True
            else:
                return False

    except Exception as e:
        print(f"\n❌ Ошибка при создании задачи: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await tracker.cleanup_all(client)


async def test_update_task():
    """Test updating a task."""
    print_header("TEST: Обновление задачи")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials
    tracker = TestObjectTracker()

    try:
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password
        ) as client:
            # Create task first
            task_name = generate_test_name("UPDATE")
            task = await client.tasks.create({"name": task_name})
            tracker.add_task(task.id)

            # Update task
            new_name = generate_test_name("UPDATED")
            print(f"\n⏳ Обновление задачи #{task.id}...")
            updated = await client.tasks.update(task.id, {"name": new_name})

            if updated.name == new_name:
                print_success("Задача успешно обновлена")

                # Verify update
                retrieved = await client.tasks.get(task.id)
                if retrieved.name == new_name:
                    print_success("Обновление проверено")
                    return True
                else:
                    return False
            else:
                return False

    except Exception as e:
        print(f"\n❌ Ошибка при обновлении задачи: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await tracker.cleanup_all(client)


async def test_delete_task():
    """Test deleting a task."""
    print_header("TEST: Удаление задачи")

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
            # Create task
            task_name = generate_test_name("DELETE")
            task = await client.tasks.create({"name": task_name})
            task_id = task.id

            print(f"\n⏳ Удаление задачи #{task_id}...")
            await client.tasks.delete(task_id)
            print_success("Задача удалена")

            # Verify deletion
            try:
                await client.tasks.get(task_id)
                print_warning("Задача все еще существует после удаления")
                return False
            except Exception:
                print_success("Удаление проверено (задача не найдена)")
                return True

    except Exception as e:
        print(f"\n❌ Ошибка при удалении задачи: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_create_comment():
    """Test creating a task comment."""
    print_header("TEST: Создание комментария к задаче")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials
    tracker = TestObjectTracker()

    try:
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password
        ) as client:
            # Create task first
            task = await client.tasks.create({"name": generate_test_name("COMMENT")})
            tracker.add_task(task.id)

            # Create comment
            comment_text = generate_test_name("COMMENT_TEXT")
            print(f"\n⏳ Создание комментария к задаче #{task.id}...")
            comment = await client.comments.create(
                entity_id=task.id, content=comment_text, entity_type="task"
            )
            tracker.add_comment(comment.id)

            print_success(f"Комментарий создан: ID={comment.id}")

            # Verify comment
            comments = await client.tasks.get_comments(task.id)
            if any(c.id == comment.id for c in comments):
                print_success("Комментарий успешно создан и проверен")
                return True
            else:
                return False

    except Exception as e:
        print(f"\n❌ Ошибка при создании комментария: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await tracker.cleanup_all(client)


async def run_all_tests():
    """Run all task write tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: ЗАДАЧИ (WRITE OPERATIONS)")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: Create task
    results.append(await test_create_task())

    # Test 2: Create simple task
    results.append(await test_create_simple_task())

    # Test 3: Update task
    results.append(await test_update_task())

    # Test 4: Delete task
    results.append(await test_delete_task())

    # Test 5: Create comment
    results.append(await test_create_comment())

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
    print("\n⚠️  ВНИМАНИЕ: Эти тесты создают, модифицируют и удаляют объекты в вашем Megaplan!")
    print("   Убедитесь, что вы используете тестовый аккаунт.\n")
    print("💡 Для запуска создайте файл .env в examples/real_tests/ с настройками:\n")
    print("   MEGAPLAN_BASE_URL=https://company.megaplan.ru")
    print("   MEGAPLAN_USERNAME=user@example.com")
    print("   MEGAPLAN_PASSWORD=your_password\n")

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
