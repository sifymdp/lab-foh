from typing import Literal

Role = Literal["OWNER", "MANAGER", "HOST", "WAITER"]


def normalize_role(role: str) -> str:
    return role.strip().upper()


def can_edit_floor(role: str) -> bool:
    return normalize_role(role) in ("OWNER", "MANAGER")


def can_manage_users(role: str) -> bool:
    return normalize_role(role) == "OWNER"


def can_manage_menu(role: str) -> bool:
    return normalize_role(role) in ("OWNER", "MANAGER")


def can_manage_reservations(role: str) -> bool:
    return normalize_role(role) in ("OWNER", "MANAGER", "HOST")
