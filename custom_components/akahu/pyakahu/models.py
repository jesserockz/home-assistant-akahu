"""Dataclasses representing Akahu API objects."""

from dataclasses import dataclass
from typing import Any, Self


@dataclass(frozen=True, kw_only=True)
class AkahuBalance:
    """Balance information for an account."""

    current: float | None
    available: float | None
    limit: float | None
    currency: str
    overdrawn: bool | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Self:
        """Build a balance from the API response."""
        return cls(
            current=data.get("current"),
            available=data.get("available"),
            limit=data.get("limit"),
            currency=data.get("currency", "NZD"),
            overdrawn=data.get("overdrawn"),
        )


@dataclass(frozen=True, kw_only=True)
class AkahuAccount:
    """A single Akahu account."""

    id: str
    name: str
    status: str
    type: str | None
    formatted_account: str | None
    connection_id: str | None
    connection_name: str | None
    balance: AkahuBalance

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Self:
        """Build an account from a single item in the API response."""
        connection = data.get("connection") or {}
        return cls(
            id=data["_id"],
            name=data["name"],
            status=data.get("status", "UNKNOWN"),
            type=data.get("type"),
            formatted_account=data.get("formatted_account"),
            connection_id=connection.get("_id"),
            connection_name=connection.get("name"),
            balance=AkahuBalance.from_api(data.get("balance") or {}),
        )


@dataclass(frozen=True, kw_only=True)
class AkahuUser:
    """The user associated with the access token."""

    id: str
    name: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Self:
        """Build a user from the API response."""
        return cls(
            id=data["_id"],
            name=data.get("preferred_name") or data.get("first_name"),
        )
