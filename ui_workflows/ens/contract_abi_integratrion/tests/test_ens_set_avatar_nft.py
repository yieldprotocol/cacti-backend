import os
import uuid
from ..ens_set_avatar_nft import ENSSetAvatarNFTWorkflow
from ....base import process_result_and_simulate_tx

# Invoke this with python -m pytest -s -k "test_contract_ens_set_avatar_nft"
def test_contract_ens_set_avatar_nft(setup_fork):
    domain = "vitalik.eth"
    wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    mock_chat_message_id = str(uuid.uuid4())
    workflow_params = {
        "domain": domain,
        "nftContractAddress": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
        "nftId": "2836",
        "collectionName": "Bored Ape Yacht Club"
    }

    result = ENSSetAvatarNFTWorkflow(wallet_chain_id, wallet_address, mock_chat_message_id, workflow_params).run()

    process_result_and_simulate_tx(wallet_address, result)