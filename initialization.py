import os
from json import loads
from dotenv import load_dotenv
load_dotenv("data/.env")

from ApiClients.yemeksepeti_client import POSMiddlewareClient
from ApiClients.trendyol_client import TrendyolClient

with open("data/regions.json", "r") as f:
    data = loads(f.read())


Yemeksepeti_Client = POSMiddlewareClient(
    base_url=f"https://integration-middleware-tr.me.restaurant-partners.com/v2/chains/{os.getenv("YEMEKSEPETI_CHAINID")}/",
    username=os.getenv("YEMEKSEPETI_USERNAME"),
    password=os.getenv("YEMEKSEPETI_PASSWORD")
)

trendyol_clients = []

for region in os.getenv("REGIONS").split(","):
    Trendyol_Client = TrendyolClient(
    api_key=os.getenv(f"TRENDYOL_API_KEY_{region}"),
    api_secret=os.getenv(f"TRENDYOL_API_SECRET_{region}"),
    agent_name=os.getenv(f"TRENDYOL_AGENT_MAIL_{region}"),
    agent_mail=os.getenv(f"TRENDYOL_AGENT_NAME_{region}")
    )
    trendyol_clients.append(Trendyol_Client)
