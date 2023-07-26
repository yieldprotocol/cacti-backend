
DUMMY_WALLET_ADDRESS = "0x4eD15A17A9CDF3hc7D6E829428267CaD67d95F8F"
DUMMY_ENS_DOMAIN = "cacti1729.eth"
DUMMY_NETWORK = "ethereum-mainnet"
def get_dummy_user_info(user_info: dict) -> dict:
    user_info["Wallet Address"] = DUMMY_WALLET_ADDRESS
    user_info["ENS Domain"] = DUMMY_ENS_DOMAIN
    user_info["Network"] = DUMMY_NETWORK
    return user_info