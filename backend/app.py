import json
import secrets
import requests  # for simulation
from dbsettings import get_session
from sqlmodel import Session, select
from sqlalchemy import func
from typing import Optional
# needed lahat tong models for the crud endpoints
from models.wallet import WalletUser, UserTransaction, UserThreatRecord
from models.analysis import ContractRegistryCache, SimulationResult, AIAnalysis
from models.session import AuthSession
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3
from substrateinterface import SubstrateInterface
from eth_account.messages import encode_defunct  # for signature verification
from eth_account import Account
# auto time date for some (for now, test purposes palang gamit)
from datetime import datetime, timezone

app = FastAPI()

# --- CONFIGURATION ---
MOONBASE_RPC = "https://rpc.api.moonbase.moonbeam.network"
PEOPLE_CHAIN_RPC = "wss://polkadot-people-rpc.polkadot.io"

# Deployed address from Remix
CONTRACT_ADDRESS = "0x7ee027F48589687939b9Db9AaE017e31E8f1c711"

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

    # simulation part from here


def simulate_transaction(transaction):
    url = MOONBASE_RPC

    payload = {
        "jsonrpc": "2.0",
        "method": "debug_traceCall",
        "params": [{
            "from": transaction.get("from"),
            "to": transaction.get("to"),
            "data": transaction.get("data", "0x"),
            "value": hex(transaction.get("value", 0)),
        },
            "latest",
            {
            "tracer": "callTracer"
        }
        ],
        "id": 1
    }

    try:
        response = requests.post(url, json=payload).json()
        return response.get("result", {})
    except Exception as e:
        return {"error": f"Simulation Error: {str(e)}"}


def analyze_trace(trace):
    effects = {
        "transfers": [],
        "approvals": [],
        "contracts_interacted": set(),
        "risk_flags": []
    }

    def recursive_trace(call):
        if not call:
            return

        to = call.get("to")
        input_data = call.get("input", "")
        call_type = call.get("type")

        if to:
            effects["contracts_interacted"].add(to)

        if input_data.startswith("0x095ea7b3"):  # approve
            effects["approvals"].append({
                "contract": to,
                "raw": input_data
            })

        if input_data.startswith("0xa9059cbb"):  # transfer
            effects["transfers"].append({
                "contract": to,
                "raw": input_data
            })

        if call_type == "DELEGATECALL":
            effects["risk_flags"].append("DELEGATECALL")

        # recurse
        for sub in call.get("calls", []):
            recursive_trace(sub)

    recursive_trace(trace)

    # convert set → list
    effects["contracts_interacted"] = list(effects["contracts_interacted"])

    return effects

# --- API ENDPOINTS ---


@app.get("/")
async def root():
    return {"message": "A.E.G.I.S. Backend Online", "docs": "/docs"}


@app.post("/analyze-intent")
async def analyze_intent(tx_payload: TransactionRequest):
    target_addr = tx_payload.to
    # adding the simulation dito

    trace = simulate_transaction({
        "from": "0x9Fa19B5662DDecc1B6fd3183B0dC08ADb17a42d4",  # dummy sender for simulation
        "to": target_addr,
        "data": tx_payload.data,
        "value": 100
    })

    effects = analyze_trace(trace)

    # The main engine: Checks Moonbeam Registry + Polkadot Identity.

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
    print("TRACE:", trace)
    print("EFFECTS:", effects)
    return {
        "address": target_addr,
        "registry_status": verdict,
        "effects": effects,
        "on_chain_identity": identity,
        "security_context": {
            "is_flagged": verdict == "Malicious",
            "is_verified_entity": identity.get("verified", False),
            "risk_score": 100 if verdict == "Malicious" else 0
        }
    }

# Wallet endpoints


