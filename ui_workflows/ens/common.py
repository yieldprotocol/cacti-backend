import re
import json
import web3
import os
from logging import basicConfig, INFO
import sha3 # 'pip install pysha3'
from idna import encode, IDNAError

import context
from utils import load_contract_abi

from ..base import WorkflowValidationError

# ENS contract addresses - https://legacy.ens.domains/name/ens.eth/subdomains
ENS_REGISTRY_ADDRESS = web3.Web3.to_checksum_address("0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e")
ENS_PUBLIC_RESOLVER_ADDRESS = web3.Web3.to_checksum_address("0x4976fb03c32e5b8cfe2b6ccb31c09ba78ebaba41")
ENS_REVERSE_REGISTRAR_ADDRESS = web3.Web3.to_checksum_address("0xa58E81fe9b61B5c3fE2AFD33CF304c454AbFc7Cb")

curr_script_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(curr_script_dir, "./abis/ens_registry.abi.json"), 'r') as f:
    ens_registry_abi_dict = json.load(f)

def keccak_256(data):
    k = sha3.keccak_256()
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

def instantiate_ens_registry_contract(web3_provider: web3.Web3):
    return web3_provider.eth.contract(address=web3.Web3.to_checksum_address(ENS_REGISTRY_ADDRESS), abi=ens_registry_abi_dict)

def is_domain_registered(web3_provider: web3.Web3, domain) -> bool:    
    node = get_node_namehash(domain)
    contract = instantiate_ens_registry_contract(web3_provider)
    address = contract.functions.owner(node).call()
    return web3.constants.ADDRESS_ZERO != address

def is_domain_owner(web3_provider: web3.Web3, domain: str, user_address: str) -> bool:
    node = get_node_namehash(domain)
    contract = instantiate_ens_registry_contract(web3_provider)
    owner_address: str = contract.functions.owner(node).call()
    return owner_address.lower() == user_address.lower()


def ens_update_common_pre_workflow_validation(web3_provider, domain, wallet_address):
    # Check if domain is registered
    if (not is_domain_registered(web3_provider, domain)):
        raise WorkflowValidationError(f"ENS name {domain} is not registered")

    # Check if wallet is owner of the domain
    if(not is_domain_owner(web3_provider, domain, wallet_address)):
        raise WorkflowValidationError(f"ENS name {domain} is not owned by the user")

def get_ens_resolver_contract():
    web3_provider = context.get_web3_provider()
    return web3_provider.eth.contract(address=ENS_PUBLIC_RESOLVER_ADDRESS, abi=load_contract_abi(__file__, "./abis/ens_resolver.abi.json"))

def get_ens_reverse_registrar_contract():
    web3_provider = context.get_web3_provider()
    return web3_provider.eth.contract(address=ENS_REVERSE_REGISTRAR_ADDRESS, abi=load_contract_abi(__file__, "./abis/ens_reverse_registrar.abi.json"))

