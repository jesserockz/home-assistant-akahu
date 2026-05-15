"""Constants for the Akahu integration."""

from datetime import timedelta
import logging

DOMAIN = "akahu"

LOGGER = logging.getLogger(__package__)

CONF_APP_TOKEN = "app_token"
CONF_USER_TOKEN = "user_token"

UPDATE_INTERVAL = timedelta(minutes=10)
