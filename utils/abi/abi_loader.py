import os
import json
from typing import Dict
from ..common import w3

ERC20_ABI = None

def load_erc20_abi():
    global ERC20_ABI
    with open(os.path.join(os.path.dirname(__file__), "./erc20.abi.json")) as f:
        ERC20_ABI = json.load(f)

def load_contract_abi(module_file_path: str, abi_relative_path: str) -> Dict:
    abi_abs_path = os.path.join(os.path.dirname(os.path.abspath(module_file_path)), abi_relative_path)
    with open(abi_abs_path, 'r') as f:
        return json.load(f)

load_erc20_abi()