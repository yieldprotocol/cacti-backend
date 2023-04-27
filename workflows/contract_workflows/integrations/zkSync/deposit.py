from base import BaseContractWorkflow
from utils import load_json

ETH = 'ETH'
DEPOSIT = 'Deposit'
BRIDGE = 'Bridge'
PROJECT = 'ZkSync Era'


def get_allowance(account, token_addr):
    """Get allowance for token"""
    token_contract = erc20_factory(token_addr)
    return token_contract.allowance(account)


def get_approval_needed(allowance, amount):
    """Check if approval is needed"""
    return allowance < amount


def handle_approval(token_addr, amount):
    """Handle approval for token"""
    token_contract = erc20_factory(token_addr)
    return token_contract.approve(amount)

# TODO should be a common util


def get_token(token_addr):
    """Get token data from address"""
    if token_addr == zero_addr:
        return eth_data
    else:
        return token_factory(token_addr).symbol()


class ZkSyncDepositWorkflow(BaseContractWorkflow):
    """ZkSync bridge/deposit contract workflow"""

    def __init__(self, wallet_chain_id: int, wallet_address: str, token_addr: str, operation: str, amount: float):
        token = token.upper()
        parsed_user_request = f"{operation.capitalize()} {amount} {token} to {PROJECT}"
        super().__init__(wallet_chain_id, wallet_address, parsed_user_request)
        assert operation in (DEPOSIT, BRIDGE), operation
        self.token_addr = token_addr
        self.operation = operation
        self.amount = amount

    # requestL2Transaction(
    #   address _contractL2, # wallet address of the user on l2
    #   uint256 _l2Value,
    #   bytes _calldata,
    #   uint256 _l2GasLimit,
    #   uint256 _l2GasPerPubdataByteLimit,
    #   bytes[] _factoryDeps,
    #   address _refundRecipient)
    def _deposit(self):
        """Deposit funds to zkSync"""
        print("Depositing funds to zkSync")

        contract_addr = '0x32400084C286CF3E17e7B677ea9583e60a000324'
        contract = self.w3.eth.contract(
            address=contract_addr, abi=load_json('abi.json'))

        token = get_token(self.token_addr)
        parsed_amount = self.w3.toWei(self.amount, token.decimals)

        if token != ETH:
            handle_approval((self.token_addr, self.amount))

        # invoke contract func
        call_data = 'dont know how to get this'
        l2_gas_limit = 'dont know how to get this'
        l2_gas_per_pubdata_byte_limit = 'dont know how to get this'
        factory_deps = 'dont know how to get this'
        refund_recipient = wallet_address

        tx = contract.functions.requestL2Transaction(
            wallet_address, parsed_amount, call_data, l2_gas_limit, l2_gas_per_pubdata_byte_limit, factory_deps, refund_recipient).transact().call()

        return tx

    def _run(self):
        """Run the contract func """
        return self._deposit()


# Invoke this with python3 -m contract_workflows.zkSync.deposit
if __name__ == "__main__":
    wallet_chain_id = 1  # Tenderly Mainnet Fork
    wallet_address = "0x663ed57D834Cd1c2aB9D0B97305a64614a2CC3fd"
    token = "ETH"
    operation = "Bridge"
    amount = 0.1

    wf = ZkSyncDepositWorkflow(wallet_chain_id, wallet_address,
                               token, operation, amount)

    print(wf.run())
