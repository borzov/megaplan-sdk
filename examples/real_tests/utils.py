"""Utility functions for real API tests."""

import os
from pathlib import Path


def load_env_file(env_path: Path | None = None) -> bool:
    """Load .env file if exists.

    Args:
        env_path: Path to .env file. If None, looks in the same directory as this file.

    Returns:
        True if .env file was loaded, False otherwise.
    """
    if env_path is None:
        env_path = Path(__file__).parent / ".env"

    if env_path.exists():
        print(f"📄 Загрузка переменных из {env_path}")
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Don't override existing env vars
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()
        return True
    return False


def get_credentials() -> tuple[str, str, str] | None:
    """Get Megaplan credentials from environment variables.

    Returns:
        Tuple of (base_url, username, password) or None if not all vars are set.
    """
    base_url = os.getenv("MEGAPLAN_BASE_URL")
    username = os.getenv("MEGAPLAN_USERNAME")
    password = os.getenv("MEGAPLAN_PASSWORD")

    if not all([base_url, username, password]):
        print("\n❌ Ошибка: Необходимо установить переменные окружения:")
        print("   MEGAPLAN_BASE_URL (например, https://company.megaplan.ru)")
        print("   MEGAPLAN_USERNAME (ваш email)")
        print("   MEGAPLAN_PASSWORD (ваш пароль)")
        print("\nПример:")
        print('   export MEGAPLAN_BASE_URL="https://company.megaplan.ru"')
        print('   export MEGAPLAN_USERNAME="user@example.com"')
        print('   export MEGAPLAN_PASSWORD="your_password"')
        print("\nИли создайте файл .env в examples/real_tests/")
        return None

    return base_url, username, password


def print_header(title: str) -> None:
    """Print formatted test header.

    Args:
        title: Test title.
    """
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_success(message: str) -> None:
    """Print success message.

    Args:
        message: Success message.
    """
    print(f"\n✅ {message}")


def print_warning(message: str) -> None:
    """Print warning message.

    Args:
        message: Warning message.
    """
    print(f"\n⚠️  {message}")


def print_error(message: str) -> None:
    """Print error message.

    Args:
        message: Error message.
    """
    print(f"\n❌ {message}")


async def get_employee_display(client, employee_ref) -> str:
    """Get employee display name from reference.

    Args:
        client: MegaplanClient instance.
        employee_ref: Employee BaseEntity reference.

    Returns:
        Employee display name or fallback string.
    """
    if not employee_ref:
        return "Не указан"
    
    try:
        # Try to get from cache first (if expand was used)
        if hasattr(employee_ref, 'first_name'):
            return employee_ref.display_name()
        
        # Load from API using cache
        from megaplan_sdk.models.employee import Employee
        employee = await client.employees._get_entity_cached(
            "employee", employee_ref.id, Employee
        )
        return employee.display_name()
    except Exception:
        return f"Employee #{employee_ref.id}"


async def get_department_display(client, department_ref) -> str:
    """Get department name from reference.

    Args:
        client: MegaplanClient instance.
        department_ref: Department BaseEntity reference.

    Returns:
        Department name or fallback string.
    """
    if not department_ref:
        return "Не указан"
    
    try:
        # Try to get from cache first (if expand was used)
        if hasattr(department_ref, 'name'):
            return department_ref.name
        
        # Load from API using cache
        from megaplan_sdk.models.department import Department
        department = await client.departments._get_entity_cached(
            "department", department_ref.id, Department
        )
        return department.name
    except Exception:
        return f"Department #{department_ref.id}"


async def get_contractor_display(client, contractor_ref) -> str:
    """Get contractor display name from reference.

    Args:
        client: MegaplanClient instance.
        contractor_ref: Contractor BaseEntity reference.

    Returns:
        Contractor display name or fallback string.
    """
    if not contractor_ref:
        return "Не указан"
    
    try:
        # Try to get from cache first (if expand was used)
        if hasattr(contractor_ref, 'name'):
            return contractor_ref.display_name()
        
        # Load from API using cache
        from megaplan_sdk.models.contractor import Contractor
        contractor = await client.contractors._get_entity_cached(
            "contractor", contractor_ref.id, Contractor
        )
        return contractor.display_name()
    except Exception:
        return f"Contractor #{contractor_ref.id}"


async def get_comment_owner_display(client, comment) -> str:
    """Get comment owner display name.

    Args:
        client: MegaplanClient instance.
        comment: Comment object with owner field.

    Returns:
        Owner display name or fallback string.
    """
    if not comment or not comment.owner:
        return "Неизвестный автор"
    
    return await get_employee_display(client, comment.owner)