@app.post("/wallets/")
def create_wallet(wallet: WalletUser, session: Session = Depends(get_session)):
    existing_wallet = session.get(WalletUser, wallet.wallet_address)
    if existing_wallet:
        raise HTTPException(status_code=400, detail="Wallet already exists")
    now = datetime.now(timezone.utc)
    wallet.created_timestamp = now
    wallet.last_login = now
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


@app.get("/wallets/")
def get_wallets(session: Session = Depends(get_session)):
    return session.query(WalletUser).all()


@app.get("/wallets/{wallet_address}")
def get_wallet(wallet_address: str, session: Session = Depends(get_session)):
    wallet = session.get(WalletUser, wallet_address)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


@app.delete("/wallets/{wallet_address}")
def delete_wallet(wallet_address: str, session: Session = Depends(get_session)):
    wallet = session.get(WalletUser, wallet_address)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    session.query(AuthSession).filter(
        AuthSession.wallet_address == wallet_address
    ).delete(synchronize_session=False)

    tx_hashes = [
        row[0] for row in session.query(UserTransaction.transaction_hash).filter(
            UserTransaction.wallet_address == wallet_address
        ).all()
    ]

    if tx_hashes:
        session.query(SimulationResult).filter(
            SimulationResult.transaction_hash.in_(tx_hashes)
        ).delete(synchronize_session=False)

        session.query(AIAnalysis).filter(
            AIAnalysis.transaction_hash.in_(tx_hashes)
        ).delete(synchronize_session=False)

        session.query(UserThreatRecord).filter(
            UserThreatRecord.transaction_hash.in_(tx_hashes)
        ).delete(synchronize_session=False)

    session.query(UserThreatRecord).filter(
        UserThreatRecord.wallet_address == wallet_address
    ).delete(synchronize_session=False)

    session.query(UserTransaction).filter(
        UserTransaction.wallet_address == wallet_address
    ).delete(synchronize_session=False)

    session.delete(wallet)
    session.commit()
    return {"message": "Deleted wallet and all associated data"}


@app.put("/wallets/{wallet_address}")
def update_wallet(wallet_address: str, updated: WalletUser, session: Session = Depends(get_session)):
    wallet = session.get(WalletUser, wallet_address)

    if not wallet:
        raise HTTPException(status_code=404, detail="Not found")

    wallet.last_login = updated.last_login
    session.add(wallet)
    session.commit()

    return wallet


@app.get("/transactions/")
def get_transactions(
    wallet_address: Optional[str] = Query(default=None),
    status: Optional[int] = Query(default=None),
    risk: Optional[int] = Query(default=None),
    limit: int = Query(default=100),
    session: Session = Depends(get_session)
):
    query = session.query(UserTransaction)
    if wallet_address:
        query = query.filter(UserTransaction.wallet_address == wallet_address)
    if status is not None:
        query = query.filter(UserTransaction.status == status)
    if risk is not None:
        query = query.filter(UserTransaction.risk_level == risk)
    results = query.order_by(
        UserTransaction.timestamp.desc()).limit(limit).all()
    return {"transactions": results, "total": len(results)}


@app.get("/transactions/{wallet_address}")
def get_transactions_by_wallet(wallet_address: str, session: Session = Depends(get_session)):
    return session.query(UserTransaction).filter(UserTransaction.wallet_address == wallet_address).all()


@app.post("/transactions/")
def create_transaction(tx: UserTransaction, session: Session = Depends(get_session)):
    existing = session.get(UserTransaction, tx.transaction_hash)
    if existing:
        raise HTTPException(
            status_code=400, detail="Transaction hash already exists")
    tx.timestamp = datetime.now(timezone.utc)
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


@app.get("/transactions/{tx_hash}/detail")
def get_transaction_by_hash(tx_hash: str, session: Session = Depends(get_session)):
    tx = session.get(UserTransaction, tx_hash)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@app.patch("/transactions/{tx_hash}/status")
