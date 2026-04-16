"""Ganache / Web3 contract helpers (shared by app and API blueprint)."""

import json
import os
import time

from web3 import Web3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
# Same folder as ChainOfCustody.sol — deploy.py writes ABI + address here
CONTRACTS_DIR = os.path.join(ROOT_DIR, "contracts")
GANACHE_URL = os.environ.get("GANACHE_URL", "http://127.0.0.1:7545")
ABI_FILE = os.path.join(CONTRACTS_DIR, "contract_abi.json")
ADDRESS_FILE = os.path.join(CONTRACTS_DIR, "contract_address.txt")
# Optional: set after Remix deploy without editing files (same value as contract_address.txt)
_ENV_CONTRACT = os.environ.get("CHAIN_CUSTODY_CONTRACT_ADDRESS", "").strip()

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

ACTION_NAMES = {
    0: "Collected",
    1: "Transferred",
    2: "Analyzed",
    3: "Verified",
    4: "Archived",
}
ACTION_CODES = {v: k for k, v in ACTION_NAMES.items()}


def _read_contract_address() -> str | None:
    """Address from env (Remix / CI) or first non-comment line in contract_address.txt."""
    if _ENV_CONTRACT:
        return _ENV_CONTRACT
    if not os.path.isfile(ADDRESS_FILE):
        return None
    with open(ADDRESS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            return line
    return None


def load_contract():
    if not os.path.isfile(ABI_FILE):
        return None
    address = _read_contract_address()
    if not address:
        return None
    with open(ABI_FILE, encoding="utf-8") as f:
        abi = json.load(f)
    try:
        return w3.eth.contract(
            address=Web3.to_checksum_address(address), abi=abi
        )
    except ValueError:
        return None


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
