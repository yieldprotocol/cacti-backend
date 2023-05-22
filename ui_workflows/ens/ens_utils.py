import re
import json
import web3
import os
from logging import basicConfig, INFO
#import sha3 # 'pip install pysha3'
import hashlib
from idna import encode, IDNAError
from utils import w3


# ENS contract addresses - https://legacy.ens.domains/name/ens.eth/subdomains
ENS_REGISTRY_ADDRESS = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e"
ENS_PUBLIC_RESOLVER_ADDRESS = "0x4976fb03c32e5b8cfe2b6ccb31c09ba78ebaba41"

curr_script_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(curr_script_dir, "./abis/ens_registry.abi"), 'r') as f:
    ens_registry_abi_dict = json.load(f)

def keccak_256(data):
    k = hashlib.sha3_256()
    k.update(data)
    return k.hexdigest()

def to_unicode(name):
    try:
        return encode(name, uts46=True, transitional=False, std3_rules=True).decode('utf-8')
    except IDNAError as e:
        return name

def get_node_namehash(domain):
    # namehash
    node = bytes.fromhex("00" * 32)
    name = to_unicode(domain)
    if name:
        labels = name.split(".")

        for label in reversed(labels):
            label_sha = bytes.fromhex(keccak_256(label.encode()))
            node_sha = keccak_256(node + label_sha)
            node = bytes.fromhex(node_sha)

    return "0x" + node.hex()

def instantiate_ens_registry_contract():
    return w3.eth.contract(address=w3.to_checksum_address(ENS_REGISTRY_ADDRESS), abi=ens_registry_abi_dict)

def is_domain_registered(domain) -> bool:
    node = get_node_namehash(domain)
    contract = instantiate_ens_registry_contract()
    address = contract.functions.owner(node).call()
    return web3.constants.ADDRESS_ZERO != address

def is_domain_owner(domain: str, user_address: str) -> bool:
    node = get_node_namehash(domain)
    contract = instantiate_ens_registry_contract()
    owner_address: str = contract.functions.owner(node).call()
    return owner_address.lower() == user_address.lower()