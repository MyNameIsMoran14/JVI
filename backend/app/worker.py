from arq.connections import RedisSettings

import app.core.all_models  # noqa: F401
from app.core.config import settings
from app.extraction.tasks import parse_document


class WorkerSettings:
    functions = [parse_document]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
