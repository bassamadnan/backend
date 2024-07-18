"""This module contains the settings for the application."""

import os
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

DATABASE_URL = os.getenv("DATABASE_URL")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES"))
ALGORITHM = os.getenv("ALGORITHM")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY")
OM2M_URL = os.getenv("OM2M_URL")
OM2M_USERNAME = os.getenv("OM2M_USERNAME")
OM2M_PASSWORD = os.getenv("OM2M_PASSWORD")
ROOT_PATH = os.getenv("ROOT_PATH") or '/'
MOBIUS_XM2MRI = os.getenv("MOBIUS_XM2MRI")
BROKER_ADDR = str(os.getenv("BROKER_ADDR", "127.0.0.1"))
BORKER_PORT = int(os.getenv("BORKER_PORT", 1883))
DEFAULT_TOPIC = str(os.getenv("DEFAULT_TOPIC", "oneM2M/req/#"))
