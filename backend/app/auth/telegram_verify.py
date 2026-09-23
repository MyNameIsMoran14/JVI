import hashlib
import hmac
import time
from urllib.parse import parse_qsl

MAX_AUTH_AGE_SECONDS = 24 * 60 * 60


class InitDataError(ValueError):
    pass


def verify_init_data(init_data: str, bot_token: str) -> dict[str, str]:
    """Verifies Telegram Mini App `initData` per Telegram's documented HMAC scheme.

    Returns the parsed key/value pairs (still containing `user` as a JSON string) on success,
    raises InitDataError otherwise. https://core.telegram.org/bots/webapps#validating-data
    """
    pairs = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("missing hash")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InitDataError("invalid signature")

    auth_date = pairs.get("auth_date")
    if not auth_date or not auth_date.isdigit():
        raise InitDataError("missing auth_date")
    if time.time() - int(auth_date) > MAX_AUTH_AGE_SECONDS:
        raise InitDataError("stale auth_date")

    return pairs