def update_transaction_status(tx_hash: str, data: dict, session: Session = Depends(get_session)):
    tx = session.get(UserTransaction, tx_hash)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    new_status = data.get("status")
    status_map = {"approved": 2, "pending": 1, "rejected": 0}
    if new_status not in status_map:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {list(status_map.keys())}")
    tx.status = status_map[new_status]
    session.add(tx)
    session.commit()
    return {"message": f"Transaction status updated to '{new_status}'", "transaction_hash": tx_hash}


@app.delete("/transactions/{tx_hash}")
def delete_tx(tx_hash: str, session: Session = Depends(get_session)):
    tx = session.get(UserTransaction, tx_hash)
    if not tx:
        raise HTTPException(status_code=404, detail="Not found")

    # Delete all children first
    session.query(SimulationResult).filter(
        SimulationResult.transaction_hash == tx_hash
    ).delete(synchronize_session=False)

    session.query(AIAnalysis).filter(
        AIAnalysis.transaction_hash == tx_hash
    ).delete(synchronize_session=False)

    session.query(UserThreatRecord).filter(
        UserThreatRecord.transaction_hash == tx_hash
    ).delete(synchronize_session=False)

    session.delete(tx)
    session.commit()
    return {"message": "Deleted transaction and all related records"}


@app.get("/threats/")
def get_threats(session: Session = Depends(get_session)):
    return session.query(UserThreatRecord).all()


@app.get("/threats/{threat_id}")
def get_threat(threat_id: int, session: Session = Depends(get_session)):
    threat = session.get(UserThreatRecord, threat_id)
    if not threat:
        raise HTTPException(status_code=404, detail="Not found")
    return threat


@app.post("/threats/")
def create_threat(threat: UserThreatRecord, session: Session = Depends(get_session)):
    threat.timestamp = datetime.now(timezone.utc)
    session.add(threat)
    session.commit()
    session.refresh(threat)
    return threat


@app.put("/threats/{threat_id}")
def update_threat(threat_id: int, updated: UserThreatRecord, session: Session = Depends(get_session)):
    threat = session.get(UserThreatRecord, threat_id)
    if not threat:
        raise HTTPException(status_code=404, detail="Not found")
    threat.threat_description = updated.threat_description
    threat.risk_level = updated.risk_level
    session.add(threat)
    session.commit()
    return threat


@app.delete("/threats/{threat_id}")
def delete_threat(threat_id: int, session: Session = Depends(get_session)):
    threat = session.get(UserThreatRecord, threat_id)
    if not threat:
        raise HTTPException(status_code=404, detail="Not found")
    session.delete(threat)
    session.commit()
    return {"message": "Deleted"}


@app.get("/simulations/")
def get_simulations(session: Session = Depends(get_session)):
    return session.query(SimulationResult).all()


@app.post("/simulations/")
def create_simulation(sim: SimulationResult, session: Session = Depends(get_session)):
    session.add(sim)
    session.commit()
    session.refresh(sim)
    return sim


