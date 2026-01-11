"""Write tests for Projects resource (create/update/delete)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from megaplan_sdk import MegaplanClient, setup_logging

from utils import get_credentials, load_env_file, print_header, print_success, print_warning
from .utils import TestObjectTracker, generate_test_name


async def test_create_project():
    """Test creating a project."""
    print_header("TEST: Создание проекта")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials
    tracker = TestObjectTracker()

    try:
        async with MegaplanClient(base_url=base_url, username=username, password=password) as client:
            project_name = generate_test_name("PROJECT")
            print(f"\n⏳ Создание проекта '{project_name}'...")

            project = await client.projects.create({"name": project_name})
            tracker.add_project(project.id)

            print_success(f"Проект создан: ID={project.id}, Name={project.name}")

            retrieved = await client.projects.get(project.id)
            if retrieved.name == project_name:
                print_success("Проект успешно создан и проверен")
                return True
            return False

    except Exception as e:
        print(f"\n❌ Ошибка при создании проекта: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await tracker.cleanup_all(client)


async def test_update_project():
    """Test updating a project."""
    print_header("TEST: Обновление проекта")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials
    tracker = TestObjectTracker()

    try:
        async with MegaplanClient(base_url=base_url, username=username, password=password) as client:
            project = await client.projects.create({"name": generate_test_name("UPDATE")})
            tracker.add_project(project.id)

            new_name = generate_test_name("UPDATED")
            print(f"\n⏳ Обновление проекта #{project.id}...")
            updated = await client.projects.update(project.id, {"name": new_name})

            if updated.name == new_name:
                retrieved = await client.projects.get(project.id)
                if retrieved.name == new_name:
                    print_success("Проект успешно обновлен")
                    return True
            return False

    except Exception as e:
        print(f"\n❌ Ошибка при обновлении проекта: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await tracker.cleanup_all(client)


async def test_delete_project():
    """Test deleting a project."""
    print_header("TEST: Удаление проекта")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        async with MegaplanClient(base_url=base_url, username=username, password=password) as client:
            project = await client.projects.create({"name": generate_test_name("DELETE")})
            project_id = project.id

            print(f"\n⏳ Удаление проекта #{project_id}...")
            await client.projects.delete(project_id)
            print_success("Проект удален")

            try:
                await client.projects.get(project_id)
                print_warning("Проект все еще существует")
                return False
            except Exception:
                print_success("Удаление проверено")
                return True

    except Exception as e:
        print(f"\n❌ Ошибка при удалении проекта: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all project write tests."""
    print("\n" + "=" * 70)
    print("  ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ: ПРОЕКТЫ (WRITE OPERATIONS)")
    print("=" * 70)

    setup_logging("INFO")
    results = []

    results.append(await test_create_project())
    results.append(await test_update_project())
    results.append(await test_delete_project())

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
