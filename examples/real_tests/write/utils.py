"""Utility functions for write tests (create/update/delete)."""

import asyncio
import random
import string
import time
from typing import Any

from megaplan_sdk import MegaplanClient


def generate_test_name(prefix: str = "TEST") -> str:
    """Generate unique test object name.

    Args:
        prefix: Prefix for test object name.

    Returns:
        Unique test object name with timestamp and random suffix.
    """
    timestamp = int(time.time())
    random_suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    return f"[{prefix}] {timestamp}_{random_suffix}"


class TestObjectTracker:
    """Track created test objects for cleanup."""

    def __init__(self) -> None:
        """Initialize tracker."""
        self.tasks: list[int] = []
        self.projects: list[int] = []
        self.deals: list[int] = []
        self.comments: list[int] = []
        self.filters: list[tuple[str, int | str]] = []  # (entity_type, filter_id)

    async def cleanup_all(self, client: MegaplanClient) -> None:
        """Cleanup all tracked objects.

        Args:
            client: MegaplanClient instance.
        """
        print("\n🧹 Очистка созданных тестовых объектов...")

        # Delete comments first (they depend on entities)
        for comment_id in self.comments:
            try:
                await client.comments.delete(comment_id)
                print(f"   ✅ Комментарий #{comment_id} удален")
            except Exception as e:
                print(f"   ⚠️  Не удалось удалить комментарий #{comment_id}: {e}")

        # Delete tasks
        for task_id in self.tasks:
            try:
                await client.tasks.delete(task_id)
                print(f"   ✅ Задача #{task_id} удалена")
            except Exception as e:
                print(f"   ⚠️  Не удалось удалить задачу #{task_id}: {e}")

        # Delete projects
        for project_id in self.projects:
            try:
                await client.projects.delete(project_id)
                print(f"   ✅ Проект #{project_id} удален")
            except Exception as e:
                print(f"   ⚠️  Не удалось удалить проект #{project_id}: {e}")

        # Delete deals
        for deal_id in self.deals:
            try:
                await client.deals.delete(deal_id)
                print(f"   ✅ Сделка #{deal_id} удалена")
            except Exception as e:
                print(f"   ⚠️  Не удалось удалить сделку #{deal_id}: {e}")

        # Delete filters
        for entity_type, filter_id in self.filters:
            try:
                await client.filters.delete(entity_type, filter_id)
                print(f"   ✅ Фильтр {entity_type}#{filter_id} удален")
            except Exception as e:
                print(f"   ⚠️  Не удалось удалить фильтр {entity_type}#{filter_id}: {e}")

        print("✅ Очистка завершена")

    def add_task(self, task_id: int) -> None:
        """Add task to tracker.

        Args:
            task_id: Task ID.
        """
        self.tasks.append(task_id)

    def add_project(self, project_id: int) -> None:
        """Add project to tracker.

        Args:
            project_id: Project ID.
        """
        self.projects.append(project_id)

    def add_deal(self, deal_id: int) -> None:
        """Add deal to tracker.

        Args:
            deal_id: Deal ID.
        """
        self.deals.append(deal_id)

    def add_comment(self, comment_id: int) -> None:
        """Add comment to tracker.

        Args:
            comment_id: Comment ID.
        """
        self.comments.append(comment_id)

    def add_filter(self, entity_type: str, filter_id: int | str) -> None:
        """Add filter to tracker.

        Args:
            entity_type: Entity type (e.g., "task", "deal").
            filter_id: Filter ID.
        """
        self.filters.append((entity_type, filter_id))


async def cleanup_orphaned_test_objects(client: MegaplanClient) -> None:
    """Cleanup orphaned test objects (objects with [TEST] prefix).

    This function can be used to clean up test objects that were not properly
    cleaned up due to test failures.

    Args:
        client: MegaplanClient instance.
    """
    print("\n🧹 Поиск и удаление оставшихся тестовых объектов...")

    # Find and delete test tasks
    try:
        tasks = await client.tasks.list(limit=100)
        deleted_count = 0
        for task in tasks:
            if task.name and task.name.startswith("[TEST]"):
                try:
                    await client.tasks.delete(task.id)
                    deleted_count += 1
                    print(f"   ✅ Удалена тестовая задача #{task.id}: {task.name}")
                except Exception:
                    pass
        if deleted_count > 0:
            print(f"   ✅ Удалено тестовых задач: {deleted_count}")
    except Exception as e:
        print(f"   ⚠️  Ошибка при очистке задач: {e}")

    # Find and delete test projects
    try:
        projects = await client.projects.list(limit=100)
        deleted_count = 0
        for project in projects:
            if project.name and project.name.startswith("[TEST]"):
                try:
                    await client.projects.delete(project.id)
                    deleted_count += 1
                    print(f"   ✅ Удален тестовый проект #{project.id}: {project.name}")
                except Exception:
                    pass
        if deleted_count > 0:
            print(f"   ✅ Удалено тестовых проектов: {deleted_count}")
    except Exception as e:
        print(f"   ⚠️  Ошибка при очистке проектов: {e}")

    # Find and delete test deals
    try:
        deals = await client.deals.list(limit=100)
        deleted_count = 0
        for deal in deals:
            if deal.name and deal.name.startswith("[TEST]"):
                try:
                    await client.deals.delete(deal.id)
                    deleted_count += 1
                    print(f"   ✅ Удалена тестовая сделка #{deal.id}: {deal.name}")
                except Exception:
                    pass
        if deleted_count > 0:
            print(f"   ✅ Удалено тестовых сделок: {deleted_count}")
    except Exception as e:
        print(f"   ⚠️  Ошибка при очистке сделок: {e}")

    print("✅ Очистка завершена")
