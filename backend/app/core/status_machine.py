from typing import Literal

TableStatus = Literal[
    "AVAILABLE",
    "RESERVED",
    "SEATED",
    "ACTIVE",
    "BILLING",
    "PAID",
    "CLEANING",
]

# Every valid one-step transition in the table lifecycle.
# AVAILABLE → SEATED  : camera detects guests (3 consecutive scans) or host manual seat
# AVAILABLE → RESERVED: host creates a reservation
# RESERVED  → SEATED  : host seats a reserved party
# RESERVED  → AVAILABLE: manual release or auto-release on no-show
# SEATED    → ACTIVE  : guest places first QR order
# SEATED    → BILLING : guest requests bill before ordering (edge case)
# ACTIVE    → BILLING : guest taps Request Bill
# BILLING   → PAID    : Stripe webhook confirms payment or staff taps Mark Paid
# PAID      → CLEANING: automatic immediately after payment confirmed
# CLEANING  → AVAILABLE: camera confirms clean or time-based fallback
STATUS_TRANSITIONS: dict[str, list[str]] = {
    "AVAILABLE": ["RESERVED", "SEATED"],
    "RESERVED":  ["AVAILABLE", "SEATED"],
    "SEATED":    ["ACTIVE", "BILLING"],
    "ACTIVE":    ["BILLING"],
    "BILLING":   ["PAID"],
    "PAID":      ["CLEANING"],
    "CLEANING":  ["AVAILABLE"],
}

# Statuses that mean the table is occupied by a live session
ACTIVE_SESSION_STATUSES = {"SEATED", "ACTIVE", "BILLING", "PAID"}


def is_valid_transition(current: str, target: str) -> bool:
    return target in STATUS_TRANSITIONS.get(current, [])
