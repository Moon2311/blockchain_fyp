# Blockchain-Based Chain of Custody for Digital Forensics

**FYP — M. Talha | Roll No: fa-2022/BS/DFCS/075**

---

## Project Overview

A tamper-proof digital evidence management system using:
- **Ethereum (Ganache)** — private blockchain
- **Solidity** — smart contract (`ChainOfCustody.sol`)
- **Python + Flask** — web backend
- **Web3.py** — blockchain integration
- **SHA-256** — hash-based integrity verification
- **AES/Fernet** — optional file encryption
- **Bootstrap 5** — responsive dashboard UI

---

## Project Structure

```
fyp/
├── contracts/
│   └── ChainOfCustody.sol        ← Ethereum smart contract
├── backend/
│   ├── app.py                    ← Flask web server
│   ├── contract_abi.json         ← Generated after deploy
│   ├── contract_address.txt      ← Generated after deploy
│   └── fernet.key                ← Generated on first run
├── frontend/
│   ├── templates/
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── upload.html
│   │   ├── evidence_list.html
│   │   ├── evidence_detail.html
│   │   └── verify.html
│   └── static/
│       ├── css/style.css
│       └── js/main.js
├── uploads/                      ← Uploaded files stored here
├── deploy.py                     ← One-time deployment script
├── requirements.txt
└── README.md
```

---

## Setup Instructions

### Step 1 — Install Ganache

Download and install **Ganache GUI** from:
https://trufflesuite.com/ganache/

- Open Ganache → Click **Quickstart (Ethereum)**
- It runs on `http://127.0.0.1:7545` by default
- You'll see 10 pre-funded test accounts

### Step 2 — Install Python Dependencies

```bash
cd fyp/
pip install -r requirements.txt
```

### Step 3 — Deploy the Smart Contract

```bash
python deploy.py
```

This will:
1. Install Solidity compiler (`solc 0.8.20`) automatically
2. Compile `contracts/ChainOfCustody.sol`
3. Deploy to Ganache
4. Save ABI → `backend/contract_abi.json`
5. Save address → `backend/contract_address.txt`

### Step 4 — Run the Flask App

```bash
python backend/app.py
```

Open browser → **http://127.0.0.1:5000**

---

## Demo Login Credentials

| Username       | Password      | Role          |
|----------------|---------------|---------------|
| `admin`        | `admin123`    | Admin         |
| `investigator` | `inv123`      | Investigator  |
| `analyst`      | `analyst123`  | Analyst       |

---

## How It Works

### Evidence Upload Flow
1. User uploads a digital file (PDF, image, log, etc.)
2. Server computes **SHA-256** hash of the original file
3. (Optional) File is encrypted with **AES-256 (Fernet)**
4. Hash + metadata is sent to **ChainOfCustody** smart contract
5. Ganache mines a transaction — record is **permanent**

### Verification Flow
1. User re-uploads the suspected file
2. Server computes a **new SHA-256** hash
3. Hash is compared with blockchain-stored hash via `verifyEvidence()`
4. **Match** → ✅ Authentic | **Mismatch** → ❌ Tampered
5. Verification event is logged on-chain automatically

### Custody Actions
Every action (Transfer, Analyze, Archive) is logged as a new blockchain transaction through `logCustodyEvent()`, creating an immutable audit trail.

---

## Smart Contract Functions

| Function | Description |
|----------|-------------|
| `addEvidence(hash, name, type, size, user, encrypted)` | Records new evidence |
| `logCustodyEvent(id, hash, action, actor, notes)` | Logs a custody action |
| `verifyEvidence(id, newHash)` | Returns (isAuthentic, storedHash) |
| `getCustodyChain(id)` | Returns all events for an evidence item |
| `getEvidence(id)` | Returns evidence metadata |
| `getEvidenceCount()` | Returns total evidence count |

---

## API Endpoints (JSON)

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | Blockchain connection status |
| `GET /api/evidence` | List all evidence (JSON) |
| `GET /api/evidence/<id>/chain` | Get custody chain (JSON) |

---

## Technologies Used

| Technology | Purpose |
|-----------|---------|
| Ganache (Ethereum) | Private blockchain |
| Solidity 0.8.20 | Smart contract language |
| Python 3.10+ | Backend language |
| Flask 3.x | Web framework |
| Web3.py 6.x | Ethereum integration |
| py-solc-x | Solidity compiler |
| cryptography (Fernet) | AES encryption |
| Bootstrap 5 | Frontend UI |
| SHA-256 | File integrity hashing |

---

## Future Scope

- Cloud deployment (AWS / Azure)
- AI-based anomaly detection
- Mobile application
- Integration with forensic tools (Autopsy, Volatility)
- Legal environment deployment
- IPFS for decentralized file storage
