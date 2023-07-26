import os
import env
import getpass

HUGGINGFACE_API_KEY = "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"
HUGGINGFACE_INFERENCE_ENDPOINT = "https://xczbh8zf5amwxdlc.us-east-1.aws.endpoints.huggingface.cloud" # may vary
OPENAI_API_KEY = "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"
CENTER_API_KEY = os.getenv('CENTER_API_KEY', 'key8f1af05afe473107c3ea2556')
ETHERSCAN_API_KEY = 'ZCUTVCPHAJ5YRNB6SZTJN9ZV24FBEX86GJ'
OPENSEA_API_KEY = os.getenv('OPENSEA_API_KEY', '')
TENDERLY_API_KEY = os.getenv('TENDERLY_API_KEY', None)

TENDERLY_FORK_BASE_URL = "https://rpc.tenderly.co/fork"
DEFAULT_MAINNET_FORK_ID = "08f78838-4799-47a8-88fb-1f169fa99f57"
TENDERLY_FORK_URL = f"{TENDERLY_FORK_BASE_URL}/{DEFAULT_MAINNET_FORK_ID}"

TEST_TENDERLY_FORK_ID = os.getenv('TEST_TENDERLY_FORK_ID', "")

ETH_MAINNET_CHAIN_ID = 1

# max num tokens for widgets info in model's input
WIDGET_INFO_TOKEN_LIMIT = 4000

# Widget Index
WIDGET_INDEX_NAME = "WidgetV15"

def get_widget_index_name():
    if env.is_local():
        return f"WidgetV{getpass.getuser()}"
    else:
        return WIDGET_INDEX_NAME