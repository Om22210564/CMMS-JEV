"""Runtime configuration loaded only from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    model: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            api_key=os.getenv("TYPESAFE_API_KEY"),
            model=os.getenv("TYPESAFE_MODEL"),
        )
