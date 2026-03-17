import os
import json
from dbsettings import get_session
from sqlmodel import Session, select
from sqlalchemy import func
from models.wallet import WalletUser, UserTransaction, UserThreatRecord
from models.analysis import ContractRegistryCache, SimulationResult, AIAnalysis
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3
from substrateinterface import SubstrateInterface

app = FastAPI()

# --- CONFIGURATION ---
MOONBASE_RPC = "https://rpc.api.moonbase.moonbeam.network"
PEOPLE_CHAIN_RPC = "wss://polkadot-people-rpc.polkadot.io"

# Deployed address from Remix
CONTRACT_ADDRESS = "0x2192c59b98904bCc01D3b31607F041f32CA8b58C"

# Load ABI
try:
    with open("registry_abi.json", "r") as f:
        CONTRACT_ABI = json.load(f)
except FileNotFoundError:
    print("ERROR: registry_abi.json not found! Please create it in this folder.")
    CONTRACT_ABI = []

# Initialize Blockchain Connections
w3 = Web3(Web3.HTTPProvider(MOONBASE_RPC))
registry_contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# CORS middleware here (frontend integration ito)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---


class TransactionRequest(BaseModel):
    to: str
    data: str = "0x"

# --- CORE LOGIC ---


def get_polkadot_identity(address: str):

    # Handles both 0x EVM addresses and native SS58 addresses.
    # Translates H160 (20-byte) to AccountId32 (32-byte) for the People Chain.

    try:
        substrate = SubstrateInterface(url=PEOPLE_CHAIN_RPC)

        # 1. Address Mapping (The '32-byte' fix)
        # If EVM address, pad it to 64 hex characters (32 bytes)
        search_address = address
        if address.startswith("0x") and len(address) == 42:
            search_address = "0x" + address[2:].lower().zfill(64)

        # 2. Query Identity Pallet
        result = substrate.query("Identity", "IdentityOf", [search_address])

        if result and result.value:
            # Extract name from SCALE encoded storage
            display_data = result.value.get('info', {}).get('display', {})

            if 'Raw' in display_data:
                raw_name = display_data['Raw']
                # Decode hex string if necessary
                name = bytes.fromhex(raw_name[2:]).decode(
                    'utf-8') if raw_name.startswith('0x') else raw_name
                return {"verified": True, "name": name}

        return {"verified": False, "name": "Anonymous"}
    except Exception as e:
        return {"verified": False, "error": f"Chain Query Error: {str(e)}"}

# --- API ENDPOINTS ---


@app.get("/")
async def root():
    return {"message": "A.E.G.I.S. Backend Online", "docs": "/docs"}


@app.post("/analyze-intent")
async def analyze_intent(tx_payload: TransactionRequest):

    # The main engine: Checks Moonbeam Registry + Polkadot Identity.

    target_addr = tx_payload.to

    # A. Check On-Chain Registry (Moonbeam)
    # 0=Unknown, 1=Safe, 2=Malicious
    try:
        status_code = registry_contract.functions.checkAddress(
            target_addr).call()
    except Exception:
        status_code = 0

    status_labels = {0: "Unknown", 1: "Safe", 2: "Malicious"}
    verdict = status_labels.get(status_code, "Unknown")

    # B. Check Polkadot Social Reputation (People Chain)
    identity = get_polkadot_identity(target_addr)

    # C. Final Response for RAG/Frontend
    return {
        "address": target_addr,
        "registry_status": verdict,
        "on_chain_identity": identity,
        "security_context": {
            "is_flagged": verdict == "Malicious",
            "is_verified_entity": identity.get("verified", False),
            "risk_score": 100 if verdict == "Malicious" else 0
        }
    }


@app.post("/wallets/")
def create_wallet(wallet: WalletUser, session: Session = Depends(get_session)):
    existing_wallet = session.get(WalletUser, wallet.wallet_address)
    if existing_wallet:
        raise HTTPException(status_code=400, detail="Wallet already exists")
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


@app.get("/wallets/")
def get_wallets(session: Session = Depends(get_session)):
    return session.query(WalletUser).all()


@app.get("/stats/{wallet_address}")
def get_stats(wallet_address: str, session: Session = Depends(get_session)):
    wallet = session.get(WalletUser, wallet_address)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    threats_blocked = session.exec(
        select(func.count()).where(
            UserThreatRecord.wallet_address == wallet_address,
            UserTransaction.status == 2
        )
    ).one()

    safe_transactions = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address,
            UserTransaction.risk_level == 0,
        )
    ).one()

    total_scanned = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address
        )
    ).one()

    pending = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address,
            UserTransaction.status == 1
        )
    ).one()

    protection_rate = 0
    if total_scanned > 0:
        protection_rate = (safe_transactions / total_scanned) * 100

    return {
        "threats_blocked": threats_blocked,
        "safe_transactions": safe_transactions,
        "total_scanned": total_scanned,
        "pending": pending,
        "protection_rate": round(protection_rate, 2)
    }
