import os
import env
import getpass

### Server ###
SERVER_HOST=os.environ['SERVER_HOST']
SERVER_ORIGINS=os.environ['SERVER_ORIGINS']
SERVER_SECRET_KEY=os.environ['SERVER_SECRET_KEY']

### Storage ###
WEAVIATE_URL = os.environ['WEAVIATE_URL']
CHATDB_URL = os.environ['CHATDB_URL']
# Scrape DB is optional
SCRAPEDB_URL = os.environ.get('SCRAPEDB_URL', None)


HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY', None)
HUGGINGFACE_INFERENCE_ENDPOINT = "https://xczbh8zf5amwxdlc.us-east-1.aws.endpoints.huggingface.cloud" # may vary

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
CENTER_API_KEY = os.getenv('CENTER_API_KEY', None)
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', None)
OPENSEA_API_KEY = os.getenv('OPENSEA_API_KEY', None)
TENDERLY_API_KEY = os.getenv('TENDERLY_API_KEY', None)

TENDERLY_FORK_BASE_URL = "https://rpc.tenderly.co/fork"
DEFAULT_MAINNET_FORK_ID = os.getenv('DEFAULT_MAINNET_FORK_ID', None)
TENDERLY_FORK_URL = f"{TENDERLY_FORK_BASE_URL}/{DEFAULT_MAINNET_FORK_ID}"

TEST_TENDERLY_FORK_ID = os.getenv('TEST_TENDERLY_FORK_ID', None)

ETH_MAINNET_CHAIN_ID = 1

CHAIN_ID_TO_NETWORK_NAME = {ETH_MAINNET_CHAIN_ID: "ethereum-mainnet"}

# max num tokens for widgets info in model's input
WIDGET_INFO_TOKEN_LIMIT = 4000

# Widget Index
WIDGET_INDEX_NAME = "WidgetV14"

def get_widget_index_name():
    if env.is_local():
        return f"WidgetV{getpass.getuser()}"
    else:
        return WIDGET_INDEX_NAME
