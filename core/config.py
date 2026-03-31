import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dropship:dropship123@localhost:5432/dropship")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
FONNTE_API_KEY = os.getenv("FONNTE_API_KEY", "")
SUPPLIER_WA_PHONE = os.getenv("SUPPLIER_WA_PHONE", "")

INVOLVE_ASIA_API_KEY = os.getenv("INVOLVE_ASIA_API_KEY", "")
INVOLVE_ASIA_SECRET = os.getenv("INVOLVE_ASIA_SECRET", "")
SHOPEE_AFFILIATE_TOKEN = os.getenv("SHOPEE_AFFILIATE_TOKEN", "")

SHOPEE_PARTNER_ID = os.getenv("SHOPEE_PARTNER_ID", "")
SHOPEE_PARTNER_KEY = os.getenv("SHOPEE_PARTNER_KEY", "")
SHOPEE_SHOP_ID = os.getenv("SHOPEE_SHOP_ID", "")

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
FLOOR_MARGIN = float(os.getenv("FLOOR_MARGIN", "0.15"))
REPRICING_INTERVAL_HOURS = int(os.getenv("REPRICING_INTERVAL_HOURS", "6"))
INVENTORY_SYNC_INTERVAL_HOURS = int(os.getenv("INVENTORY_SYNC_INTERVAL_HOURS", "2"))
