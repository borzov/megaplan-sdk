"""Integration tests for Tasks resource with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from megaplan_sdk import MegaplanClient, setup_logging

from utils import (
    get_comment_owner_display,
    get_credentials,
    get_employee_display,
    load_env_file,
    print_header,
    print_success,
    print_warning,
)


async def test_list_tasks():
    """Test listing tasks."""
    print_header("TEST: Получение списка задач")

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
            # Get first 10 tasks with expanded responsible and owner
            print("\n⏳ Загрузка первых 10 задач (с автоматической подгрузкой ответственных)...")
            tasks_full = await client.tasks.list(limit=10, expand=["responsible", "owner"])
            print_success(f"Загружено задач: {len(tasks_full)}")

            print("\n📋 Список задач:")
            for i, task_full in enumerate(tasks_full, 1):
                task = task_full.task
                print(f"  {i}. [{task.id}] {task.name}")
                print(f"     Статус: {task.status}")
                if task_full.responsible_details:
                    print(f"     Ответственный: {task_full.responsible_details.display_name()}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке списка задач: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_task():
    """Test getting task by ID."""
    print_header("TEST: Получение задачи по ID")

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
            # First get a task from list
            tasks = await client.tasks.list(limit=1)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            task_id = tasks[0].id
            print(f"\n⏳ Загрузка задачи с ID {task_id}...")
            task = await client.tasks.get(task_id)

            print(f"\n📋 Информация о задаче:")
            print(f"   ID: {task.id}")
            print(f"   Название: {task.name}")
            print(f"   Статус: {task.status}")
            if task.description:
                desc = task.description[:100] + "..." if len(task.description) > 100 else task.description
                print(f"   Описание: {desc}")
            if task.responsible:
                resp_name = await get_employee_display(client, task.responsible)
                print(f"   Ответственный: {resp_name}")
            if task.owner:
                owner_name = await get_employee_display(client, task.owner)
                print(f"   Постановщик: {owner_name}")
            if task.deadline:
                print(f"   Дедлайн: {task.deadline}")

            print_success(f"Задача {task_id} загружена")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке задачи: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_task_comments():
    """Test getting task comments."""
    print_header("TEST: Получение комментариев к задаче")

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
            # First get a task from list
            tasks = await client.tasks.list(limit=5)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            # Find task with comments
            task_id = None
            for task in tasks:
                try:
                    comments = await client.tasks.get_comments(task.id, limit=1)
                    if comments:
                        task_id = task.id
                        break
                except Exception:
                    continue

            if not task_id:
                print_warning("Не найдено задач с комментариями")
                return False

            print(f"\n⏳ Загрузка комментариев для задачи #{task_id}...")
            comments = await client.tasks.get_comments(task_id, limit=10)
            print_success(f"Загружено комментариев: {len(comments)}")

            if comments:
                print(f"\n💬 Комментарии к задаче #{task_id}:")
                for i, comment in enumerate(comments[:5], 1):
                    print(f"\n  {i}. Комментарий #{comment.id}")
                    owner_name = await get_comment_owner_display(client, comment)
                    print(f"     Автор: {owner_name}")
                    if comment.content:
                        text_preview = comment.content[:80]
                        if len(comment.content) > 80:
                            text_preview += "..."
                        print(f"     Текст: {text_preview}")
                    if comment.created_at:
                        print(f"     Дата: {comment.created_at}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке комментариев: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_full_details():
    """Test getting full task details."""
    print_header("TEST: Получение полной информации о задаче")

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
            # First get a task from list
            tasks = await client.tasks.list(limit=1)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            task_id = tasks[0].id
            print(f"\n⏳ Загрузка полной информации о задаче #{task_id}...")

            details = await client.tasks.get_full_details(
                task_id=task_id,
                include_comments=True,
                include_sub_tasks=True,
                include_responsible_details=True,
                include_owner_details=True,
                comments_limit=5
            )

            print(f"\n📋 Полная информация о задаче:")
            print(f"   ID: {details.task.id}")
            print(f"   Название: {details.task.name}")
            print(f"   Статус: {details.task.status}")

            if details.responsible_details:
                print(f"   Ответственный: {details.responsible_details.display_name()}")

            if details.owner_details:
                print(f"   Постановщик: {details.owner_details.display_name()}")

            if details.comments:
                print(f"\n💬 Комментарии ({len(details.comments)}):")
                for i, comment in enumerate(details.comments[:3], 1):
                    print(f"   {i}. Комментарий #{comment.id}")
                    owner_name = await get_comment_owner_display(client, comment)
                    print(f"      Автор: {owner_name}")

            if details.sub_tasks:
                print(f"\n📋 Подзадачи ({len(details.sub_tasks)}):")
                for i, subtask in enumerate(details.sub_tasks[:3], 1):
                    print(f"   {i}. [{subtask.id}] {subtask.name} ({subtask.status})")

            print_success(f"Полная информация о задаче {task_id} загружена")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке полной информации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all task tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: ЗАДАЧИ (TASKS)")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: List tasks
    results.append(await test_list_tasks())

    # Test 2: Get task by ID
    results.append(await test_get_task())

    # Test 3: Get task comments
    results.append(await test_get_task_comments())

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
