"""CLI application for testing Megaplan SDK.

Simple interactive menu for testing all SDK features including get_full_details.
"""

import asyncio
import os
from pathlib import Path

from megaplan_sdk import MegaplanClient, setup_logging


# Global cache for employee information to minimize API requests
_employee_cache: dict[int, dict] = {}
_cache_stats = {"hits": 0, "misses": 0}


def clear_employee_cache():
    """Clear the employee cache."""
    global _employee_cache, _cache_stats
    _employee_cache.clear()
    _cache_stats = {"hits": 0, "misses": 0}


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return {
        "size": len(_employee_cache),
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "hit_rate": (
            _cache_stats["hits"] / (_cache_stats["hits"] + _cache_stats["misses"])
            if (_cache_stats["hits"] + _cache_stats["misses"]) > 0
            else 0
        ),
    }


async def get_employee_info(client: MegaplanClient, employee_id: int) -> dict | None:
    """Get employee information with caching.

    Args:
        client: MegaplanClient instance.
        employee_id: Employee ID.

    Returns:
        Employee data dict or None if not found.
    """
    global _cache_stats

    # Check cache first
    if employee_id in _employee_cache:
        _cache_stats["hits"] += 1
        return _employee_cache[employee_id]

    # Fetch from API
    _cache_stats["misses"] += 1
    try:
        employee = await client.employees.get(employee_id)
        # Store in cache
        employee_data = {
            "id": employee.id,
            "first_name": getattr(employee, "first_name", ""),
            "last_name": getattr(employee, "last_name", ""),
            "middle_name": getattr(employee, "middle_name", ""),
            "position": getattr(employee, "position", ""),
            "email": getattr(employee, "email", ""),
            "phone": getattr(employee, "phone", ""),
            "department": getattr(employee, "department", None),
        }
        _employee_cache[employee_id] = employee_data
        return employee_data
    except Exception as e:
        print(f"⚠️ Не удалось загрузить информацию о сотруднике {employee_id}: {e}")
        return None


def format_employee(employee_data: dict | None) -> str:
    """Format employee information for display.

    Args:
        employee_data: Employee data from get_employee_info or None.

    Returns:
        Formatted string with employee info.
    """
    if not employee_data:
        return "Не указано"

    # Build full name
    name_parts = [
        employee_data.get("last_name", ""),
        employee_data.get("first_name", ""),
        employee_data.get("middle_name", ""),
    ]
    full_name = " ".join(part for part in name_parts if part)

    if not full_name:
        full_name = "Без имени"

    # Add position if available
    position = employee_data.get("position", "")

    # Format: "Иванов Иван Иванович, Senior Developer (ID: 123)"
    result = full_name
    if position:
        result += f", {position}"
    result += f" (ID: {employee_data['id']})"

    return result


async def format_employee_from_entity(client: MegaplanClient, entity) -> str:
    """Format employee from BaseEntity reference.

    Args:
        client: MegaplanClient instance.
        entity: BaseEntity with id field.

    Returns:
        Formatted employee string.
    """
    if not entity:
        return "Не указано"

    employee_data = await get_employee_info(client, entity.id)
    return format_employee(employee_data)


