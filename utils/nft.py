import env
import context
from typing import List, Dict
from web3.exceptions import ContractLogicError
from utils import web3_provider, ETH_MAINNET_CHAIN_ID

SNEAKY_CHEETAH_CLUB_CONTRACT_ADDRESS = "0x4C3A2F61a4449667b7085734f24095c5f932b875"
PUDGY_PENGUINS_CONTRACT_ADDRESS = "0xbd3531da5cf5857e7cfaa92426877b022e612cf8"

# NOTE: Only choose collections that have a "tokenOfOwnerByIndex" standard function to easily enumerate and fetch all NFTs owned by an address
DEV_NFT_COLLECTIONS_SUPPORTED = [
    SNEAKY_CHEETAH_CLUB_CONTRACT_ADDRESS,
    PUDGY_PENGUINS_CONTRACT_ADDRESS
]

ERC721_ABI = [
    {
        "inputs": [
            { "internalType": "address", "name": "owner", "type": "address" },
            { "internalType": "uint256", "name": "index", "type": "uint256" }
        ],
        "name": "tokenOfOwnerByIndex",
        "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }],
        "stateMutability": "view",
        "type": "function"
    },
]

def dev_fetch_nfts_from_contract_by_owner(address_or_domain: str, chain_id: int) -> List[Dict]:
    if env.is_prod():
        raise Exception('This function is only for dev/demo')
    
    if chain_id != ETH_MAINNET_CHAIN_ID:
        raise Exception('This function is only for Mainnet Chain ID')

    web3 = web3_provider.get_web3_from_chain_id(chain_id)

    results = []

    normalized_address = None
    if ".eth" in address_or_domain:
        normalized_address = web3.ens.address(address_or_domain)
    else:
        normalized_address = address_or_domain

    for contract_address in DEV_NFT_COLLECTIONS_SUPPORTED:
        try:
            contract = web3.eth.contract(address=web3.to_checksum_address(contract_address), abi=ERC721_ABI)
            # Arbitary limit of 10 NFTs for testing
            for i in range(0, 10):
                token_id = contract.functions.tokenOfOwnerByIndex(normalized_address, i).call()
                results.append(dict(contract_address=contract_address, token_id=token_id))
        except ContractLogicError as e:
            # Exception is thrown when no further NFTs are found as per index
            continue

    return results

    
    