@app.put("/simulations/{sim_id}")
def update_simulation(sim_id: int, updated: SimulationResult, session: Session = Depends(get_session)):
    sim = session.get(SimulationResult, sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Not found")
    sim.simulation_summary = updated.simulation_summary
    session.add(sim)
    session.commit()
    return sim


@app.delete("/simulations/{sim_id}")
def delete_simulation(sim_id: int, session: Session = Depends(get_session)):
    sim = session.get(SimulationResult, sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Not found")
    session.delete(sim)
    session.commit()
    return {"message": "Deleted"}


@app.get("/analyses/")
def get_analyses(session: Session = Depends(get_session)):
    return session.query(AIAnalysis).all()


@app.post("/analyses/")
def create_analysis(analysis: AIAnalysis, session: Session = Depends(get_session)):
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis


@app.put("/analyses/{analysis_id}")
def update_analysis(analysis_id: int, updated: AIAnalysis, session: Session = Depends(get_session)):
    analysis = session.get(AIAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Not found")
    analysis.ai_summary = updated.ai_summary
    analysis.recommendation = updated.recommendation
    analysis.trust_score = updated.trust_score
    session.add(analysis)
    session.commit()
    return analysis


@app.delete("/analyses/{analysis_id}")
def delete_analysis(analysis_id: int, session: Session = Depends(get_session)):
    analysis = session.get(AIAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Not found")
    session.delete(analysis)
    session.commit()
    return {"message": "Deleted"}


@app.get("/registry/")
def get_registry(session: Session = Depends(get_session)):
    return session.query(ContractRegistryCache).all()


@app.post("/registry/")
def create_registry(entry: ContractRegistryCache, session: Session = Depends(get_session)):
    existing = session.get(ContractRegistryCache, entry.contract_address)
    if existing:
        raise HTTPException(status_code=400, detail="Entry already exists")
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@app.put("/registry/{contract_address}")
def update_registry(contract_address: str, updated: ContractRegistryCache, session: Session = Depends(get_session)):
    entry = session.get(ContractRegistryCache, contract_address)
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    entry.is_verified = updated.is_verified
    entry.tregistry_status = updated.tregistry_status
    entry.last_checked_timestamp = updated.last_checked_timestamp
    session.add(entry)
    session.commit()
    return entry


@app.delete("/registry/{contract_address}")
def delete_registry(contract_address: str, session: Session = Depends(get_session)):
    entry = session.get(ContractRegistryCache, contract_address)
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    session.delete(entry)
    session.commit()
    return {"message": "Deleted"}


@app.get("/stats/{wallet_address}")
def get_stats(wallet_address: str, session: Session = Depends(get_session)):
    wallet = session.get(WalletUser, wallet_address)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    threats_blocked = session.exec(
        select(func.count()).where(
            UserThreatRecord.wallet_address == wallet_address
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


@app.get("/auth/nonce/{wallet_address}")
def get_nonce(wallet_address: str, session: Session = Depends(get_session)):
    wallet = session.get(WalletUser, wallet_address)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    nonce = secrets.token_hex(16)
    auth = AuthSession(wallet_address=wallet_address, nonce=nonce,
                       created_timestamp=datetime.now(timezone.utc))
    session.add(auth)
    session.commit()
    return {"nonce": nonce}


@app.post("/sync/{wallet_address}")
def sync_wallet(wallet_address: str, session: Session = Depends(get_session)):
    wallet = session.get(WalletUser, wallet_address)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    wallet.last_login = datetime.now(timezone.utc)
    session.add(wallet)
    session.commit()
    return {"message": "Wallet synced", "wallet_address": wallet_address}


@app.post("/auth/verify/")
def verify_signature(data: dict, session: Session = Depends(get_session)):
    wallet_address = data["wallet_address"]
    signature = data["signature"]

    auth = session.exec(
        select(AuthSession)
        .where(AuthSession.wallet_address == wallet_address)
        .order_by(AuthSession.created_timestamp.desc())
    ).first()

    if not auth:
        raise HTTPException(status_code=404, detail="Nonce not found")

    message = f"Login to AEGIS:\nNonce: {auth.nonce}"
    encoded_message = encode_defunct(text=message)

    try:
        recovered_address = Account.recover_message(
            encoded_message, signature=signature)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Signature verification failed: {str(e)}")

    if recovered_address.lower() != wallet_address.lower():
        raise HTTPException(
            status_code=400, detail="Signature does not match wallet address")

    auth.signature = signature
    session.add(auth)

    # Auto-register the wallet if it doesn't exist yet
    wallet = session.get(WalletUser, wallet_address)
    if not wallet:
        now = datetime.now(timezone.utc)
        wallet = WalletUser(
            wallet_address=wallet_address,
            created_timestamp=now,
            last_login=now
        )
        session.add(wallet)
    else:
        wallet.last_login = datetime.now(timezone.utc)
        session.add(wallet)

    session.commit()
    return {"message": "Authentication successful", "wallet_address": wallet_address}
