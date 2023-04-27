from abc import ABC
from web3 import Web3, HTTPProvider
from utils import TENDERLY_FORK_URL


# just returning the tenderly fork rpc url for now until we set up actual rpc's
def get_rpc_url(url):
    return TENDERLY_FORK_URL


def get_web3(provider: HTTPProvider):
    return Web3(provider)


def get_provider(url):
    return Web3(Web3.HTTPProvider(url))

# TODO - figure out how for Web3


def get_signer(w3: Web3, address):
    return 'blah'


class BaseContractWorkflow(ABC):
    """Common interface for contract workflow."""

    def __init__(self, wallet_chain_id: int, wallet_address: str, parsed_user_request: str):
        """Initialize the contract workflow."""
        self.wallet_chain_id = wallet_chain_id
        self.wallet_address = wallet_address
        self.parsed_user_request = parsed_user_request

        provider = get_provider(get_rpc_url(self.wallet_chain_id))
        self.w3 = get_web3(provider)
        # self.signer = get_signer(self, self.provider)

    def run(self):
        """Run the contract func """
        print(f"Running contract workflow: {self.parsed_user_request}")

        return self._run()
