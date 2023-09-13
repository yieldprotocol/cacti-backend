import os
import env
import getpass

### Server ###

SERVER_HOST=os.environ['SERVER_HOST']
SERVER_ORIGINS=os.environ['SERVER_ORIGINS']
SERVER_SECRET_KEY=os.environ['SERVER_SECRET_KEY']

# Let FE/Wallet handle gas estimation as it would be more up-to-date, default is true
USE_CLIENT_TO_ESTIMATE_GAS = os.environ.get('USE_FRONTEND_TO_ESTIMATE_GAS', 'true').lower() == 'true'

### Storage ###

WEAVIATE_URL = os.environ['WEAVIATE_URL']
WEAVIATE_API_KEY = os.environ['WEAVIATE_API_KEY']

CHATDB_URL = os.environ['CHATDB_URL']

# Scrape DB is optional
SCRAPEDB_URL = os.environ.get('SCRAPEDB_URL', None)

### Tenderly ###

TENDERLY_FORK_BASE_URL = "https://rpc.tenderly.co/fork"

TENDERLY_API_KEY = os.getenv('TENDERLY_API_KEY', None)
TENDERLY_DEFAULT_MAINNET_FORK_ID = os.getenv('TENDERLY_DEFAULT_MAINNET_FORK_ID', None)
TENDERLY_FORK_URL = f"{TENDERLY_FORK_BASE_URL}/{TENDERLY_DEFAULT_MAINNET_FORK_ID}"

TENDERLY_PROJECT_API_BASE_URL = os.getenv('TENDERLY_PROJECT_API_BASE_URL', None)
TENDERLY_DASHBOARD_PROJECT_BASE_URL = os.getenv('TENDERLY_DASHBOARD_PROJECT_BASE_URL', None)

TEST_TENDERLY_FORK_ID = os.getenv('TEST_TENDERLY_FORK_ID', None)

### External Services ###

HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY', None)
HUGGINGFACE_INFERENCE_ENDPOINT = "https://xczbh8zf5amwxdlc.us-east-1.aws.endpoints.huggingface.cloud" # may vary

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

OPENSEA_API_KEY = os.getenv('OPENSEA_API_KEY', None)
CENTER_API_KEY = os.getenv('CENTER_API_KEY', None)

ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', None)
ALCHEMY_API_KEY =  os.getenv('ALCHEMY_API_KEY', None)

### Widget Vector Index/Store ###

# max num tokens for widgets info in model's input
WIDGET_INFO_TOKEN_LIMIT = 4000

# Widget Index
WIDGET_INDEX_NAME = "WidgetV21"

def get_widget_index_name():
    if env.is_local():
        return f"WidgetV{getpass.getuser()}"
    else:
        return WIDGET_INDEX_NAME

### Network/Chain ###

ETH_MAINNET_CHAIN_ID = 1
ETH_MAINNET_RPC_URL = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

CHAIN_ID_TO_NETWORK_NAME = {ETH_MAINNET_CHAIN_ID: "ethereum-mainnet"}
