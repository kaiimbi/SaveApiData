from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv

load_dotenv("data/.env")


class MongoAPI:
    def __init__(self, uri=None, db_name=None, collection_name=None):
        self.uri = uri or os.getenv("MONGO_URI")
        self.db_name = db_name or os.getenv("MONGO_DB_NAME")
        self.collection_name = collection_name or os.getenv("MONGO_COLLECTION_NAME")

        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')  # Проверка соединения
            print("✅ MongoDB подключение успешно")
        except ConnectionFailure as e:
            print(f"❌ Ошибка подключения к MongoDB: {e}")
            raise

        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def insert_one(self, data: dict):
        result = self.collection.insert_one(data)
        return str(result.inserted_id)

    def insert_many(self, data: list):
        result = self.collection.insert_many(data)
        return [str(_id) for _id in result.inserted_ids]

    def find(self, query: dict = {}, projection: dict = None):
        return list(self.collection.find(query, projection))

    def find_one(self, query: dict):
        return self.collection.find_one(query)

    def update_one(self, query: dict, new_values: dict, upsert=False):
        result = self.collection.update_one(query, {"$set": new_values}, upsert=upsert)
        return result.modified_count

    def update_many(self, query: dict, new_values: dict):
        result = self.collection.update_many(query, {"$set": new_values})
        return result.modified_count

    def delete_one(self, query: dict):
        result = self.collection.delete_one(query)
        return result.deleted_count

    def delete_many(self, query: dict):
        result = self.collection.delete_many(query)
        return result.deleted_count
