from dotenv import load_dotenv
load_dotenv("data/.env")

from DodoIS.DodoISData import *
from ApiClients.yemeksepeti_client import *
from ApiClients.trendyol_client import *

def initialization():

    yemeksepeti_client = POSMiddlewareClient(
        base_url=f"https://integration-middleware-tr.me.restaurant-partners.com/v2/chains/{os.getenv('YEMEKSEPETI_CHAINID')}/",
        username=os.getenv("YEMEKSEPETI_USERNAME"),
        password=os.getenv("YEMEKSEPETI_PASSWORD")
    )
    logging.info(f"Initializing Yemeksepeti Client is Completed")

    trendyol_clients = trendyol_initialization()

    logging.info(f"Initialized Trendyol clients for regions: {os.getenv('REGIONS')}")

    auth = DodoISAuth(env_path="data/.env")
    dodois_client = DodoISClient(auth=auth)

    logging.info(f"Initializing DodoIS Client is Completed")

    return yemeksepeti_client, trendyol_clients, dodois_client



def trendyol_initialization():
    trendyol_clients = {}
    for region in os.getenv("REGIONS").split(","):
        trendyol_client = TrendyolClient(
            api_key=os.getenv(f"TRENDYOL_API_KEY_{region}"),
            api_secret=os.getenv(f"TRENDYOL_API_SECRET_{region}"),
            agent_name=os.getenv(f"TRENDYOL_AGENT_MAIL_{region}"),
            agent_mail=os.getenv(f"TRENDYOL_AGENT_NAME_{region}")
        )

        supplier_id = os.getenv(f"TRENDYOL_SUPPLIER_ID_{region}")
        if not supplier_id:
            raise EnvironmentError(f"Missing TRENDYOL_SUPPLIER_ID for region {region}")
        trendyol_clients[supplier_id] = trendyol_client

    return trendyol_clients