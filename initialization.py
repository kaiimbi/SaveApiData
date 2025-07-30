import os
import logging
from dotenv import load_dotenv
load_dotenv("data/.env")

from DodoIS.DodoISData import *
from ApiClients.yemeksepeti_client import *
from ApiClients.trendyol_client import *

def initialization():
    Yemeksepeti_Client = POSMiddlewareClient(
        base_url=f"https://integration-middleware-tr.me.restaurant-partners.com/v2/chains/{os.getenv("YEMEKSEPETI_CHAINID")}/",
        username=os.getenv("YEMEKSEPETI_USERNAME"),
        password=os.getenv("YEMEKSEPETI_PASSWORD")
    )
    logging.info(f"Initializing Yemeksepeti Client is Completed")

    trendyol_clients = {}

    for region in os.getenv("REGIONS").split(","):
        Trendyol_Client = TrendyolClient(
        api_key=os.getenv(f"TRENDYOL_API_KEY_{region}"),
        api_secret=os.getenv(f"TRENDYOL_API_SECRET_{region}"),
        agent_name=os.getenv(f"TRENDYOL_AGENT_MAIL_{region}"),
        agent_mail=os.getenv(f"TRENDYOL_AGENT_NAME_{region}")
        )
        trendyol_clients[os.getenv(f"TRENDYOL_SUPPLIER_ID_{region}")] = Trendyol_Client

    logging.info(f"Initializing Trendyol Client is Completed")

    auth = DodoISAuth(env_path="data/.env")

    DodoIS_Client = DodoISClient(auth=auth)

    logging.info(f"Initializing DodoIS Client is Completed")


    return Yemeksepeti_Client, trendyol_clients, DodoIS_Client
