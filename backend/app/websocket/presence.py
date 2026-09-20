import hashlib
from dataclasses import asdict, dataclass
from typing import Dict, Optional

# Curated high-contrast IDE presence colors
PRESENCE_COLORS = [
    "#3b82f6",  # Blue
    "#10b981",  # Emerald
    "#f59e0b",  # Amber
    "#ef4444",  # Red
    "#8b5cf6",  # Violet
    "#ec4899",  # Pink
    "#06b6d4",  # Cyan
    "#14b8a6",  # Teal
    "#f97316",  # Orange
    "#a855f7",  # Purple
]


def get_user_color(user_id: str) -> str:
    """Deterministically assign a vibrant color to a user."""
    hash_val = int(hashlib.md5(user_id.encode("utf-8")).hexdigest(), 16)
    return PRESENCE_COLORS[hash_val % len(PRESENCE_COLORS)]


@dataclass
class UserCursor:
    line: int
    column: int


@dataclass
class UserSelection:
    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass
class UserPresence:
    user_id: str
    username: str
    avatar_url: Optional[str]
    color: str
    current_file: Optional[str]
    cursor: Optional[UserCursor]
    selection: Optional[UserSelection]
    is_online: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)
