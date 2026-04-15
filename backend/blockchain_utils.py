"""Ganache / Web3 contract helpers (shared by app and API blueprint)."""

import json
import os
import time

from web3 import Web3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GANACHE_URL = "http://127.0.0.1:7545"
ABI_FILE = os.path.join(BASE_DIR, "contract_abi.json")
ADDRESS_FILE = os.path.join(BASE_DIR, "contract_address.txt")

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

ACTION_NAMES = {
    0: "Collected",
    1: "Transferred",
    2: "Analyzed",
    3: "Verified",
    4: "Archived",
}
ACTION_CODES = {v: k for k, v in ACTION_NAMES.items()}


def load_contract():
    if not os.path.exists(ABI_FILE) or not os.path.exists(ADDRESS_FILE):
        return None
    with open(ABI_FILE) as f:
        abi = json.load(f)
    with open(ADDRESS_FILE) as f:
        address = f.read().strip()
    return w3.eth.contract(address=address, abi=abi)


contract = load_contract()


def get_ganache_account():
    return w3.eth.accounts[0] if w3.eth.accounts else None


def format_event(ev):
    action_id = ev[3] if isinstance(ev[3], int) else int(ev[3])
    return {
        "evidenceId": ev[0],
        "fileHash": ev[1],
        "fileName": ev[2],
        "action": ACTION_NAMES.get(action_id, "Unknown"),
        "actor": ev[4],
        "notes": ev[5],
        "timestamp": ev[6],
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ev[6])),
    }


def blockchain_status():
    connected = w3.is_connected()
    deployed = contract is not None
    return {"connected": connected, "deployed": deployed}
