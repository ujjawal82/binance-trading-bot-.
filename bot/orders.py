from __future__ import annotations

import logging
from typing import Any

from .client import BinanceClient
from .validators import OrderRequest


class OrderService:
    """Application service layer for order placement."""

    def __init__(self, client: BinanceClient, logger: logging.Logger | None = None) -> None:
        self.client = client
        self.logger = logger or logging.getLogger("trading_bot")

    def place(self, order: OrderRequest) -> dict[str, Any]:
        self.logger.info("Order service received request | %s", order.as_display_dict())
        return self.client.place_order(order)


def response_summary(response: dict[str, Any]) -> dict[str, Any]:
    """Extract the fields reviewers care about, keeping raw data available elsewhere."""
    return {
        "orderId": response.get("orderId"),
        "status": response.get("status"),
        "executedQty": response.get("executedQty"),
        "avgPrice": response.get("avgPrice") or response.get("averagePrice") or response.get("price"),
        "symbol": response.get("symbol"),
        "side": response.get("side"),
        "type": response.get("type"),
        "dryRun": response.get("dryRun", False),
    }
