from db.mongo import MongoAPI
from get_data import get_updated_data
from datetime import datetime,timedelta,timezone
from initialization import initialization

if __name__ == '__main__':
    Yemeksepeti, trendyol_clients, DodoIS  = initialization()

    start_date_range = 0
    end_date_range = 1
    if start_date_range > 2:
        Yemeksepeti = None

    for i in range(start_date_range,end_date_range):

        gmt_timezone = timezone(timedelta(hours=3))
        now = datetime.now(gmt_timezone) - timedelta(days=i)

        collection_name = str(now.month) + str(now.year)
        file_name = str(now.day) + collection_name

        mongo = MongoAPI(collection_name=collection_name)

        old_data = mongo.find_json_by_name(file_name)

        new_data = get_updated_data(now,
                                    gmt_timezone,
                                    Yemeksepeti,
                                    trendyol_clients,
                                    DodoIS,
                                    old_data)
        data = {
            "name" : file_name,
             "data" : new_data
            }
        if old_data:
            mongo.update_json_by_name(file_name, data)
        else:
            mongo.create_json(data)
        print(i)
