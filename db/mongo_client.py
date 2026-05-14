from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import MONGO_URI, MONGO_DB, MONGO_COLLECTION


class CarsDB:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DB]
        self.collection = self.db[MONGO_COLLECTION]
        self.collection.create_index("lot_number", unique=True)

    def insert_car(self, car_data: dict) -> bool:
        car_data["scraped_at"] = datetime.now(timezone.utc)
        try:
            self.collection.insert_one(car_data)
            print(f"[DB] Saved lot {car_data.get('lot_number')}")
            return True
        except DuplicateKeyError:
            print(f"[DB] Lot {car_data.get('lot_number')} already exists, skipping")
            return False

    def lot_exists(self, lot_number: str) -> bool:
        return self.collection.find_one({"lot_number": lot_number}) is not None

    def close(self):
        self.client.close()
