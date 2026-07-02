from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import requests

from .validators import OrderRequest, format_decimal


DEFAULT_BASE_URL = "https://testnet.binancefuture.com"


class BinanceAPIError(RuntimeError):
    """Raised when Binance returns a non-2xx response or invalid payload."""


class BinanceClient:
    """Small Binance USDT-M Futures REST wrapper.

    Uses direct signed REST calls instead of hiding the task behind a large SDK.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str | None = None,
        timeout: int = 15,
        logger: logging.Logger | None = None,
        dry_run: bool = False,
    ) -> None:
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        self.base_url = (base_url or os.getenv("BINANCE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.logger = logger or logging.getLogger("trading_bot")
        self.dry_run = dry_run

    def _mask_key(self) -> str:
        if not self.api_key:
            return "not-set"
        if len(self.api_key) <= 8:
            return "****"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

    def _sign(self, params: dict[str, Any]) -> str:
        if not self.api_secret:
            raise BinanceAPIError("BINANCE_API_SECRET is missing. Add it to environment or use --dry-run.")
        query = urlencode(params, doseq=True)
        return hmac.new(self.api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()

    def _request(self, method: str, endpoint: str, params: dict[str, Any] | None = None, signed: bool = False) -> dict[str, Any]:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        headers: dict[str, str] = {}

        if signed:
            if not self.api_key:
                raise BinanceAPIError("BINANCE_API_KEY is missing. Add it to environment or use --dry-run.")
            params.setdefault("timestamp", int(time.time() * 1000))
            params.setdefault("recvWindow", 5000)
            params["signature"] = self._sign(params)
            headers["X-MBX-APIKEY"] = self.api_key

        safe_params = {k: ("<hidden>" if k == "signature" else v) for k, v in params.items()}
        self.logger.info(
            "API request | method=%s endpoint=%s base_url=%s api_key=%s params=%s",
            method.upper(), endpoint, self.base_url, self._mask_key(), json.dumps(safe_params, default=str),
        )

        try:
            response = self.session.request(
                method=method.upper(),
                url=f"{self.base_url}{endpoint}",
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            self.logger.exception("Network failure while calling Binance: %s", exc)
            raise BinanceAPIError(f"Network failure: {exc}") from exc

        text = response.text[:4000]
        self.logger.info("API response | status=%s body=%s", response.status_code, text)

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": text}

        if not response.ok:
            # payload is always a dict here (either Binance's JSON body, e.g.
            # {"code": -1121, "msg": "Invalid symbol."}, or our {"raw": text}
            # fallback for a non-JSON error body such as an HTML gateway page).
            # Binance's own error fields take priority; fall back to the raw
            # HTTP status/body so a non-JSON failure is never reported as
            # "None: None".
            msg = payload.get("msg") or text or "no response body"
            code = payload.get("code") if payload.get("code") is not None else response.status_code
            self.logger.error("Binance API error | code=%s message=%s", code, msg)
            raise BinanceAPIError(f"Binance API error {code}: {msg}")

        if not isinstance(payload, dict):
            raise BinanceAPIError("Unexpected Binance response format.")
        return payload

    def place_order(self, order: OrderRequest) -> dict[str, Any]:
        """Place a Binance Futures order or return a realistic dry-run response."""
        params: dict[str, Any] = {
            "symbol": order.symbol,
            "side": order.side,
            "type": order.order_type,
            "quantity": format_decimal(order.quantity),
            "newOrderRespType": "RESULT",
        }

        if order.order_type == "LIMIT":
            params["timeInForce"] = "GTC"
            params["price"] = format_decimal(order.price) if order.price is not None else None
        elif order.order_type == "STOP":
            # Binance Futures stop-limit order: order waits for stopPrice, then places a LIMIT at price.
            params["timeInForce"] = "GTC"
            params["price"] = format_decimal(order.price) if order.price is not None else None
            params["stopPrice"] = format_decimal(order.stop_price) if order.stop_price is not None else None
            params["workingType"] = "MARK_PRICE"

        if self.dry_run:
            synthetic_id = int(time.time() * 1000) % 1_000_000_000
            response = {
                "dryRun": True,
                "orderId": synthetic_id,
                "symbol": order.symbol,
                "status": "DRY_RUN_ACCEPTED",
                "clientOrderId": f"dry_{synthetic_id}",
                "price": str(params.get("price", "0")),
                "avgPrice": str(params.get("price", "0")) if order.order_type != "MARKET" else "0.00",
                "origQty": format_decimal(order.quantity),
                "executedQty": "0",
                "side": order.side,
                "type": order.order_type,
                "message": "No exchange call was made. Remove --dry-run and set testnet API credentials for live testnet orders.",
            }
            self.logger.info("DRY RUN order request | params=%s", json.dumps(params, default=str))
            self.logger.info("DRY RUN order response | body=%s", json.dumps(response, default=str))
            return response

        return self._request("POST", "/fapi/v1/order", params=params, signed=True)
