from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
import os
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, Any

load_dotenv("data/.env")

class MongoAPI:
    def __init__(self, uri=None, db_name=None, collection_name=None):
        self.uri = uri or os.getenv("MONGO_URI")
        self.db_name = db_name or os.getenv("MONGO_DB_NAME")
        self.collection_name = collection_name

        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            logging.info("Connected to MongoDB")
        except ConnectionFailure as e:
            logging.error(f"Error to connect MongoDB: {e}")
            raise

        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def find_by_date_and_unit(self, date, unit) -> Optional[Dict[str, Any]]:
        try:
            result = self.collection.find_one({"date": date, "unit": unit})
            if result:
                logging.info(f"Документ найден: {date}, unit: {unit}")
            else:
                logging.warning(f"Документ не найден: {date}, unit: {unit}")
            return result
        except PyMongoError as e:
            logging.error(f"Ошибка при поиске документа: {e}")
            return None

    def update_by_date_and_unit(self, date, unit, data: Dict[str, Any]) -> bool:
        try:
            result = self.collection.update_one(
                {"date": date, "unit": unit},
                {"$set": data}
            )
            if result.modified_count > 0:
                logging.info(f"Документ обновлён: {date}, unit: {unit}")
                return True
            else:
                logging.warning(f"⚠Документ не был обновлён: {date}, unit: {unit}")
                return False
        except PyMongoError as e:
            logging.error(f"Ошибка при обновлении документа: {e}")
            return False

    def create_json(self, data: Dict[str, Any]) -> bool:
        if "date" not in data or "unit" not in data:
            logging.error("Документ должен содержать поля 'date' и 'unit'.")
            return False

        if self.find_by_date_and_unit(data["date"], data["unit"]):
            logging.warning(f"⚠Документ уже существует: {data['date']}, unit: {data['unit']}")
            return False

        try:
            self.collection.insert_one(data)
            logging.info(f"Документ создан: {data['date']}, unit: {data['unit']}")
            return True
        except PyMongoError as e:
            logging.error(f"Ошибка при создании документа: {e}")
            return False
