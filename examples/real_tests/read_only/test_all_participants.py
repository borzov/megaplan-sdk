"""Integration tests for allParticipants endpoints with real Megaplan API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from megaplan_sdk import (
    ContractorHuman,
    Employee,
    Group,
    MegaplanClient,
    setup_logging,
)

from utils import (
    get_credentials,
    load_env_file,
    print_header,
    print_success,
    print_warning,
)

# Test entity IDs from user request
TEST_DEAL_ID = 1806  # from https://ruvents.megaplan.ru/deals/1806/card/
TEST_TASK_ID = 1006020  # from https://ruvents.megaplan.ru/task/1006020/card/
TEST_PROJECT_ID = 1000088  # from https://ruvents.megaplan.ru/project/1000088/card/


def get_participant_display(participant) -> str:
    """Get display name for any participant type."""
    if isinstance(participant, Employee):
        return f"Employee: {participant.display_name()}"
    elif isinstance(participant, ContractorHuman):
        return f"ContractorHuman: {participant.display_name()}"
    elif isinstance(participant, Group):
        return f"Group: {participant.display_name()}"
    else:
        return f"Unknown: {type(participant).__name__}#{participant.id}"


async def test_task_all_participants():
    """Test getting all participants for a task."""
    print_header(f"TEST: Все участники задачи (ID: {TEST_TASK_ID})")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        async with MegaplanClient(
            base_url=base_url, username=username, password=password
        ) as client:
            print(f"\n⏳ Загрузка участников задачи {TEST_TASK_ID}...")
            participants = await client.tasks.get_all_participants(task_id=TEST_TASK_ID)
            print_success(f"Загружено участников: {len(participants)}")

            if participants:
                print("\n👥 Участники задачи:")
                for i, p in enumerate(participants, 1):
                    print(f"  {i}. [{p.id}] {get_participant_display(p)}")

                # Show type distribution
                employees = [p for p in participants if isinstance(p, Employee)]
                contractors = [p for p in participants if isinstance(p, ContractorHuman)]
                groups = [p for p in participants if isinstance(p, Group)]

                print(f"\n📊 Распределение по типам:")
                print(f"   - Employee: {len(employees)}")
                print(f"   - ContractorHuman: {len(contractors)}")
                print(f"   - Group: {len(groups)}")
            else:
                print_warning("Участников не найдено")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_project_all_participants():
    """Test getting all participants for a project."""
    print_header(f"TEST: Все участники проекта (ID: {TEST_PROJECT_ID})")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        async with MegaplanClient(
            base_url=base_url, username=username, password=password
        ) as client:
            print(f"\n⏳ Загрузка участников проекта {TEST_PROJECT_ID}...")
            participants = await client.projects.get_all_participants(
                project_id=TEST_PROJECT_ID
            )
            print_success(f"Загружено участников: {len(participants)}")

            if participants:
                print("\n👥 Участники проекта:")
                for i, p in enumerate(participants, 1):
                    print(f"  {i}. [{p.id}] {get_participant_display(p)}")

                # Show type distribution
                employees = [p for p in participants if isinstance(p, Employee)]
                contractors = [p for p in participants if isinstance(p, ContractorHuman)]
                groups = [p for p in participants if isinstance(p, Group)]

                print(f"\n📊 Распределение по типам:")
                print(f"   - Employee: {len(employees)}")
                print(f"   - ContractorHuman: {len(contractors)}")
                print(f"   - Group: {len(groups)}")
            else:
                print_warning("Участников не найдено")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_deal_all_participants():
    """Test getting all participants for a deal."""
    print_header(f"TEST: Все участники сделки (ID: {TEST_DEAL_ID})")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        async with MegaplanClient(
            base_url=base_url, username=username, password=password
        ) as client:
            print(f"\n⏳ Загрузка участников сделки {TEST_DEAL_ID}...")
            participants = await client.deals.get_all_participants(deal_id=TEST_DEAL_ID)
            print_success(f"Загружено участников: {len(participants)}")

            if participants:
                print("\n👥 Участники сделки:")
                for i, emp in enumerate(participants, 1):
                    print(f"  {i}. [{emp.id}] {emp.display_name()}")
            else:
                print_warning("Участников не найдено")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_all_participants_with_limit():
    """Test getting participants with pagination limit."""
    print_header("TEST: Получение участников с лимитом пагинации")

    load_env_file()
    credentials = get_credentials()
    if not credentials:
        return False

    base_url, username, password = credentials

    try:
        async with MegaplanClient(
            base_url=base_url, username=username, password=password
        ) as client:
            # Test with limit on task
            print(f"\n⏳ Загрузка первых 2 участников задачи {TEST_TASK_ID}...")
            participants = await client.tasks.get_all_participants(
                task_id=TEST_TASK_ID, limit=2
            )
            print_success(f"Загружено участников (limit=2): {len(participants)}")

            for i, p in enumerate(participants, 1):
                print(f"  {i}. [{p.id}] {get_participant_display(p)}")

            return True

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all allParticipants tests."""
    print("\n" + "=" * 70)
    print("  ТЕСТИРОВАНИЕ allParticipants ENDPOINTS")
    print("=" * 70)

    tests = [
        ("Task allParticipants", test_task_all_participants),
        ("Project allParticipants", test_project_all_participants),
        ("Deal allParticipants", test_deal_all_participants),
        ("Pagination limit", test_all_participants_with_limit),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{'─' * 50}")
        result = await test_func()
        results.append((name, result))
        print(f"{'─' * 50}")

    # Summary
    print("\n" + "=" * 70)
    print("  РЕЗУЛЬТАТЫ ТЕСТОВ allParticipants")
    print("=" * 70)

    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n  Всего: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    setup_logging(level="INFO")
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