def clear_screen():
    """Clear terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def print_header(title: str):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_menu(title: str, options: list[tuple[str, str]]):
    """Print menu with options."""
    print_header(title)
    for key, description in options:
        print(f"  [{key}] {description}")
    print("  [0] Назад")
    print()


def print_separator(char="-", length=70):
    """Print separator line."""
    print(char * length)


def format_entity_ref(entity):
    """Format BaseEntity reference."""
    if entity:
        return f"{entity.content_type}#{entity.id}"
    return "Не указано"


def print_full_details_summary(details, entity_type: str):
    """Print summary of loaded full details."""
    print(f"\n📦 Загружена полная информация о {entity_type}")
    print_separator()

    components = []
    if hasattr(details, 'comments') and details.comments:
        components.append(f"💬 Комментарии: {len(details.comments)}")
    if hasattr(details, 'history') and details.history:
        components.append(f"📜 История: {len(details.history)}")
    if hasattr(details, 'status_history') and details.status_history:
        components.append(f"🔄 История статусов: {len(details.status_history)}")
    if hasattr(details, 'sub_tasks') and details.sub_tasks:
        components.append(f"📋 Подзадачи: {len(details.sub_tasks)}")
    if hasattr(details, 'actual_sub_tasks') and details.actual_sub_tasks:
        components.append(f"✅ Актуальные подзадачи: {len(details.actual_sub_tasks)}")
    if hasattr(details, 'deals') and details.deals:
        components.append(f"💼 Сделки: {len(details.deals)}")
    if hasattr(details, 'issues') and details.issues:
        components.append(f"📋 Задачи: {len(details.issues)}")
    if hasattr(details, 'actual_issues') and details.actual_issues:
        components.append(f"✅ Актуальные задачи: {len(details.actual_issues)}")
    if hasattr(details, 'related_tasks') and details.related_tasks:
        components.append(f"🔗 Связанные задачи: {len(details.related_tasks)}")
    if hasattr(details, 'auditors') and details.auditors:
        components.append(f"👁️ Аудиторы: {len(details.auditors)}")
    if hasattr(details, 'executors') and details.executors:
        components.append(f"👥 Соисполнители: {len(details.executors)}")
    if hasattr(details, 'milestones') and details.milestones:
        components.append(f"🎯 Вехи: {len(details.milestones)}")
    if hasattr(details, 'responsible_details') and details.responsible_details:
        components.append("👤 Ответственный (полная информация)")
    if hasattr(details, 'owner_details') and details.owner_details:
        components.append("👤 Владелец (полная информация)")
    if hasattr(details, 'contractor_details') and details.contractor_details:
        components.append("🏢 Контрагент (полная информация)")

    if components:
        for comp in components:
            print(f"  ✓ {comp}")
    else:
        print("  (дополнительные данные не загружены)")

    print_separator()


async def test_task_full_details(client: MegaplanClient):
    """Test get_full_details for tasks."""
    task_id = input("\nВведите ID задачи: ").strip()
    if not task_id.isdigit():
        print("❌ Неверный ID")
        return

    print("\n📋 Выберите, что загрузить:")
    print("  [1] Только основная информация")
    print("  [2] С комментариями и историей")
    print("  [3] Полная информация (все данные)")
    print("  [4] Настроить вручную")

    choice = input("\nВаш выбор: ").strip()

    # Prepare parameters
    params = {"task_id": int(task_id)}

    if choice == "1":
        # Minimal - just the task
        pass
    elif choice == "2":
        # Comments and history
        params.update({
            "include_comments": True,
            "include_history": True,
            "comments_limit": 20
        })
    elif choice == "3":
        # Everything
        params.update({
            "include_sub_tasks": True,
            "include_actual_sub_tasks": True,
            "include_comments": True,
            "include_history": True,
            "include_auditors": True,
            "include_executors": True,
            "include_milestones": True,
            "include_responsible_details": True,
            "include_owner_details": True
        })
    elif choice == "4":
        # Manual configuration
        if input("  Загрузить подзадачи? (y/n): ").strip().lower() == "y":
            params["include_sub_tasks"] = True
        if input("  Загрузить актуальные подзадачи? (y/n): ").strip().lower() == "y":
            params["include_actual_sub_tasks"] = True
        if input("  Загрузить комментарии? (y/n): ").strip().lower() == "y":
            params["include_comments"] = True
            limit = input("    Лимит комментариев (Enter = без лимита): ").strip()
            if limit.isdigit():
                params["comments_limit"] = int(limit)
        if input("  Загрузить историю? (y/n): ").strip().lower() == "y":
            params["include_history"] = True
        if input("  Загрузить аудиторов? (y/n): ").strip().lower() == "y":
            params["include_auditors"] = True
        if input("  Загрузить соисполнителей? (y/n): ").strip().lower() == "y":
            params["include_executors"] = True
        if input("  Загрузить вехи? (y/n): ").strip().lower() == "y":
            params["include_milestones"] = True
        if input("  Загрузить полные данные ответственного? (y/n): ").strip().lower() == "y":
            params["include_responsible_details"] = True
        if input("  Загрузить полные данные постановщика? (y/n): ").strip().lower() == "y":
            params["include_owner_details"] = True

    try:
        print("\n⏳ Загрузка полной информации о задаче...")
        details = await client.tasks.get_full_details(**params)

        # Pre-load employee info for caching
        task = details.task
        responsible_str = None
        owner_str = None

        if task.responsible:
            responsible_str = await format_employee_from_entity(client, task.responsible)
        if task.owner:
            owner_str = await format_employee_from_entity(client, task.owner)

        # Print main task info
        print("\n✅ Задача загружена:")
        print_separator()
        print(f"  ID: {task.id}")
        print(f"  Название: {task.name}")
        print(f"  Статус: {task.status}")
        if task.deadline:
            print(f"  Deadline: {task.deadline}")
        if responsible_str:
            print(f"  Ответственный: {responsible_str}")
        if owner_str:
            print(f"  Постановщик: {owner_str}")

        # Print loaded components summary
        print_full_details_summary(details, "задаче")

        # Show first few comments with author info
        if details.comments:
            print(f"\n💬 Последние комментарии ({len(details.comments)} всего):")
            for i, comment in enumerate(details.comments[:3], 1):
                author_str = "Неизвестен"
                if comment.owner:
                    author_str = await format_employee_from_entity(client, comment.owner)
                text_preview = (comment.content or "")[:60]
                print(f"  {i}. #{comment.id} от {author_str}:")
                print(f"     {text_preview}{'...' if len(comment.content or '') > 60 else ''}")

        # Show subtasks
        if details.sub_tasks:
            print(f"\n📋 Подзадачи ({len(details.sub_tasks)} всего):")
            for i, subtask in enumerate(details.sub_tasks[:5], 1):
                print(f"  {i}. #{subtask.id}: {subtask.name} ({subtask.status})")
            if len(details.sub_tasks) > 5:
                print(f"     ... и еще {len(details.sub_tasks) - 5}")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

    input("\nНажмите Enter...")


async def test_project_full_details(client: MegaplanClient):
    """Test get_full_details for projects."""
    project_id = input("\nВведите ID проекта: ").strip()
    if not project_id.isdigit():
        print("❌ Неверный ID")
        return

    print("\n📋 Выберите, что загрузить:")
    print("  [1] Только основная информация")
    print("  [2] С сделками и задачами")
    print("  [3] Полная информация (все данные)")

    choice = input("\nВаш выбор: ").strip()

    params = {"project_id": int(project_id)}

    if choice == "2":
        params.update({
            "include_deals": True,
            "include_issues": True,
            "include_comments": True
        })
    elif choice == "3":
        params.update({
            "include_deals": True,
            "include_issues": True,
            "include_actual_issues": True,
            "include_comments": True,
            "include_history": True,
            "include_auditors": True,
            "include_executors": True,
            "include_milestones": True,
            "include_responsible_details": True,
            "include_owner_details": True
        })

    try:
        print("\n⏳ Загрузка полной информации о проекте...")
        details = await client.projects.get_full_details(**params)

        # Pre-load employee info for caching
        project = details.project
        responsible_str = None
        owner_str = None

        if project.responsible:
            responsible_str = await format_employee_from_entity(client, project.responsible)
        if project.owner:
            owner_str = await format_employee_from_entity(client, project.owner)

        # Print main project info
        print("\n✅ Проект загружен:")
        print_separator()
        print(f"  ID: {project.id}")
        print(f"  Название: {project.name}")
        if responsible_str:
            print(f"  Ответственный: {responsible_str}")
        if owner_str:
            print(f"  Владелец: {owner_str}")

        # Print loaded components summary
        print_full_details_summary(details, "проекте")

        # Show deals
        if details.deals:
            print(f"\n💼 Сделки проекта ({len(details.deals)} всего):")
            for i, deal in enumerate(details.deals[:5], 1):
                print(f"  {i}. #{deal.id}: {deal.name}")
            if len(details.deals) > 5:
                print(f"     ... и еще {len(details.deals) - 5}")

        # Show issues/tasks
        if details.issues:
            print(f"\n📋 Задачи проекта ({len(details.issues)} всего):")
            for i, task in enumerate(details.issues[:5], 1):
                print(f"  {i}. #{task.id}: {task.name} ({task.status})")
            if len(details.issues) > 5:
                print(f"     ... и еще {len(details.issues) - 5}")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

    input("\nНажмите Enter...")


async def test_deal_full_details(client: MegaplanClient):
    """Test get_full_details for deals."""
    deal_id = input("\nВведите ID сделки: ").strip()
    if not deal_id.isdigit():
        print("❌ Неверный ID")
        return

    print("\n📋 Выберите, что загрузить:")
    print("  [1] Только основная информация")
    print("  [2] С комментариями и историей")
    print("  [3] Полная информация (все данные)")

    choice = input("\nВаш выбор: ").strip()

    params = {"deal_id": int(deal_id)}

    if choice == "2":
        params.update({
            "include_comments": True,
            "include_history": True,
            "include_status_history": True,
            "comments_limit": 20
        })
    elif choice == "3":
        params.update({
            "include_comments": True,
            "include_history": True,
            "include_status_history": True,
            "include_auditors": True,
            "include_responsible_details": True,
            "include_contractor_details": True,
            "include_related_tasks": True
        })

    try:
        print("\n⏳ Загрузка полной информации о сделке...")
        details = await client.deals.get_full_details(**params)

        # Pre-load employee info for caching
        deal = details.deal
        responsible_str = None
        contractor_str = None

        if deal.responsible:
            responsible_str = await format_employee_from_entity(client, deal.responsible)
        if deal.contractor:
            contractor_str = format_entity_ref(deal.contractor)

        # Print main deal info
        print("\n✅ Сделка загружена:")
        print_separator()
        print(f"  ID: {deal.id}")
        print(f"  Название: {deal.name}")
        if deal.sum_base:
            print(f"  Сумма: {deal.sum_base}")
        if deal.state:
            print(f"  Статус: {deal.state.name}")
        if responsible_str:
            print(f"  Ответственный: {responsible_str}")
        if contractor_str:
            print(f"  Контрагент: {contractor_str}")

        # Print contractor details if loaded
        if details.contractor_details:
            print(f"\n🏢 Контрагент (детали):")
            contr = details.contractor_details
            print(f"  Название: {contr.name}")
            print(f"  Тип: {contr.content_type}")

        # Print loaded components summary
        print_full_details_summary(details, "сделке")

        # Show status history
        if details.status_history:
            print(f"\n🔄 История статусов ({len(details.status_history)} всего):")
            for i, entry in enumerate(details.status_history[:3], 1):
                print(f"  {i}. {entry}")

        # Show related tasks
        if details.related_tasks:
            print(f"\n🔗 Связанные задачи ({len(details.related_tasks)} всего):")
            for i, task in enumerate(details.related_tasks[:5], 1):
                print(f"  {i}. #{task.id}: {task.name}")
            if len(details.related_tasks) > 5:
                print(f"     ... и еще {len(details.related_tasks) - 5}")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

    input("\nНажмите Enter...")


async def test_tasks(client: MegaplanClient):
    """Test Tasks resource."""
    while True:
        print_menu(
            "Tasks (Задачи)",
            [
                ("1", "Список задач (первые 5)"),
                ("2", "Поиск задачи по ID"),
                ("3", "🆕 Полная информация о задаче (get_full_details)"),
                ("4", "Создать тестовую задачу"),
                ("5", "Итерация по всем задачам (первые 10)"),
                ("6", "Управление участниками (auditors/executors)"),
                ("7", "Управление вехами (milestones)"),
                ("8", "История изменений (history)"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print("\n⏳ Загрузка задач...")
            tasks = await client.tasks.list(limit=5)
            print(f"\n✅ Найдено задач: {len(tasks)}")
            for task in tasks:
                print(f"  - #{task.id}: {task.name} (статус: {task.status})")
            input("\nНажмите Enter...")

        elif choice == "2":
            task_id = input("Введите ID задачи: ").strip()
            if task_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка задачи #{task_id}...")
                    task = await client.tasks.get(int(task_id))
                    print("\n✅ Задача найдена:")
                    print(f"  ID: {task.id}")
                    print(f"  Название: {task.name}")
                    print(f"  Статус: {task.status}")
                    print(f"  Deadline: {task.deadline}")
                    if task.responsible:
                        responsible_str = await format_employee_from_entity(client, task.responsible)
                        print(f"  Ответственный: {responsible_str}")

                    # Load and display comments
                    print("\n⏳ Загрузка комментариев...")
                    comments = await client.tasks.get_comments(int(task_id), limit=5)
                    if comments:
                        print(f"\n💬 Комментарии ({len(comments)}):")
                        for comment in comments:
                            author_str = "Неизвестен"
                            if comment.owner:
                                author_str = await format_employee_from_entity(client, comment.owner)
                            text_preview = (comment.content or "")[:50]
                            print(f"  - #{comment.id} от {author_str}: {text_preview}...")
                    else:
                        print("\n💬 Комментариев нет")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "3":
            await test_task_full_details(client)

        elif choice == "4":
            name = input("Название задачи: ").strip() or "Тестовая задача из SDK"
            try:
                print("\n⏳ Создание задачи...")
                task = await client.tasks.create({"name": name, "statement": "Создано через SDK"})
                print("\n✅ Задача создана!")
                print(f"  ID: {task.id}")
                print(f"  Название: {task.name}")
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "5":
            print("\n⏳ Итерация по задачам...")
            count = 0
            async for task in client.tasks.iterate(limit=5):
                count += 1
                print(f"  {count}. #{task.id}: {task.name}")
                if count >= 10:
                    break
            print(f"\n✅ Обработано: {count} задач")
            input("\nНажмите Enter...")

        elif choice == "6":
            await test_task_participants(client)

        elif choice == "7":
            await test_task_milestones(client)

        elif choice == "8":
            await test_task_history(client)


async def test_task_participants(client: MegaplanClient):
    """Test task participants (auditors and executors)."""
    while True:
        print_menu(
            "Участники задачи",
            [
                ("1", "Список наблюдателей (auditors)"),
                ("2", "Добавить наблюдателя"),
                ("3", "Удалить наблюдателя"),
                ("4", "Список соисполнителей (executors)"),
                ("5", "Добавить соисполнителя"),
                ("6", "Удалить соисполнителя"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            task_id = input("ID задачи: ").strip()
            if task_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка наблюдателей задачи #{task_id}...")
                    auditors = await client.tasks.get_auditors(int(task_id), limit=10)
                    print(f"\n✅ Наблюдателей: {len(auditors)}")
                    for auditor in auditors:
                        print(f"  - {auditor}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            task_id = input("ID задачи: ").strip()
            auditor_id = input("ID сотрудника (auditor): ").strip()
            if task_id.isdigit() and auditor_id.isdigit():
                try:
                    print("\n⏳ Добавление наблюдателя...")
                    result = await client.tasks.add_auditor(int(task_id), int(auditor_id))
                    print(f"\n✅ Наблюдатель добавлен: {result}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "3":
            task_id = input("ID задачи: ").strip()
            auditor_id = input("ID наблюдателя для удаления: ").strip()
            if task_id.isdigit() and auditor_id.isdigit():
                try:
                    print("\n⏳ Удаление наблюдателя...")
                    await client.tasks.remove_auditor(int(task_id), int(auditor_id))
                    print("\n✅ Наблюдатель удален")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "4":
            task_id = input("ID задачи: ").strip()
            if task_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка соисполнителей задачи #{task_id}...")
                    executors = await client.tasks.get_executors(int(task_id), limit=10)
                    print(f"\n✅ Соисполнителей: {len(executors)}")
                    for executor in executors:
                        print(f"  - {executor}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "5":
            task_id = input("ID задачи: ").strip()
            executor_id = input("ID сотрудника (executor): ").strip()
            if task_id.isdigit() and executor_id.isdigit():
                try:
                    print("\n⏳ Добавление соисполнителя...")
                    result = await client.tasks.add_executor(int(task_id), int(executor_id))
                    print(f"\n✅ Соисполнитель добавлен: {result}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "6":
            task_id = input("ID задачи: ").strip()
            executor_id = input("ID соисполнителя для удаления: ").strip()
            if task_id.isdigit() and executor_id.isdigit():
                try:
                    print("\n⏳ Удаление соисполнителя...")
                    await client.tasks.remove_executor(int(task_id), int(executor_id))
                    print("\n✅ Соисполнитель удален")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")


async def test_task_milestones(client: MegaplanClient):
    """Test task milestones."""
    while True:
        print_menu(
            "Вехи задачи",
            [
                ("1", "Список вех (milestones)"),
                ("2", "Добавить веху"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            task_id = input("ID задачи: ").strip()
            if task_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка вех задачи #{task_id}...")
                    milestones = await client.tasks.get_milestones(int(task_id), limit=10)
                    print(f"\n✅ Вех: {len(milestones)}")
                    for milestone in milestones:
                        print(f"  - {milestone}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            task_id = input("ID задачи: ").strip()
            name = input("Название вехи: ").strip()
            if task_id.isdigit() and name:
                try:
                    print("\n⏳ Добавление вехи...")
                    milestone = await client.tasks.add_milestone(
                        int(task_id),
                        {"name": name}
                    )
                    print(f"\n✅ Веха добавлена: {milestone}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")


async def test_task_history(client: MegaplanClient):
    """Test task history."""
    while True:
        print_menu(
            "История задачи",
            [
                ("1", "Показать историю изменений"),
                ("2", "Поиск в истории"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            task_id = input("ID задачи: ").strip()
            if task_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка истории задачи #{task_id}...")
                    history = await client.tasks.get_history(int(task_id), limit=10)
                    print(f"\n✅ Записей в истории: {len(history)}")
                    for entry in history:
                        print(f"  - {entry}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            task_id = input("ID задачи: ").strip()
            query = input("Поисковый запрос: ").strip()
            if task_id.isdigit() and query:
                try:
                    print(f"\n⏳ Поиск в истории задачи #{task_id}...")
                    results = await client.tasks.search_history(int(task_id), query, limit=10)
                    print(f"\n✅ Найдено записей: {len(results)}")
                    for entry in results:
                        print(f"  - {entry}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")


async def test_projects(client: MegaplanClient):
    """Test Projects resource."""
    while True:
        print_menu(
            "Projects (Проекты)",
            [
                ("1", "Список проектов (первые 5)"),
                ("2", "Поиск проекта по ID"),
                ("3", "🆕 Полная информация о проекте (get_full_details)"),
                ("4", "Создать тестовый проект"),
                ("5", "Управление участниками (auditors/executors)"),
                ("6", "Управление вехами (milestones)"),
                ("7", "История изменений (history)"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print("\n⏳ Загрузка проектов...")
            projects = await client.projects.list(limit=5)
            print(f"\n✅ Найдено проектов: {len(projects)}")
            for project in projects:
                print(f"  - #{project.id}: {project.name}")
            input("\nНажмите Enter...")

        elif choice == "2":
            project_id = input("Введите ID проекта: ").strip()
            if project_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка проекта #{project_id}...")
                    project = await client.projects.get(int(project_id))
                    print("\n✅ Проект найден:")
                    print(f"  ID: {project.id}")
                    print(f"  Название: {project.name}")

                    # Load and display comments
                    print("\n⏳ Загрузка комментариев...")
                    comments = await client.projects.get_comments(int(project_id), limit=5)
                    if comments:
                        print(f"\n💬 Комментарии ({len(comments)}):")
                        for comment in comments:
                            author = comment.owner.id if comment.owner else "Unknown"
                            text_preview = (comment.content or "")[:50]
                            print(f"  - #{comment.id} от {author}: {text_preview}...")
                    else:
                        print("\n💬 Комментариев нет")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "3":
            await test_project_full_details(client)

        elif choice == "4":
            name = input("Название проекта: ").strip() or "Тестовый проект из SDK"
            try:
                print("\n⏳ Создание проекта...")
                project = await client.projects.create({"name": name})
                print("\n✅ Проект создан!")
                print(f"  ID: {project.id}")
                print(f"  Название: {project.name}")
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "5":
            await test_project_participants(client)

        elif choice == "6":
            await test_project_milestones(client)

        elif choice == "7":
            await test_project_history(client)


async def test_project_participants(client: MegaplanClient):
    """Test project participants (auditors and executors)."""
    while True:
        print_menu(
            "Участники проекта",
            [
                ("1", "Список наблюдателей (auditors)"),
                ("2", "Добавить наблюдателя"),
                ("3", "Удалить наблюдателя"),
                ("4", "Список соисполнителей (executors)"),
                ("5", "Добавить соисполнителя"),
                ("6", "Удалить соисполнителя"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            project_id = input("ID проекта: ").strip()
            if project_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка наблюдателей проекта #{project_id}...")
                    auditors = await client.projects.get_auditors(int(project_id), limit=10)
                    print(f"\n✅ Наблюдателей: {len(auditors)}")
                    for auditor in auditors:
                        print(f"  - {auditor}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            project_id = input("ID проекта: ").strip()
            auditor_id = input("ID сотрудника (auditor): ").strip()
            if project_id.isdigit() and auditor_id.isdigit():
                try:
                    print("\n⏳ Добавление наблюдателя...")
                    result = await client.projects.add_auditor(int(project_id), int(auditor_id))
                    print(f"\n✅ Наблюдатель добавлен: {result}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "3":
            project_id = input("ID проекта: ").strip()
            auditor_id = input("ID наблюдателя для удаления: ").strip()
            if project_id.isdigit() and auditor_id.isdigit():
                try:
                    print("\n⏳ Удаление наблюдателя...")
                    await client.projects.remove_auditor(int(project_id), int(auditor_id))
                    print("\n✅ Наблюдатель удален")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "4":
            project_id = input("ID проекта: ").strip()
            if project_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка соисполнителей проекта #{project_id}...")
                    executors = await client.projects.get_executors(int(project_id), limit=10)
                    print(f"\n✅ Соисполнителей: {len(executors)}")
                    for executor in executors:
                        print(f"  - {executor}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "5":
            project_id = input("ID проекта: ").strip()
            executor_id = input("ID сотрудника (executor): ").strip()
            if project_id.isdigit() and executor_id.isdigit():
                try:
                    print("\n⏳ Добавление соисполнителя...")
                    result = await client.projects.add_executor(int(project_id), int(executor_id))
                    print(f"\n✅ Соисполнитель добавлен: {result}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "6":
            project_id = input("ID проекта: ").strip()
            executor_id = input("ID соисполнителя для удаления: ").strip()
            if project_id.isdigit() and executor_id.isdigit():
                try:
                    print("\n⏳ Удаление соисполнителя...")
                    await client.projects.remove_executor(int(project_id), int(executor_id))
                    print("\n✅ Соисполнитель удален")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")


async def test_project_milestones(client: MegaplanClient):
    """Test project milestones."""
    while True:
        print_menu(
            "Вехи проекта",
            [
                ("1", "Список вех (milestones)"),
                ("2", "Добавить веху"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            project_id = input("ID проекта: ").strip()
            if project_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка вех проекта #{project_id}...")
                    milestones = await client.projects.get_milestones(int(project_id), limit=10)
                    print(f"\n✅ Вех: {len(milestones)}")
                    for milestone in milestones:
                        print(f"  - {milestone}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            project_id = input("ID проекта: ").strip()
            name = input("Название вехи: ").strip()
            if project_id.isdigit() and name:
                try:
                    print("\n⏳ Добавление вехи...")
                    milestone = await client.projects.add_milestone(
                        int(project_id),
                        {"name": name}
                    )
                    print(f"\n✅ Веха добавлена: {milestone}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")


async def test_project_history(client: MegaplanClient):
    """Test project history."""
    while True:
        print_menu(
            "История проекта",
            [
                ("1", "Показать историю изменений"),
                ("2", "Поиск в истории"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            project_id = input("ID проекта: ").strip()
            if project_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка истории проекта #{project_id}...")
                    history = await client.projects.get_history(int(project_id), limit=10)
                    print(f"\n✅ Записей в истории: {len(history)}")
                    for entry in history:
                        print(f"  - {entry}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            project_id = input("ID проекта: ").strip()
            query = input("Поисковый запрос: ").strip()
            if project_id.isdigit() and query:
                try:
                    print(f"\n⏳ Поиск в истории проекта #{project_id}...")
                    results = await client.projects.search_history(int(project_id), query, limit=10)
                    print(f"\n✅ Найдено записей: {len(results)}")
                    for entry in results:
                        print(f"  - {entry}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")


async def test_deals(client: MegaplanClient):
    """Test Deals resource."""
    while True:
        print_menu(
            "Deals (Сделки)",
            [
                ("1", "Список сделок (первые 5)"),
                ("2", "Поиск сделки по ID"),
                ("3", "🆕 Полная информация о сделке (get_full_details)"),
                ("4", "Создать тестовую сделку"),
                ("5", "Управление наблюдателями (auditors)"),
                ("6", "История изменений (history)"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print("\n⏳ Загрузка сделок...")
            try:
                deals = await client.deals.list(limit=5)
                print(f"\n✅ Найдено сделок: {len(deals)}")
                for deal in deals:
                    print(f"  - #{deal.id}: {deal.name}")
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            deal_id = input("Введите ID сделки: ").strip()
            if deal_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка сделки #{deal_id}...")
                    deal = await client.deals.get(int(deal_id))
                    print("\n✅ Сделка найдена:")
                    print(f"  ID: {deal.id}")
                    print(f"  Название: {deal.name}")
                    print(f"  Программа: {deal.program}")
                    if deal.responsible:
                        responsible_str = await format_employee_from_entity(client, deal.responsible)
                        print(f"  Ответственный: {responsible_str}")

                    # Load and display comments
                    print("\n⏳ Загрузка комментариев...")
                    comments = await client.deals.get_comments(int(deal_id), limit=5)
                    if comments:
                        print(f"\n💬 Комментарии ({len(comments)}):")
                        for comment in comments:
                            author_str = "Неизвестен"
                            if comment.owner:
                                author_str = await format_employee_from_entity(client, comment.owner)
                            text_preview = (comment.content or "")[:50]
                            print(f"  - #{comment.id} от {author_str}: {text_preview}...")
                    else:
                        print("\n💬 Комментариев нет")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "3":
            await test_deal_full_details(client)

        elif choice == "4":
            name = input("Название сделки: ").strip() or "Тестовая сделка из SDK"
            try:
                print("\n⏳ Создание сделки...")
                deal = await client.deals.create({"name": name})
                print("\n✅ Сделка создана!")
                print(f"  ID: {deal.id}")
                print(f"  Название: {deal.name}")
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "5":
            await test_deal_auditors(client)

        elif choice == "6":
            await test_deal_history(client)


async def test_deal_auditors(client: MegaplanClient):
    """Test deal auditors."""
    while True:
        print_menu(
            "Наблюдатели сделки",
            [
                ("1", "Список наблюдателей (auditors)"),
                ("2", "Добавить наблюдателя"),
                ("3", "Удалить наблюдателя"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            deal_id = input("ID сделки: ").strip()
            if deal_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка наблюдателей сделки #{deal_id}...")
                    auditors = await client.deals.get_auditors(int(deal_id))
                    print(f"\n✅ Наблюдателей: {len(auditors)}")
                    for auditor in auditors:
                        print(f"  - {auditor}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            deal_id = input("ID сделки: ").strip()
            auditor_id = input("ID сотрудника (auditor): ").strip()
            if deal_id.isdigit() and auditor_id.isdigit():
                try:
                    print("\n⏳ Добавление наблюдателя...")
                    result = await client.deals.add_auditor(int(deal_id), int(auditor_id))
                    print(f"\n✅ Наблюдатель добавлен: {result}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "3":
            deal_id = input("ID сделки: ").strip()
            auditor_id = input("ID наблюдателя для удаления: ").strip()
            if deal_id.isdigit() and auditor_id.isdigit():
                try:
                    print("\n⏳ Удаление наблюдателя...")
                    await client.deals.remove_auditor(int(deal_id), int(auditor_id))
                    print("\n✅ Наблюдатель удален")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")


async def test_deal_history(client: MegaplanClient):
    """Test deal history."""
    while True:
        print_menu(
            "История сделки",
            [
                ("1", "Показать историю изменений"),
                ("2", "Поиск в истории"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            deal_id = input("ID сделки: ").strip()
            if deal_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка истории сделки #{deal_id}...")
                    history = await client.deals.get_history(int(deal_id), limit=10)
                    print(f"\n✅ Записей в истории: {len(history)}")
                    for entry in history:
                        print(f"  - {entry}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            deal_id = input("ID сделки: ").strip()
            query = input("Поисковый запрос: ").strip()
            if deal_id.isdigit() and query:
                try:
                    print(f"\n⏳ Поиск в истории сделки #{deal_id}...")
                    results = await client.deals.search_history(int(deal_id), query, limit=10)
                    print(f"\n✅ Найдено записей: {len(results)}")
                    for entry in results:
                        print(f"  - {entry}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")


async def test_comments(client: MegaplanClient):
    """Test Comments resource."""
    while True:
        print_menu(
            "Comments (Комментарии)",
            [
                ("1", "Список комментариев для задачи"),
                ("2", "Создать комментарий к задаче"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            task_id = input("ID задачи: ").strip()
            if task_id.isdigit():
                try:
                    print(f"\n⏳ Загрузка комментариев для задачи #{task_id}...")
                    comments = await client.comments.list(entity_id=int(task_id), limit=10)
                    print(f"\n✅ Найдено комментариев: {len(comments)}")
                    for comment in comments:
                        author_str = "Неизвестен"
                        if comment.owner:
                            author_str = await format_employee_from_entity(client, comment.owner)
                        text_preview = (comment.content or "")[:50]
                        print(f"  - #{comment.id} от {author_str}: {text_preview}...")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            task_id = input("ID задачи для комментария: ").strip()
            text = input("Текст комментария: ").strip()
            if task_id.isdigit() and text:
                try:
                    print("\n⏳ Создание комментария...")
                    comment = await client.comments.create(
                        entity_id=int(task_id),
                        content=text,
                    )
                    print("\n✅ Комментарий создан!")
                    print(f"  ID: {comment.id}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")


async def test_contractors(client: MegaplanClient):
    """Test Contractors resource."""
    while True:
        print_menu(
            "Contractors (Контрагенты)",
            [
                ("1", "Список контрагентов (первые 5)"),
                ("2", "Поиск контрагента"),
                ("3", "Создать компанию"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print("\n⏳ Загрузка контрагентов...")
            try:
                contractors = await client.contractors.list(limit=5)
                print(f"\n✅ Найдено контрагентов: {len(contractors)}")
                for contractor in contractors:
                    print(f"  - #{contractor.id}: {contractor.name} ({contractor.content_type})")
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            query = input("Поисковый запрос: ").strip()
            if query:
                try:
                    print(f"\n⏳ Поиск '{query}'...")
                    contractors = await client.contractors.list(q=query, limit=5)
                    print(f"\n✅ Найдено: {len(contractors)}")
                    for contractor in contractors:
                        print(f"  - #{contractor.id}: {contractor.name}")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "3":
            name = input("Название компании: ").strip() or "Тестовая компания"
            try:
                print("\n⏳ Создание компании...")
                contractor = await client.contractors.create(
                    {"contentType": "ContractorCompany", "name": name}
                )
                print("\n✅ Компания создана!")
                print(f"  ID: {contractor.id}")
                print(f"  Название: {contractor.name}")
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")


async def test_employees(client: MegaplanClient):
    """Test Employees resource."""
    while True:
        print_menu(
            "Employees (Сотрудники)",
            [
                ("1", "Список сотрудников (первые 5)"),
                ("2", "Текущий пользователь"),
                ("3", "Поиск сотрудника"),
            ],
        )

        choice = input("Выберите действие: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print("\n⏳ Загрузка сотрудников...")
            try:
                employees = await client.employees.list(limit=5)
                print(f"\n✅ Найдено сотрудников: {len(employees)}")
                for employee in employees:
                    name = f"{employee.first_name or ''} {employee.last_name or ''}".strip()
                    print(f"  - #{employee.id}: {name} ({employee.email})")
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "2":
            try:
                print("\n⏳ Загрузка информации о текущем пользователе...")
                me = await client.employees.get_current()
                print("\n✅ Текущий пользователь:")
                print(f"  ID: {me.id}")
                print(f"  Email: {me.email}")
                print(f"  Имя: {me.first_name} {me.last_name}")
                print(f"  Должность: {me.position}")
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")

        elif choice == "3":
            query = input("Поисковый запрос (имя или email): ").strip()
            if query:
                try:
                    print(f"\n⏳ Поиск '{query}'...")
                    employees = await client.employees.list(q=query, limit=5)
                    print(f"\n✅ Найдено: {len(employees)}")
                    for employee in employees:
                        name = f"{employee.first_name or ''} {employee.last_name or ''}".strip()
                        print(f"  - #{employee.id}: {name} ({employee.email})")
                except Exception as e:
                    print(f"\n❌ Ошибка: {e}")
            input("\nНажмите Enter...")


async def main_menu(client: MegaplanClient):
    """Main menu."""
    while True:
        clear_screen()
        print_menu(
            "Megaplan SDK - Test Application",
            [
                ("1", "Tasks (Задачи)"),
                ("2", "Projects (Проекты)"),
                ("3", "Deals (Сделки)"),
                ("4", "Comments (Комментарии)"),
                ("5", "Contractors (Контрагенты)"),
                ("6", "Employees (Сотрудники)"),
            ],
        )
        print("  [c] 📊 Статистика кэша пользователей")
        print("  [x] 🗑️  Очистить кэш пользователей")
        print("  [q] Выход")
        print()

        choice = input("Выберите раздел: ").strip().lower()

        if choice == "q" or choice == "0":
            print("\n👋 До свидания!")
            break
        elif choice == "c":
            # Show cache statistics
            stats = get_cache_stats()
            print("\n📊 Статистика кэша пользователей:")
            print_separator()
            print(f"  Размер кэша: {stats['size']} пользователей")
            print(f"  Попаданий в кэш: {stats['hits']}")
            print(f"  Промахов: {stats['misses']}")
            if stats['hits'] + stats['misses'] > 0:
                print(f"  Hit rate: {stats['hit_rate']:.1%}")
            print_separator()
            input("\nНажмите Enter...")
        elif choice == "x":
            # Clear cache
            clear_employee_cache()
            print("\n✅ Кэш пользователей очищен!")
            input("\nНажмите Enter...")
        elif choice == "1":
            await test_tasks(client)
        elif choice == "2":
            await test_projects(client)
        elif choice == "3":
            await test_deals(client)
        elif choice == "4":
            await test_comments(client)
        elif choice == "5":
            await test_contractors(client)
        elif choice == "6":
            await test_employees(client)
        else:
            print("\n❌ Неверный выбор")
            input("Нажмите Enter...")


async def main():
    """Main entry point."""
    clear_screen()
    print_header("Megaplan SDK - Test Application")

    # Get credentials
    print("\n📝 Введите credentials:")
    base_url = input("  Base URL (https://company.megaplan.ru): ").strip()
    username = input("  Username (email): ").strip()
    password = input("  Password: ").strip()

    if not all([base_url, username, password]):
        print("\n❌ Все поля обязательны!")
        return

    # Setup logging
    log_level = os.getenv("LOG_LEVEL", "WARNING")
    setup_logging(log_level)

    # Initialize client
    print("\n⏳ Подключение к Megaplan...")

    try:
        async with MegaplanClient(
            base_url=base_url,
            username=username,
            password=password,
            log_level=log_level,
        ) as client:
            print("✅ Успешная авторизация!")
            input("\nНажмите Enter для продолжения...")

            # Main menu
            await main_menu(client)

    except Exception as e:
        print(f"\n❌ Ошибка подключения: {e}")
        print("\nПроверьте:")
        print("  - Корректность URL (должен начинаться с https://)")
        print("  - Правильность username и password")
        print("  - Доступность сервера Megaplan")


if __name__ == "__main__":
    asyncio.run(main())
