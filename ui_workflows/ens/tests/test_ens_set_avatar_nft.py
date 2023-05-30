import os
import uuid
from ..ens_set_avatar_nft import ENSSetAvatarNFTWorkflow
from ...base import process_result_and_simulate_tx

# Invoke this with python -m pytest -s -k "test_ens_set_avatar_nft"
def test_ens_set_avatar_nft(setup_fork):
    domain = "owocki.gitcoin.eth"
    wallet_address = "0xDDF369C3bf18b1B12EA295d597B943b955eF4671"
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    mock_chat_message_id = str(uuid.uuid4())
    workflow_params = {
        "domain": domain,
        "nftContractAddress": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
        "nftId": "2836"
    }

    result = ENSSetAvatarNFTWorkflow(wallet_chain_id, wallet_address, mock_chat_message_id, workflow_params).run()

    process_result_and_simulate_tx(wallet_address, result)