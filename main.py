import logging

from db.mongo import MongoAPI
from get_data import get_updated_data
from datetime import datetime,timedelta,timezone
from initialization import initialization
import json

with open("data/regions.json") as f:
    regions_data = json.load(f)



if __name__ == '__main__':
    Yemeksepeti, trendyol_clients, DodoIS  = initialization()
    mongo = MongoAPI(collection_name="Daily_Stats")

    start_date_range = 0
    end_date_range = 365

    for i in range(start_date_range,end_date_range):
        if start_date_range > 2:
            Yemeksepeti = None

        gmt_timezone = timezone(timedelta(hours=3))
        now = datetime.now(gmt_timezone) - timedelta(days=i)

        file_date = now.strftime("%Y-%m-%d")

        old_data_by_unit = {}
        for region in regions_data['divisions']:
            for unit in region['units']:
                old_data_by_unit[unit['dodois_unit_id']] =  mongo.find_by_date_and_unit(file_date, unit['dodois_unit_id'])

        data = get_updated_data(now,
                                gmt_timezone,
                                Yemeksepeti,
                                trendyol_clients,
                                DodoIS,
                                old_data_by_unit)

        for unit in data.keys():
            if not mongo.create_json(data[unit]):
                mongo.update_by_date_and_unit(file_date, unit, data[unit])

