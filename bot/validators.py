from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP"}
SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,30}$")


class ValidationError(ValueError):
    """Raised when user input is invalid before hitting the exchange."""


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None

    @property
    def is_limit_family(self) -> bool:
        return self.order_type in {"LIMIT", "STOP"}

    def as_display_dict(self) -> dict[str, str | None]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "type": self.order_type,
            "quantity": format_decimal(self.quantity),
            "price": format_decimal(self.price) if self.price is not None else None,
            "stop_price": format_decimal(self.stop_price) if self.stop_price is not None else None,
        }


def parse_positive_decimal(value: Any, field_name: str) -> Decimal:
    if value is None or str(value).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{field_name} must be a valid number.") from None
    if parsed <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return parsed


def format_decimal(value: Decimal) -> str:
    """Return a Binance-friendly decimal string without scientific notation."""
    normalized = format(value.normalize(), "f")
    # Decimal('1.0').normalize() formats as '1'; keep zero trimming safe.
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def validate_order_input(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Any,
    price: Any = None,
    stop_price: Any = None,
) -> OrderRequest:
    cleaned_symbol = (symbol or "").strip().upper()
    cleaned_side = (side or "").strip().upper()
    cleaned_type = (order_type or "").strip().upper().replace("-", "_")

    if not SYMBOL_RE.match(cleaned_symbol):
        raise ValidationError("symbol must be uppercase letters/numbers, for example BTCUSDT.")
    if cleaned_side not in VALID_SIDES:
        raise ValidationError("side must be BUY or SELL.")
    if cleaned_type not in VALID_ORDER_TYPES:
        raise ValidationError("order type must be MARKET, LIMIT, or STOP.")

    parsed_quantity = parse_positive_decimal(quantity, "quantity")
    parsed_price = None
    parsed_stop_price = None

    if cleaned_type == "MARKET":
        if price not in (None, ""):
            raise ValidationError("price is not used for MARKET orders.")
    elif cleaned_type == "LIMIT":
        parsed_price = parse_positive_decimal(price, "price")
    elif cleaned_type == "STOP":
        parsed_price = parse_positive_decimal(price, "price")
        parsed_stop_price = parse_positive_decimal(stop_price, "stop_price")

    return OrderRequest(
        symbol=cleaned_symbol,
        side=cleaned_side,
        order_type=cleaned_type,
        quantity=parsed_quantity,
        price=parsed_price,
        stop_price=parsed_stop_price,
    )
