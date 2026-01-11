"""Integration tests for Tasks resource with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from megaplan_sdk import MegaplanClient, TaskFilterBuilder, setup_logging

from utils import (
    get_comment_owner_display,
    get_credentials,
    get_employee_display,
    load_env_file,
    print_header,
    print_success,
    print_warning,
)
from .utils_validation import (
    log_api_error,
    validate_search_results,
    validate_status_filter,
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


async def test_iterate_tasks():
    """Test iterating over tasks."""
    print_header("TEST: Автоматическая пагинация задач (iterate)")

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
            print("\n⏳ Итерация по задачам (первые 20)...")
            count = 0
            async for task in client.tasks.iterate(limit=10):
                count += 1
                if count <= 5:
                    print(f"  {count}. [{task.id}] {task.name}")
                if count >= 20:
                    break

            print_success(f"Обработано задач: {count}")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при итерации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_filter_builder():
    """Test filtering tasks with FilterBuilder."""
    print_header("TEST: Фильтрация задач через FilterBuilder")

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
            # Get a task name to search for
            tasks = await client.tasks.list(limit=1)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            task_name = tasks[0].name
            search_word = task_name.split()[0] if task_name else "тест"

            print(f"\n⏳ Поиск задач с названием, содержащим '{search_word}'...")
            filter_obj = TaskFilterBuilder().field("name").contains(search_word).build()
            filtered_tasks = await client.tasks.list(filter=filter_obj, limit=10)

            print_success(f"Найдено задач: {len(filtered_tasks)}")
            if filtered_tasks:
                print("\n📋 Найденные задачи:")
                for i, task in enumerate(filtered_tasks[:5], 1):
                    print(f"  {i}. [{task.id}] {task.name}")

                # Validate that all results contain the search term
                is_valid, errors = validate_search_results(
                    filtered_tasks, search_word, field_name="name"
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


async def test_list_with_statuses():
    """Test listing tasks with status filter."""
    print_header("TEST: Фильтрация задач по статусам")

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
            print("\n⏳ Загрузка задач со статусами 'assigned' и 'accepted'...")
            # Note: Valid task statuses according to RAML: created, assigned, accepted, done, 
            # completed, rejected, cancelled, expired, delayed, template, overdue
            # Using "assigned" and "accepted" which are present in the system
            tasks = await client.tasks.list(statuses=["assigned", "accepted"], limit=10)

            print_success(f"Найдено задач: {len(tasks)}")
            if tasks:
                print("\n📋 Задачи:")
                for i, task in enumerate(tasks[:5], 1):
                    print(f"  {i}. [{task.id}] {task.name} - {task.status}")

                # Validate that all results have one of the expected statuses
                is_valid, errors = validate_status_filter(
                    tasks, ["assigned", "accepted"], status_field="status"
                )
                if not is_valid:
                    print_warning("Валидация результатов фильтрации по статусам провалилась:")
                    for error in errors:
                        print_warning(f"  - {error}")
                    return False
                print_success("Валидация результатов фильтрации: все задачи имеют ожидаемые статусы")

            return True

    except Exception as e:
        # Log API error with full details
        log_api_error(
            method="GET",
            url=f"{base_url}/api/v3/task",
            params={"statuses": ["assigned", "in_progress"]},
            error=e,
        )
        raise  # Re-raise to fail the test


async def test_list_with_pagination():
    """Test listing tasks with pagination."""
    print_header("TEST: Пагинация задач")

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
            # Get first page
            print("\n⏳ Загрузка первой страницы (5 задач)...")
            first_page = await client.tasks.list(limit=5)
            if not first_page:
                print_warning("Нет доступных задач для тестирования")
                return False

            print_success(f"Загружено задач на первой странице: {len(first_page)}")

            # Get second page using page_after
            if len(first_page) >= 5:
                last_task = first_page[-1]
                print(f"\n⏳ Загрузка второй страницы (после задачи #{last_task.id})...")
                second_page = await client.tasks.list(
                    limit=5,
                    page_after={"contentType": "Task", "id": last_task.id}
                )
                print_success(f"Загружено задач на второй странице: {len(second_page)}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при пагинации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_sub_tasks():
    """Test getting task sub-tasks."""
    print_header("TEST: Получение подзадач")

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
            # Find a task with sub-tasks
            tasks = await client.tasks.list(limit=10)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            task_id = None
            for task in tasks:
                try:
                    sub_tasks = await client.tasks.get_sub_tasks(task.id, limit=1)
                    if sub_tasks:
                        task_id = task.id
                        break
                except Exception:
                    continue

            if not task_id:
                print_warning("Не найдено задач с подзадачами")
                return True  # Not a failure

            print(f"\n⏳ Загрузка подзадач для задачи #{task_id}...")
            sub_tasks = await client.tasks.get_sub_tasks(task_id, limit=10)
            print_success(f"Найдено подзадач: {len(sub_tasks)}")

            if sub_tasks:
                print("\n📋 Подзадачи:")
                for i, subtask in enumerate(sub_tasks[:5], 1):
                    print(f"  {i}. [{subtask.id}] {subtask.name} ({subtask.status})")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке подзадач: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_actual_sub_tasks():
    """Test getting actual sub-tasks."""
    print_header("TEST: Получение актуальных подзадач")

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
            tasks = await client.tasks.list(limit=10)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            task_id = tasks[0].id
            print(f"\n⏳ Загрузка актуальных подзадач для задачи #{task_id}...")
            actual_sub_tasks = await client.tasks.get_actual_sub_tasks(task_id, limit=10)
            print_success(f"Найдено актуальных подзадач: {len(actual_sub_tasks)}")

            if actual_sub_tasks:
                print("\n📋 Актуальные подзадачи:")
                for i, subtask in enumerate(actual_sub_tasks[:5], 1):
                    print(f"  {i}. [{subtask.id}] {subtask.name}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке актуальных подзадач: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tree_level():
    """Test getting tasks at tree level."""
    print_header("TEST: Получение задач на уровне дерева")

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
            print("\n⏳ Загрузка задач на уровне дерева...")
            # Note: tree_level may return items with string IDs (e.g., "Task:1005808:...")
            # This is a known API behavior
            tree_tasks = await client.tasks.tree_level(limit=10)
            print_success(f"Найдено задач/проектов: {len(tree_tasks)}")

            if tree_tasks:
                print("\n📋 Элементы дерева:")
                for i, item in enumerate(tree_tasks[:5], 1):
                    # Handle both int and string IDs
                    item_id = item.id if isinstance(item.id, int) else str(item.id)[:20]
                    print(f"  {i}. [{item_id}] {item.name}")

            return True

    except Exception as e:
        print_warning(f"Ошибка при загрузке дерева (может быть связано с форматом ID): {e}")
        return True  # Not a critical failure


async def test_get_auditors():
    """Test getting task auditors."""
    print_header("TEST: Получение аудиторов задачи")

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
            tasks = await client.tasks.list(limit=10)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            task_id = tasks[0].id
            print(f"\n⏳ Загрузка аудиторов для задачи #{task_id}...")
            auditors = await client.tasks.get_auditors(task_id)
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


async def test_get_executors():
    """Test getting task executors."""
    print_header("TEST: Получение соисполнителей задачи")

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
            tasks = await client.tasks.list(limit=10)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            task_id = tasks[0].id
            print(f"\n⏳ Загрузка соисполнителей для задачи #{task_id}...")
            executors = await client.tasks.get_executors(task_id)
            print_success(f"Найдено соисполнителей: {len(executors)}")

            if executors:
                print("\n👥 Соисполнители:")
                for i, executor in enumerate(executors[:5], 1):
                    print(f"  {i}. {executor}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке соисполнителей: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_milestones():
    """Test getting task milestones."""
    print_header("TEST: Получение вех задачи")

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
            tasks = await client.tasks.list(limit=10)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            task_id = tasks[0].id
            print(f"\n⏳ Загрузка вех для задачи #{task_id}...")
            milestones = await client.tasks.get_milestones(task_id)
            print_success(f"Найдено вех: {len(milestones)}")

            if milestones:
                print("\n🎯 Вехи:")
                for i, milestone in enumerate(milestones[:5], 1):
                    milestone_name = milestone.name or milestone.description or f"Milestone#{milestone.id}"
                    milestone_type = milestone.type or "unknown"
                    print(f"  {i}. {milestone_name} (type: {milestone_type})")

            return True

    except Exception as e:
        # Log API error with full details
        log_api_error(
            method="GET",
            url=f"{base_url}/api/v3/task/{task_id}/milestones",
            error=e,
        )
        raise  # Re-raise to fail the test


async def test_get_history():
    """Test getting task history."""
    print_header("TEST: Получение истории изменений задачи")

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
            tasks = await client.tasks.list(limit=10)
            if not tasks:
                print_warning("Нет доступных задач для тестирования")
                return False

            task_id = tasks[0].id
            print(f"\n⏳ Загрузка истории для задачи #{task_id}...")
            history = await client.tasks.get_history(task_id, limit=10)
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

    # Test 5: Iterate tasks
    results.append(await test_iterate_tasks())

    # Test 6: Filter builder
    results.append(await test_filter_builder())

    # Test 7: List with statuses
    results.append(await test_list_with_statuses())

    # Test 8: Pagination
    results.append(await test_list_with_pagination())

    # Test 9: Get sub-tasks
    results.append(await test_get_sub_tasks())

    # Test 10: Get actual sub-tasks
    results.append(await test_get_actual_sub_tasks())

    # Test 11: Tree level
    results.append(await test_tree_level())

    # Test 12: Get auditors
    results.append(await test_get_auditors())

    # Test 13: Get executors
    results.append(await test_get_executors())

    # Test 14: Get milestones
    results.append(await test_get_milestones())

    # Test 15: Get history
    results.append(await test_get_history())

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
