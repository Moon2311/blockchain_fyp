# ChainOfCustody — Remix IDE + Ganache

This project stores evidence **SHA-256** hashes on Ethereum via `ChainOfCustody.sol`. You can deploy with **`python deploy.py`** (recommended) or with **Remix** as required for coursework.

## 1. Start Ganache

- **Ganache GUI**: create a workspace; default HTTP is `http://127.0.0.1:7545`.
- **ganache-cli**: `ganache --port 7545` (or set `GANACHE_URL` to match).

The Flask backend uses the same URL unless you override **`GANACHE_URL`** in the environment (must match Remix’s “External HTTP provider”).

## 2. Remix — compile

1. Open [Remix IDE](https://remix.ethereum.org).
2. Create a file `ChainOfCustody.sol` and paste the contents of this folder’s `ChainOfCustody.sol`.
3. **Solidity compiler**: pick a version compatible with the file pragma (e.g. **0.8.7**).
4. **Compile** `ChainOfCustody`.

## 3. Remix — connect to Ganache

1. **Deploy & Run** → **ENVIRONMENT** → **External: Http Provider**.
2. URL: `http://127.0.0.1:7545` (or your `GANACHE_URL`).
3. Remix will show Ganache accounts with ETH for gas.

## 4. Remix — deploy

1. **Contract** dropdown → `ChainOfCustody`.
2. **Deploy** (confirm the selected account).
3. Under **Deployed Contracts**, copy the **deployed contract address** (starts with `0x`).

## 5. Save artifacts for the Python backend

The backend loads:

| Artifact | Path (repo root–relative) |
|----------|---------------------------|
| Solidity | `contracts/ChainOfCustody.sol` |
| ABI | `contracts/contract_abi.json` |
| Address | `contracts/contract_address.txt` |
| Address template | `contracts/contract_address.example.txt` |

**ABI (from Remix)**

- After compile, open the **Compilation Details** / ABI JSON for `ChainOfCustody`.
- Save the **ABI array** as `contracts/contract_abi.json` (valid JSON array).

**Address**

- Create (or overwrite) `contracts/contract_address.txt` with **one line**: the contract address, e.g.  
  `0x1234...abcd`  
- You can start from `contracts/contract_address.example.txt`: copy to `contract_address.txt` and replace the placeholder line.
- Optional: prefix lines with `#` for comments; the backend ignores `#` lines and blank lines.

**Alternative — environment variable**

- Set `CHAIN_CUSTODY_CONTRACT_ADDRESS=0x...` so the backend uses that address without editing the file (still need `contracts/contract_abi.json`).

## 6. Verify in Remix / Ganache UI

- In Remix, under **Deployed Contracts**, call **`getEvidenceCount`**, **`getEvidence`**, **`verifyEvidence`** (view) with an `evidenceId` and hash string after uploads from the app.
- In Ganache, open a transaction sent by the app or Remix and inspect input/logs for transparency.

## 7. Run the app

From repo root (after ABI + address are in place):

```bash
cd backend && python app.py
```

If the contract is missing or the address is wrong, `GET /api/status` reports `deployed: false` until artifacts are fixed.
