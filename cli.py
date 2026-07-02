from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import configure_logging
from bot.orders import OrderService, response_summary
from bot.validators import VALID_ORDER_TYPES, VALID_SIDES, ValidationError, validate_order_input


def load_dotenv(path: str | Path = ".env") -> None:
    """Tiny .env loader to keep the project dependency-light."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        # Strip inline comments (e.g. KEY=value # comment)
        value = value.split(" #")[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def yes_no(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place Binance USDT-M Futures Testnet orders from the command line.",
    )
    parser.add_argument("--symbol", help="Trading pair, e.g. BTCUSDT")
    parser.add_argument(
        "--side", type=lambda s: s.strip().upper(), choices=sorted(VALID_SIDES), help="BUY or SELL (case-insensitive)"
    )
    parser.add_argument(
        "--type",
        dest="order_type",
        type=lambda s: s.strip().upper(),
        choices=sorted(VALID_ORDER_TYPES),
        help="MARKET, LIMIT, or STOP (case-insensitive)",
    )
    parser.add_argument("--quantity", help="Order quantity, e.g. 0.001")
    parser.add_argument("--price", help="Limit price (required for LIMIT and STOP)")
    parser.add_argument("--stop-price", help="Trigger price (required for STOP)")
    parser.add_argument("--dry-run", action="store_true", help="Validate and log the order without sending it to Binance")
    parser.add_argument("--log-file", default="logs/trading_bot.log", help="Where to write API/order logs")
    parser.add_argument("--base-url", default=None, help="Override Binance base URL")
    parser.add_argument("--interactive", "-i", action="store_true", help="Use a guided prompt flow")
    return parser


def prompt_choice(label: str, choices: list[str]) -> str:
    print(f"\n{label}")
    for idx, choice in enumerate(choices, start=1):
        print(f"  {idx}. {choice}")
    while True:
        answer = input("Choose number: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1]
        print("Please choose a listed number.")


def interactive_args() -> dict[str, Any]:
    print("\nBinance Futures Testnet Order Desk")
    print("A careful, guided flow — no order is sent until validation passes.\n")
    symbol = input("Symbol [BTCUSDT]: ").strip() or "BTCUSDT"
    side = prompt_choice("Side", ["BUY", "SELL"])
    order_type = prompt_choice("Order type", ["MARKET", "LIMIT", "STOP"])
    quantity = input("Quantity (example 0.001): ").strip()
    price = None
    stop_price = None
    if order_type in {"LIMIT", "STOP"}:
        price = input("Limit price: ").strip()
    if order_type == "STOP":
        stop_price = input("Stop trigger price: ").strip()
    dry_run_answer = input("Dry run first? [Y/n]: ").strip().lower()
    return {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
        "stop_price": stop_price,
        "dry_run": dry_run_answer not in {"n", "no"},
    }


def print_human_output(order_dict: dict[str, Any], response: dict[str, Any]) -> None:
    print("\nOrder request")
    print("-------------")
    for key, value in order_dict.items():
        if value is not None:
            print(f"{key:>11}: {value}")

    summary = response_summary(response)
    print("\nExchange response")
    print("-----------------")
    for key in ["orderId", "status", "executedQty", "avgPrice", "symbol", "side", "type", "dryRun"]:
        print(f"{key:>11}: {summary.get(key)}")

    if summary.get("dryRun"):
        print("\nSUCCESS: dry-run passed. Set testnet credentials and remove --dry-run to send the order.")
    else:
        print("\nSUCCESS: order accepted by Binance Futures Testnet.")


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    logger = configure_logging(args.log_file)

    try:
        values = interactive_args() if args.interactive else vars(args)
        order = validate_order_input(
            symbol=values.get("symbol"),
            side=values.get("side"),
            order_type=values.get("order_type"),
            quantity=values.get("quantity"),
            price=values.get("price"),
            stop_price=values.get("stop_price"),
        )
        dry_run = bool(values.get("dry_run")) or yes_no(os.getenv("BINANCE_DRY_RUN"))
        client = BinanceClient(base_url=args.base_url, logger=logger, dry_run=dry_run)
        service = OrderService(client=client, logger=logger)
        response = service.place(order)
        print_human_output(order.as_display_dict(), response)
        logger.info("Completed successfully | summary=%s", json.dumps(response_summary(response), default=str))
        return 0
    except ValidationError as exc:
        logger.error("Validation failed: %s", exc)
        print(f"\nFAILED: {exc}", file=sys.stderr)
        return 2
    except BinanceAPIError as exc:
        logger.error("API failure: %s", exc)
        print(f"\nFAILED: {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        logger.warning("User cancelled from keyboard")
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
