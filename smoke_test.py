from cli import load_dotenv
load_dotenv()  # Load .env before any module reads environment variables

from bot.validators import validate_order_input, ValidationError
from bot.client import BinanceClient
from bot.logging_config import configure_logging
from bot.orders import OrderService, response_summary

logger = configure_logging('logs/smoke_test.log')

market = validate_order_input('BTCUSDT', 'BUY', 'MARKET', '0.001')
limit = validate_order_input('BTCUSDT', 'SELL', 'LIMIT', '0.001', price='95000')
client = BinanceClient(logger=logger, dry_run=True)
service = OrderService(client, logger)

for order in (market, limit):
    summary = response_summary(service.place(order))
    assert summary['status'] == 'DRY_RUN_ACCEPTED'
    print(summary)

try:
    validate_order_input('BTCUSDT', 'BUY', 'LIMIT', '0.001')
except ValidationError:
    print('validation check passed')
else:
    raise AssertionError('LIMIT without price should fail')

print('smoke test passed')
