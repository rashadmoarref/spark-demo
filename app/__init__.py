#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
from logging.config import dictConfig

from app.config import settings

__logger = logging.getLogger(__name__)
dictConfig(settings.LOGGING)

# show loaded config
config = json.dumps(settings.as_dict(), indent=2)

__logger.info(
    f"Microservice initialized for ({settings.current_env} env) with: " f"{config}"
)
