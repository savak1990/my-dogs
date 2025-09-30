from functools import lru_cache
from dogs_common.config import AppConfig, get_config
from dogs_common.s3 import get_s3_client


class DogsImageProcessor:
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config
        self.s3 = get_s3_client(app_config=app_config)

@lru_cache(maxsize=1)
def get_processor() -> DogsImageProcessor:
    app_config = get_config()
    return DogsImageProcessor(app_config=app_config)