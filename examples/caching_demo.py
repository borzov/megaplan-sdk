"""Demonstration of entity caching features in Megaplan SDK.

This example shows how the SDK automatically caches entities (employees, contractors,
departments) to reduce API calls and improve performance.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from megaplan_sdk import MegaplanClient


async def demo_caching():
    """Demonstrate caching with performance comparison."""
    print("\n" + "=" * 70)
    print("  ДЕМОНСТРАЦИЯ КЭШИРОВАНИЯ СУЩНОСТЕЙ")
    print("=" * 70)

    # Replace with your credentials
    base_url = "https://your-company.megaplan.ru"
    username = "your_email@example.com"
    password = "your_password"

    async with MegaplanClient(
        base_url=base_url,
        username=username,
        password=password,
        enable_cache=True,      # Enable caching (default)
        cache_ttl=300,          # Cache TTL: 5 minutes (default)
        cache_max_size=1000,    # Max cache size: 1000 entities (default)
    ) as client:

        print("\n📊 EXAMPLE 1: Loading tasks with expand (automatic caching)")
        print("-" * 70)

        # First load: fetches tasks and employees from API
        start = time.time()
        tasks_full = await client.tasks.list(limit=10, expand=["responsible", "owner"])
        first_load_time = time.time() - start

        print(f"✓ Loaded {len(tasks_full)} tasks with responsible/owner details")
        print(f"  Time: {first_load_time:.3f}s")

        # Show example output
        if tasks_full:
            task_full = tasks_full[0]
            print(f"\n  Example task: {task_full.task.name}")
            if task_full.responsible_details:
                print(f"  Responsible: {task_full.responsible_details.display_name()}")
            if task_full.owner_details:
                print(f"  Owner: {task_full.owner_details.display_name()}")

        # Second load: same employees are cached, only task list is fetched
        print("\n  Loading another batch of tasks (employees cached)...")
        start = time.time()
        tasks_full_2 = await client.tasks.list(
            limit=10,
            page_after={"contentType": "Task", "id": tasks_full[-1].task.id} if tasks_full else None,
            expand=["responsible", "owner"]
        )
        second_load_time = time.time() - start

        print(f"✓ Loaded {len(tasks_full_2)} tasks")
        print(f"  Time: {second_load_time:.3f}s")

        if first_load_time > 0:
            speedup = ((first_load_time - second_load_time) / first_load_time) * 100
            if speedup > 0:
                print(f"  ⚡ Speedup from caching: {speedup:.1f}%")

        print("\n📊 EXAMPLE 2: Loading deals with contractors")
        print("-" * 70)

        deals_full = await client.deals.list(limit=10, expand=["responsible", "contractor"])
        print(f"✓ Loaded {len(deals_full)} deals with contractor details")

        if deals_full:
            deal_full = deals_full[0]
            print(f"\n  Example deal: {deal_full.deal.name}")
            if deal_full.contractor_details:
                print(f"  Contractor: {deal_full.contractor_details.display_name()}")
            if deal_full.responsible_details:
                print(f"  Responsible: {deal_full.responsible_details.display_name()}")

        print("\n📊 EXAMPLE 3: Loading employees with departments")
        print("-" * 70)

        employees = await client.employees.list(limit=10, expand=["department", "manager"])
        print(f"✓ Loaded {len(employees)} employees with expanded fields")

        if employees:
            emp = employees[0]
            print(f"\n  Example employee: {emp.display_name()}")
            if emp.department and hasattr(emp.department, 'name'):
                print(f"  Department: {emp.department.name}")
            if emp.manager and hasattr(emp.manager, 'display_name'):
                print(f"  Manager: {emp.manager.display_name()}")

        print("\n📊 CACHE STATISTICS")
        print("-" * 70)

        if client._cache:
            stats = client._cache.stats()
            print(f"  Total cached entities: {stats['size']}")
            print(f"  Entity types in cache:")
            for entity_type, count in stats['types'].items():
                print(f"    - {entity_type}: {count}")

        print("\n📊 CACHE MANAGEMENT")
        print("-" * 70)

        # Clear cache for specific type
        print("  Clearing Employee cache...")
        client.clear_cache_type("Employee")

        if client._cache:
            stats = client._cache.stats()
            print(f"  ✓ Cache size after clearing employees: {stats['size']}")

        # Full cache clear
        print("\n  Clearing entire cache...")
        client.clear_cache()

        if client._cache:
            stats = client._cache.stats()
            print(f"  ✓ Cache size after full clear: {stats['size']}")

        print("\n" + "=" * 70)
        print("  CACHING FEATURES:")
        print("  • Automatic caching of employees, contractors, and departments")
        print("  • LRU eviction when cache is full")
        print("  • TTL-based expiration (5 minutes by default)")
        print("  • Batch loading with parallel requests")
        print("  • Significant performance improvement for repeated entity access")
        print("=" * 70)


async def demo_without_caching():
    """Demonstrate SDK without caching for comparison."""
    print("\n" + "=" * 70)
    print("  COMPARISON: WITHOUT CACHING")
    print("=" * 70)

    # Replace with your credentials
    base_url = "https://your-company.megaplan.ru"
    username = "your_email@example.com"
    password = "your_password"

    async with MegaplanClient(
        base_url=base_url,
        username=username,
        password=password,
        enable_cache=False,  # Disable caching
    ) as client:

        print("\n⚠️  Caching disabled - each entity will be fetched from API every time")

        # Load tasks with expand
        start = time.time()
        tasks_full = await client.tasks.list(limit=10, expand=["responsible", "owner"])
        first_load_time = time.time() - start

        print(f"\n✓ Loaded {len(tasks_full)} tasks")
        print(f"  Time: {first_load_time:.3f}s")

        # Load again - no caching benefit
        start = time.time()
        tasks_full_2 = await client.tasks.list(
            limit=10,
            page_after={"contentType": "Task", "id": tasks_full[-1].task.id} if tasks_full else None,
            expand=["responsible", "owner"]
        )
        second_load_time = time.time() - start

        print(f"\n✓ Loaded {len(tasks_full_2)} tasks (second batch)")
        print(f"  Time: {second_load_time:.3f}s")
        print(f"  ℹ️  Similar times because entities are not cached")


if __name__ == "__main__":
    print("\n💡 CACHING DEMONSTRATION")
    print("\nBefore running this demo, update the credentials in the code:")
    print("  - base_url")
    print("  - username")
    print("  - password")
    print("\nThis demo will:")
    print("  1. Show how caching improves performance")
    print("  2. Demonstrate cache statistics and management")
    print("  3. Compare performance with and without caching")
    print("\nPress Ctrl+C to exit")
    print()

    try:
        asyncio.run(demo_caching())
        # Uncomment to also run comparison without caching:
        # asyncio.run(demo_without_caching())
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
