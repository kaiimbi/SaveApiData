import logging
from initialization import initialization
from json import loads
from datetime import datetime, timedelta, timezone

with open("data/regions.json", encoding="utf-8") as f:
    data = loads(f.read())


def update_data(day_range = 0):
    Yemeksepeti, trendyol_clients, DodoIS = initialization()
    gmt_plus_3 = timezone(timedelta(hours=3))
    now = datetime.now(gmt_plus_3) - timedelta(days=day_range)


    result_data = {}

    for division in data['divisions']:
        trendyol_supplier_id = division['trendyol_supplier_id']
        region_name = division['region_name']
        franchise_name = division['franchise']


        for unit in division['units']:

            unit_id = unit['dodois_unit_id']
            trendyol_unit_id = unit['trendyol_id']
            yemeksepeti_unit_id = unit['yemeksepeti_pos_id']

            result = {
                "name": unit['dodois_name'],
                "region_name": region_name,
                "franchise": franchise_name,
                "trendyol_id": trendyol_unit_id,
                "yemeksepeti_id": yemeksepeti_unit_id,
            }


            #DodoIS
            dodois_data = get_dodois_data(DodoIS, unit_id, now)
            result_data["dodois"] = dodois_data

            #Trendyol
            trendyol_data = get_trendyol_data(trendyol_clients,trendyol_supplier_id, trendyol_unit_id, now)
            result['trendyol'] = trendyol_data

            # Yemeksepeti
            yemeksepeti_data = get_yemeksepeti_data(Yemeksepeti, yemeksepeti_unit_id, now, gmt_plus_3)
            result['yemeksepeti'] = yemeksepeti_data

            result_data[unit_id] = result

            logging.info(f"{unit['dodois_name']} statistics added in result")

    return result_data



def get_yemeksepeti_data(Yemeksepeti, yemeksepeti_unit_id, now_time, gmt_timezone):
    if yemeksepeti_unit_id:
        yemeksepeti_result = {}

        orders = Yemeksepeti.get("/orders/ids", params={"status": "accepted", "vendorId": yemeksepeti_unit_id})
        total_order = orders['count']

        if total_order:

            yemeksepeti_order_data = {
                "cancelled_orders": [],
                "total_price": 0,
                "order_price_coordinate": []
            }

            order_list = orders['orders']
            for order in order_list:
                order_detail = Yemeksepeti.get(f"/orders/{order}")['order']

                created_at_str = order_detail['createdAt']
                created_at_utc = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                created_at_local = created_at_utc.astimezone(gmt_timezone)

                if created_at_local.date() != now_time.date():
                    continue

                if order_detail['status'] == "cancelled":
                    yemeksepeti_order_data['cancelled_orders'].append(
                        {"orderId": order_detail['code'], 'price': order_detail['price']['totalNet']})
                    continue
                price = float(order_detail['price']['totalNet'])
                yemeksepeti_order_data['total_price'] += price

                yemeksepeti_order_data['order_price_coordinate'].append(
                    [price, order_detail['delivery']['address']['latitude'],
                     order_detail['delivery']['address']['longitude']])
            yemeksepeti_result['orders'] = yemeksepeti_order_data

        if yemeksepeti_result:
            return yemeksepeti_result


def get_trendyol_data(trendyol_clients, trendyol_supplier_id, trendyol_unit_id, now):
    start_date_epochmille = int((now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() + 3600 * 3) * 1000)
    end_date_epochmille = int(
        ((now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).timestamp() + 3600 * 3) * 1000)

    if trendyol_unit_id:
        trendyol_result = {}

        Trendyol = trendyol_clients[trendyol_supplier_id]
        response = Trendyol.get_all_paginated(
            url=f"https://api.tgoapis.com/integrator/review/meal/suppliers/{trendyol_supplier_id}/stores/{trendyol_unit_id}/reviews/filter",
            params={
                "startDate": start_date_epochmille,
                "endDate": end_date_epochmille
            }
        )
        if response:
            trendyol_result['reviews'] = response

        response = Trendyol.get_all_paginated(
            url=f"https://api.tgoapis.com/integrator/claim/meal/suppliers/{trendyol_supplier_id}/claims",
            params={
                "storeId": trendyol_unit_id,
                "createdStartDate": start_date_epochmille,
                "createdEndDate": end_date_epochmille
            }
        )
        if response:
            trendyol_result['claims'] = response

        response = Trendyol.get_all_paginated(

            url=f"https://api.tgoapis.com/integrator/order/meal/suppliers/{trendyol_supplier_id}/packages",
            params={
                "packageModificationStartDate": start_date_epochmille - 3600 * 1000 * 4,
                "packageModificationEndDate": end_date_epochmille + 3600 * 1000 * 4,
                "storeId": trendyol_unit_id,

            }
        )

        trendyol_order_data = {"total_order": 0,
                               "store_pickup_order": 0,
                               "total_price": 0,
                               "late_orders": [],
                               "cancelled_orders": [],
                               "order_price_coordinate": []
                               }

        for package in response:
            if not start_date_epochmille <= package['packageCreationDate'] or not package[
                                                                                      'packageCreationDate'] < end_date_epochmille:
                continue
            trendyol_order_data['total_order'] += 1
            trendyol_order_data['total_price'] += package['totalPrice']
            if package['storePickupSelected']:
                trendyol_order_data['store_pickup_order'] += 1

            if package['packageStatus'] == "Cancelled" or package['packageStatus'] == "UnSupplied" and not package[
                'cancelInfo']:
                trendyol_order_data['cancelled_orders'].append(
                    {"reason": package['cancelInfo'], "orderId": package['orderId'],
                     "totalPrice": package['totalPrice']})

            if package['packageStatus'] == "Delivered" and package['packageCreationDate'] < package[
                'packageModificationDate'] - 3600 * 1000:
                trendyol_order_data['late_orders'].append(
                    {"orderId": package['orderId'],
                     "late_time": int(
                         (package['packageModificationDate'] - package['packageCreationDate']) / 60 / 1000)})
            trendyol_order_data['order_price_coordinate'].append(
                [package['totalPrice'], package['address']['latitude'], package['address']['longitude']])

        if trendyol_order_data['total_order']:
            trendyol_result['orders'] = trendyol_order_data

        if trendyol_result:
            return trendyol_result

def get_dodois_data(DodoIS, unit_id ,now):

    start_date = now.strftime("%Y-%m-%d")
    end_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    dodois_result = {}
    endpoints = [
        ("finances/sales/units", "salesStatistics", "result", "from", "to"),
        ("production/orders-handover-statistics", "ordersHandoverStatistics", "ordersHandoverStatistics", "from", "to"),
        ("delivery/statistics", "unitsStatistics", "unitsStatistics", "from", "to"),
        ("orders/clients-statistics", "clientStatistics", "clientStatistics", "fromDate", "toDate"),
    ]

    for endpoint, key, response_key, from_param_name, to_param_name in endpoints:
        common_params = {from_param_name: start_date, to_param_name: end_date, "units": unit_id}

        response = DodoIS._request(endpoint=endpoint, params=common_params)
        if response.get(response_key):
            dodois_result[key] = response[response_key]

    params = {"from": (now - timedelta(days=7)).strftime("%Y-%m-%d"),
              "to": (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"), "units": unit_id}

    response = DodoIS._request(endpoint="finances/sales/units", params=params)
    if response.get("result"):
        dodois_result["salesStatisticsWeekAgo"] = response["result"]

    if dodois_result:
        return dodois_result