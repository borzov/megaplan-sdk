"""Integration tests for Available Parents endpoints with real Megaplan API."""

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

# Test data IDs from the user's Megaplan instance
# - Project #1000095 - project with tasks
# - Task #1003812 - task with subtasks and deals
# - Task #1005804 - task with a parent task
TEST_PROJECT_ID = 1000095
TEST_TASK_WITH_SUBTASKS_ID = 1003812
TEST_TASK_WITH_PARENT_ID = 1005804


async def test_task_available_parents_global():
    """Test getting available parents for new task (global endpoint)."""
    print_header("TEST: Доступные родители для новой задачи (глобальный)")

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
            print("\n⏳ Загрузка доступных родительских задач/проектов...")
            parents = await client.tasks.get_available_parents(limit=10)
            print_success(f"Найдено доступных родителей: {len(parents)}")

            if parents:
                print("\n📋 Доступные родители:")
                task_count = 0
                project_count = 0
                for i, parent in enumerate(parents[:10], 1):
                    entity_type = type(parent).__name__
                    print(f"  {i}. [{entity_type}] {parent.id}: {parent.name}")
                    if entity_type == "Task":
                        task_count += 1
                    elif entity_type == "Project":
                        project_count += 1

                print(f"\n📊 Статистика: Tasks={task_count}, Projects={project_count}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_task_available_parents_for_task_with_subtasks():
    """Test getting available parents for task #1003812 (has subtasks and deals)."""
    print_header(f"TEST: Доступные родители для задачи #{TEST_TASK_WITH_SUBTASKS_ID}")

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
            # First verify the task exists
            print(f"\n⏳ Проверка задачи #{TEST_TASK_WITH_SUBTASKS_ID}...")
            try:
                task = await client.tasks.get(TEST_TASK_WITH_SUBTASKS_ID)
                print_success(f"Задача найдена: {task.name}")
            except Exception as e:
                print_warning(f"Задача #{TEST_TASK_WITH_SUBTASKS_ID} не найдена: {e}")
                print_warning("Используем первую доступную задачу...")
                tasks = await client.tasks.list(limit=1)
                if not tasks:
                    print_warning("Нет доступных задач")
                    return True  # Not a failure
                task = tasks[0]
                print_success(f"Используем задачу #{task.id}: {task.name}")

            print(f"\n⏳ Загрузка доступных родителей для задачи #{task.id}...")
            parents = await client.tasks.get_available_parents_for(task.id, limit=10)
            print_success(f"Найдено доступных родителей: {len(parents)}")

            if parents:
                print("\n📋 Доступные родители:")
                for i, parent in enumerate(parents[:10], 1):
                    entity_type = type(parent).__name__
                    print(f"  {i}. [{entity_type}] {parent.id}: {parent.name}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_task_available_parents_for_task_with_parent():
    """Test getting available parents for task #1005804 (has a parent task)."""
    print_header(f"TEST: Доступные родители для задачи #{TEST_TASK_WITH_PARENT_ID} (имеет надзадачу)")

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
            # First verify the task exists and check its parent
            print(f"\n⏳ Проверка задачи #{TEST_TASK_WITH_PARENT_ID}...")
            try:
                task = await client.tasks.get(TEST_TASK_WITH_PARENT_ID)
                print_success(f"Задача найдена: {task.name}")
                if hasattr(task, 'parent') and task.parent:
                    print(f"   Текущий родитель: {task.parent}")
            except Exception as e:
                print_warning(f"Задача #{TEST_TASK_WITH_PARENT_ID} не найдена: {e}")
                print_warning("Используем первую доступную задачу...")
                tasks = await client.tasks.list(limit=1)
                if not tasks:
                    print_warning("Нет доступных задач")
                    return True  # Not a failure
                task = tasks[0]
                print_success(f"Используем задачу #{task.id}: {task.name}")

            print(f"\n⏳ Загрузка доступных родителей для задачи #{task.id}...")
            parents = await client.tasks.get_available_parents_for(task.id, limit=10)
            print_success(f"Найдено доступных родителей: {len(parents)}")

            if parents:
                print("\n📋 Доступные родители:")
                for i, parent in enumerate(parents[:10], 1):
                    entity_type = type(parent).__name__
                    print(f"  {i}. [{entity_type}] {parent.id}: {parent.name}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_project_available_parents_global():
    """Test getting available parents for new project (global endpoint)."""
    print_header("TEST: Доступные родители для нового проекта (глобальный)")

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
            print("\n⏳ Загрузка доступных родительских проектов...")
            parents = await client.projects.get_available_parents(limit=10)
            print_success(f"Найдено доступных родительских проектов: {len(parents)}")

            if parents:
                print("\n📁 Доступные родительские проекты:")
                for i, parent in enumerate(parents[:10], 1):
                    print(f"  {i}. [{parent.id}] {parent.name}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_project_available_parents_for_project():
    """Test getting available parents for project #1000095."""
    print_header(f"TEST: Доступные родители для проекта #{TEST_PROJECT_ID}")

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
            # First verify the project exists
            print(f"\n⏳ Проверка проекта #{TEST_PROJECT_ID}...")
            try:
                project = await client.projects.get(TEST_PROJECT_ID)
                print_success(f"Проект найден: {project.name}")
            except Exception as e:
                print_warning(f"Проект #{TEST_PROJECT_ID} не найден: {e}")
                print_warning("Используем первый доступный проект...")
                projects = await client.projects.list(limit=1)
                if not projects:
                    print_warning("Нет доступных проектов")
                    return True  # Not a failure
                project = projects[0]
                print_success(f"Используем проект #{project.id}: {project.name}")

            print(f"\n⏳ Загрузка доступных родителей для проекта #{project.id}...")
            parents = await client.projects.get_available_parents_for(project.id, limit=10)
            print_success(f"Найдено доступных родительских проектов: {len(parents)}")

            if parents:
                print("\n📁 Доступные родительские проекты:")
                for i, parent in enumerate(parents[:10], 1):
                    print(f"  {i}. [{parent.id}] {parent.name}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_available_parents_with_template_filter():
    """Test getting available parents with isTemplate filter."""
    print_header("TEST: Доступные родители с фильтром isTemplate=False")

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
            print("\n⏳ Загрузка НЕ-шаблонных родителей для задач...")
            parents = await client.tasks.get_available_parents(
                is_template=False, limit=5
            )
            print_success(f"Найдено: {len(parents)}")

            if parents:
                print("\n📋 Родители (is_template=False):")
                for i, parent in enumerate(parents[:5], 1):
                    entity_type = type(parent).__name__
                    print(f"  {i}. [{entity_type}] {parent.id}: {parent.name}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all available parents tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: AVAILABLE PARENTS ENDPOINTS")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: Global available parents for tasks
    results.append(await test_task_available_parents_global())

    # Test 2: Available parents for task with subtasks
    results.append(await test_task_available_parents_for_task_with_subtasks())

    # Test 3: Available parents for task with parent
    results.append(await test_task_available_parents_for_task_with_parent())

    # Test 4: Global available parents for projects
    results.append(await test_project_available_parents_global())

    # Test 5: Available parents for specific project
    results.append(await test_project_available_parents_for_project())

    # Test 6: Available parents with template filter
    results.append(await test_available_parents_with_template_filter())

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
