from aws_lambda_powertools import Logger, Tracer
from aws_xray_sdk.core import patch_all
from .config import get_config

# Apply X-Ray patching early at module import time
patch_all()

# Get config once at module import time
_config = get_config()

# Create shared logger and tracer instances with consistent configuration
logger = Logger(
    service=_config.powertools_service_name,
    level=_config.log_level
)

tracer = Tracer(
    service=_config.powertools_service_name
)