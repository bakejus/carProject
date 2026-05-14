from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")

IMAGES_DIR = "images"

# Playwright settings
HEADLESS = False
TIMEOUT = 30000  # ms

# Image download
MAX_CONCURRENT_DOWNLOADS = 10
