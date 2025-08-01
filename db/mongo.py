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
            logging.info(f"Error to connect MongoDB: {e}")

            raise

        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def find_json_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Найти JSON-документ по имени (поле 'name').
        :param name: Значение поля 'name'.
        :return: Найденный документ или None.
        """
        try:
            result = self.collection.find_one({"name": name})
            if result:
                logging.info(f"🔍 Документ найден: {name}")
            else:
                logging.warning(f"⚠️ Документ не найден: {name}")
            return result
        except PyMongoError as e:
            logging.error(f"Ошибка при поиске документа '{name}': {e}")
            return None

    def update_json_by_name(self, name: str, new_data: Dict[str, Any]) -> bool:
        """
        Обновить JSON-документ по имени (поле 'name').
        :param name: Значение поля 'name'.
        :param new_data: Новые данные (ключи и значения, которые нужно обновить).
        :return: True, если документ обновлён.
        """
        try:
            result = self.collection.update_one(
                {"name": name},
                {"$set": new_data}
            )
            if result.modified_count > 0:
                logging.info(f"✅ Документ '{name}' успешно обновлён.")
                return True
            else:
                logging.warning(f"⚠️ Документ '{name}' не обновлён.")
                return False
        except PyMongoError as e:
            logging.error(f"Ошибка при обновлении документа '{name}': {e}")
            return False

    def create_json(self, data: Dict[str, Any]) -> bool:
        """
        Создаёт новый JSON-документ в коллекции.
        Если документ с таким 'name' уже существует — вставка не произойдёт.
        :param data: JSON-данные, обязательно должно быть поле 'name'.
        :return: True если успешно создан, иначе False.
        """
        if "name" not in data:
            logging.error("❌ Документ должен содержать поле 'name'.")
            return False

        if self.find_json_by_name(data["name"]):
            logging.warning(f"⚠️ Документ с именем '{data['name']}' уже существует.")
            return False

        try:
            self.collection.insert_one(data)
            logging.info(f"✅ Документ '{data['name']}' успешно создан.")
            return True
        except PyMongoError as e:
            logging.error(f"Ошибка при создании документа '{data['name']}': {e}")
            return False