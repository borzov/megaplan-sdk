"""Integration tests for Projects resource with real Megaplan API."""

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


async def test_list_projects():
    """Test listing projects."""
    print_header("TEST: Получение списка проектов")

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
            # Get first 10 projects
            print("\n⏳ Загрузка первых 10 проектов...")
            projects = await client.projects.list(limit=10)
            print_success(f"Загружено проектов: {len(projects)}")

            if projects:
                print("\n📁 Список проектов:")
                for i, project in enumerate(projects, 1):
                    print(f"  {i}. [{project.id}] {project.name}")
                    print(f"     Статус: {project.status}")
                    if project.responsible:
                        resp_name = await get_employee_display(client, project.responsible)
                        print(f"     Ответственный: {resp_name}")
            else:
                print_warning("Проектов не найдено")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке списка проектов: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_project():
    """Test getting project by ID."""
    print_header("TEST: Получение проекта по ID")

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
            # First get a project from list
            projects = await client.projects.list(limit=1)
            if not projects:
                print_warning("Нет доступных проектов для тестирования")
                return False

            project_id = projects[0].id
            print(f"\n⏳ Загрузка проекта с ID {project_id}...")
            project = await client.projects.get(project_id)

            print(f"\n📁 Информация о проекте:")
            print(f"   ID: {project.id}")
            print(f"   Название: {project.name}")
            print(f"   Статус: {project.status}")
            if project.description:
                desc = project.description[:100] + "..." if len(project.description) > 100 else project.description
                print(f"   Описание: {desc}")
            if project.responsible:
                resp_name = await get_employee_display(client, project.responsible)
                print(f"   Ответственный: {resp_name}")
            if project.owner:
                owner_name = await get_employee_display(client, project.owner)
                print(f"   Владелец: {owner_name}")

            print_success(f"Проект {project_id} загружен")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке проекта: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_project_issues():
    """Test getting project issues (tasks)."""
    print_header("TEST: Получение задач проекта")

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
            # First get a project from list
            projects = await client.projects.list(limit=5)
            if not projects:
                print_warning("Нет доступных проектов для тестирования")
                return False

            # Find project with issues
            project_id = None
            for project in projects:
                try:
                    issues = await client.projects.get_issues(project.id, limit=1)
                    if issues:
                        project_id = project.id
                        break
                except Exception:
                    continue

            if not project_id:
                # Use first project anyway
                project_id = projects[0].id

            print(f"\n⏳ Загрузка задач для проекта #{project_id}...")
            issues = await client.projects.get_issues(project_id, limit=10)
            print_success(f"Загружено задач: {len(issues)}")

            if issues:
                print(f"\n📋 Задачи проекта #{project_id}:")
                for i, issue in enumerate(issues[:5], 1):
                    print(f"  {i}. [{issue.id}] {issue.name}")
                    print(f"     Статус: {issue.status}")
                    if issue.responsible:
                        resp_name = await get_employee_display(client, issue.responsible)
                        print(f"     Ответственный: {resp_name}")
            else:
                print("\n📋 Задач нет")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке задач проекта: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_full_details():
    """Test getting full project details."""
    print_header("TEST: Получение полной информации о проекте")

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
            # First get a project from list
            projects = await client.projects.list(limit=1)
            if not projects:
                print_warning("Нет доступных проектов для тестирования")
                return False

            project_id = projects[0].id
            print(f"\n⏳ Загрузка полной информации о проекте #{project_id}...")

            details = await client.projects.get_full_details(
                project_id=project_id,
                include_comments=True,
                include_deals=True,
                comments_limit=5
            )

            print(f"\n📁 Полная информация о проекте:")
            print(f"   ID: {details.project.id}")
            print(f"   Название: {details.project.name}")
            print(f"   Статус: {details.project.status}")

            if details.project.responsible:
                resp_name = await get_employee_display(client, details.project.responsible)
                print(f"   Ответственный: {resp_name}")

            if details.comments:
                print(f"\n💬 Комментарии ({len(details.comments)}):")
                for i, comment in enumerate(details.comments[:3], 1):
                    print(f"   {i}. Комментарий #{comment.id}")
                    owner_name = await get_comment_owner_display(client, comment)
                    print(f"      Автор: {owner_name}")

            if details.deals:
                print(f"\n💼 Сделки ({len(details.deals)}):")
                for i, deal in enumerate(details.deals[:3], 1):
                    print(f"   {i}. [{deal.id}] {deal.name}")

            print_success(f"Полная информация о проекте {project_id} загружена")
            return True

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке полной информации: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all project tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: ПРОЕКТЫ (PROJECTS)")
    print("=" * 70)

    # Setup logging
    setup_logging("INFO")

    results = []

    # Test 1: List projects
    results.append(await test_list_projects())

    # Test 2: Get project by ID
    results.append(await test_get_project())

    # Test 3: Get project issues (tasks)
    results.append(await test_get_project_issues())

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
