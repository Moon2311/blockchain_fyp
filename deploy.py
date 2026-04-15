"""
deploy.py - Compiles and deploys ChainOfCustody smart contract to Ganache.
Run this ONCE before starting the Flask app.

Usage:
    python deploy.py

Requirements:
    pip install web3 py-solc-x
"""

import json
import os
from solcx import compile_source, install_solc, get_installed_solc_versions

from web3 import Web3

# ── Configuration ──────────────────────────────────────────────────────────────
GANACHE_URL = "http://127.0.0.1:7545"   # default Ganache GUI port
CONTRACT_FILE = os.path.join(os.path.dirname(__file__), "contracts", "ChainOfCustody.sol")
ABI_OUTPUT    = os.path.join(os.path.dirname(__file__), "backend", "contract_abi.json")
ADDRESS_FILE  = os.path.join(os.path.dirname(__file__), "backend", "contract_address.txt")
# ───────────────────────────────────────────────────────────────────────────────


def install_compiler():
    # 0.8.7 is compatible with Ganache 2.7.x (older EVM / no PUSH0 opcode)
    target = "0.8.7"
    installed = [str(v) for v in get_installed_solc_versions()]
    if target not in installed:
        print(f"[*] Installing solc {target} …")
        install_solc(target)
    else:
        print(f"[*] solc {target} already installed.")
    return target


def compile_contract(solc_version):
    print("[*] Compiling ChainOfCustody.sol …")
    with open(CONTRACT_FILE, "r") as f:
        source = f.read()

    compiled = compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version=solc_version,
        evm_version="berlin"   # Ganache 2.7.x supports Berlin EVM
    )
    contract_id = "<stdin>:ChainOfCustody"
    abi = compiled[contract_id]["abi"]
    bytecode = compiled[contract_id]["bin"]
    print("[✓] Compilation successful.")
    return abi, bytecode


def deploy(abi, bytecode):
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not w3.is_connected():
        raise ConnectionError(
            f"Cannot connect to Ganache at {GANACHE_URL}\n"
            "Make sure Ganache is running (GUI or CLI: ganache --port 7545)"
        )

    print(f"[*] Connected to Ganache. Accounts: {len(w3.eth.accounts)}")
    deployer = w3.eth.accounts[0]
    w3.eth.default_account = deployer

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    print("[*] Deploying contract …")
    tx_hash = Contract.constructor().transact({"from": deployer, "gas": 3_000_000})
    receipt  = w3.eth.wait_for_transaction_receipt(tx_hash)
    address  = receipt.contractAddress
    print(f"[✓] Contract deployed at: {address}")
    return address, w3


def save_artifacts(abi, address):
    os.makedirs(os.path.dirname(ABI_OUTPUT), exist_ok=True)
    with open(ABI_OUTPUT, "w") as f:
        json.dump(abi, f, indent=2)
    with open(ADDRESS_FILE, "w") as f:
        f.write(address)
    print(f"[✓] ABI saved  → {ABI_OUTPUT}")
    print(f"[✓] Address saved → {ADDRESS_FILE}")


if __name__ == "__main__":
    solc_ver = install_compiler()
    abi, bytecode = compile_contract(solc_ver)
    address, w3 = deploy(abi, bytecode)
    save_artifacts(abi, address)

    # Quick smoke test
    contract = w3.eth.contract(address=address, abi=abi)
    count = contract.functions.getEvidenceCount().call()
    print(f"[✓] Smoke test – evidenceCounter = {count}  (should be 0)")
    print("\n✅  Deployment complete. You can now run:  python backend/app.py")
