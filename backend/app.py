import json
import ast
import sys
import os
import secrets
import tempfile
import subprocess
import eth_abi
from decimal import Decimal
from dbsettings import get_session
from sqlmodel import Session, select
from sqlalchemy import func
from typing import Optional
from models.wallet import WalletUser, UserTransaction, UserThreatRecord
from models.analysis import ContractRegistryCache, SimulationResult, AIAnalysis
from models.session import AuthSession
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3
from substrateinterface import SubstrateInterface
from eth_account.messages import encode_defunct
from eth_account import Account
from datetime import datetime, timezone

app = FastAPI()
# --- CONFIGURATION ---

# Swap to Westend Hub before passing?:
#   CHAIN_RPC = "https://westend-asset-hub-eth-rpc.polkadot.io"
#   CHAIN_CURRENCY = "WND"
MOONBASE_RPC = "https://rpc.api.moonbase.moonbeam.network"
CHAIN_CURRENCY = "DEV"
PEOPLE_CHAIN_RPC = "wss://polkadot-people-rpc.polkadot.io"

# Deployed address from Remix
# iniba ko name kalito eh
REGISTRY_ADDRESS = "0x7ee027F48589687939b9Db9AaE017e31E8f1c711"

# Absolute path to the hardhat_sim directory (sits next to main.py)
HARDHAT_SIM_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "hardhat_sim")

# On Windows npx lives as npx.cmd; on POSIX it's just npx
NPX = "npx.cmd" if sys.platform == "win32" else "npx"

try:
    with open("registry_abi.json", "r") as f:
        # iniba ko din name, para straightforward ;))))
        REGISTRY_ABI = json.load(f)
except FileNotFoundError:
    print("ERROR: registry_abi.json not found.")
    REGISTRY_ABI = []

w3 = Web3(Web3.HTTPProvider(MOONBASE_RPC))
registry_contract = w3.eth.contract(
    address=REGISTRY_ADDRESS, abi=REGISTRY_ABI)

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
    sender: str           # who is signing
    to: str               # contract being called
    data: str = "0x"      # encoded calldata
    value: int = 0        # native token value in wei


# hardcoded selectors (pwede lipat)

KNOWN_SELECTORS = {
    "095ea7b3": "approve(address,uint256)",
    "a9059cbb": "transfer(address,uint256)",
    "23b872dd": "transferFrom(address,address,uint256)",
    "39509351": "increaseAllowance(address,uint256)",
    "a22cb465": "setApprovalForAll(address,bool)",
    "42842e0e": "safeTransferFrom(address,address,uint256)",
    "b88d4fde": "safeTransferFrom(address,address,uint256,bytes)",
    "ac9650d8": "multicall(bytes[])",
    "e449022e": "uniswapV3Swap(uint256,uint256,uint160[])",
    "40c10f19": "mint(address,uint256)",
    "a0712d68": "mint(uint256)",
}

APPROVAL_SELECTORS = {"095ea7b3", "39509351", "a22cb465"}
TRANSFER_SELECTORS = {"a9059cbb", "23b872dd", "42842e0e", "b88d4fde"}


# token formating function, pwede lipat another file

def format_amount(raw: int, decimals: int = 18) -> dict:
    divisor = Decimal(10 ** decimals)
    human = Decimal(raw) / divisor
    return {
        "raw": raw,
        "human": float(human),
        "formatted": f"{human:.6f} {CHAIN_CURRENCY}",
    }


def get_token_decimals(token_address: str) -> int:
    DECIMALS_ABI = [{
        "inputs": [], "name": "decimals",
        "outputs": [{"type": "uint8"}],
        "stateMutability": "view", "type": "function"
    }]
    try:
        token = w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=DECIMALS_ABI
        )
        return token.functions.decimals().call()
    except Exception:
        return 18


# note: naglagay ako mga layers para sa simulation report, nakakainis kaya dinamihan ko na ;)) 11 hours though..
# layer 1 - calldata decode (ABI, selectors, etc.)

def decode_calldata(data: str, contract_address: str) -> dict:
    if not data or data == "0x" or len(data) < 10:
        return {
            "function": "native_transfer",
            "selector": None,
            "args": {},
            "decoded_via": "none",
            "intent_summary": "Direct native token transfer - no contract function called.",
        }

    selector = data[2:10].lower()

    try:
        func_obj, decoded_args = registry_contract.decode_function_input(data)
        safe_args = {
            k: v.hex() if isinstance(v, bytes) else str(v)
            for k, v in decoded_args.items()
        }
        return {
            "function": func_obj.fn_name,
            "selector": selector,
            "args": safe_args,
            "decoded_via": "abi",
            "intent_summary": f"Calls '{func_obj.fn_name}' on the registry contract.",
        }
    except Exception:
        pass

    known = KNOWN_SELECTORS.get(selector)
    if known:
        result = {
            "function": known,
            "selector": selector,
            "args": {},
            "decoded_via": "selector_table",
        }

        try:
            decimals = get_token_decimals(contract_address)

            if selector in {"a9059cbb", "095ea7b3", "39509351"}:
                recipient = "0x" + data[34:74]
                amount_raw = int(data[74:138], 16)
                result["args"] = {
                    "recipient_or_spender": recipient,
                    "amount": format_amount(amount_raw, decimals),
                }

            elif selector == "23b872dd":
                from_addr = "0x" + data[34:74]
                to_addr = "0x" + data[98:138]
                amount_raw = int(data[138:202], 16)
                result["args"] = {
                    "from": from_addr,
                    "to": to_addr,
                    "amount": format_amount(amount_raw, decimals),
                }

            elif selector == "a22cb465":
                operator = "0x" + data[34:74]
                approved = bool(int(data[74:138], 16))
                result["args"] = {
                    "operator": operator,
                    "approved": approved,
                }
        except Exception:
            result["args"] = {"raw_calldata": data}

        fn = result["function"]
        args = result["args"]
        if selector in APPROVAL_SELECTORS:
            spender = args.get("recipient_or_spender",
                               args.get("operator", "unknown"))
            amount = args.get("amount", {}).get("formatted", "unknown amount")
            result["intent_summary"] = (
                f"Grants spending rights of {amount} to {spender}. "
                f"This allows that address to spend tokens on your behalf."
            )
        elif selector in TRANSFER_SELECTORS:
            recipient = args.get("recipient_or_spender",
                                 args.get("to", "unknown"))
            amount = args.get("amount", {}).get("formatted", "unknown amount")
            result["intent_summary"] = f"Transfers {amount} to {recipient}."
        elif selector == "ac9650d8":
            result["intent_summary"] = (
                "Multicall - batches multiple contract calls into one transaction. "
                "The exact sub-calls are not visible without a tracing node."
            )
        else:
            result["intent_summary"] = f"Calls '{fn}'."

        return result

    return {
        "function": "unknown",
        "selector": selector,
        "args": {"raw_calldata": data},
        "decoded_via": "none",
        "intent_summary": (
            f"Unknown function selector 0x{selector}. "
            "This function is not in any known ABI or selector database."
        ),
    }

# layer 2 - hardhat simulation, works fine pero need ng node


def get_storage_slot(holder: str, mapping_slot: int = 0) -> int:
    return int(Web3.keccak(
        eth_abi.encode(
            ["address", "uint256"],
            [Web3.to_checksum_address(holder), mapping_slot]
        )
    ).hex(), 16)


def simulate_with_hardhat(sender: str, to: str, data: str, value: int = 0) -> dict:
    checksum_sender = Web3.to_checksum_address(sender)
    checksum_to = Web3.to_checksum_address(to)

    real_dev_balance = str(w3.eth.get_balance(checksum_sender))

    real_code = w3.eth.get_code(checksum_to)
    is_contract = len(real_code) > 2

    real_token_balance = 0
    token_balance_slot = None
    if is_contract:
        try:
            token_balance_slot = get_storage_slot(checksum_sender, 0)
            raw_slot = w3.eth.get_storage_at(checksum_to, token_balance_slot)
            real_token_balance = int(raw_slot.hex(), 16)
        except Exception:
            pass

    params = {
        "sender":              checksum_sender,
        "to":                  checksum_to,
        "data":                data or "0x",
        "value":               value,
        "real_dev_balance":    real_dev_balance,
        "token_balance_slot":  token_balance_slot,
        "real_token_balance":  real_token_balance,
    }

    # Use a named temp file; delete=False so the subprocess can read it
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_params.json", delete=False, dir=tempfile.gettempdir()
    ) as pf:
        json.dump(params, pf)
        params_file = pf.name

    output_file = params_file.replace("_params.json", "_result.json")

    try:
        env = os.environ.copy()
        env["SIM_PARAMS_FILE"] = params_file
        env["SIM_OUTPUT_FILE"] = output_file
        env["CHAIN_RPC"] = MOONBASE_RPC

        proc = subprocess.run(
            [NPX, "hardhat", "run", "scripts/simulate.js", "--network", "hardhat"],
            cwd=HARDHAT_SIM_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )

        if not os.path.exists(output_file):
            stderr_snippet = proc.stderr[-800:
                                         ] if proc.stderr else "(no stderr)"
            raise RuntimeError(
                f"Hardhat script did not produce output. "
                f"Exit code: {proc.returncode}. stderr: {stderr_snippet}"
            )

        with open(output_file, "r") as f:
            sim_raw = json.load(f)

    except FileNotFoundError:
        return _fallback_gas_estimate(
            sender, to, data, value,
            note=(
                "Node.js / npx not found. Install Node.js and run "
                "`cd hardhat_sim && npm install` to enable full fork simulation."
            ),
        )

    except subprocess.TimeoutExpired:
        return _fallback_gas_estimate(
            sender, to, data, value,
            note="Hardhat simulation timed out. Falling back to eth_estimateGas.",
        )

    except Exception as exc:
        return _fallback_gas_estimate(
            sender, to, data, value,
            note=f"Hardhat simulation error: {exc}",
        )

    finally:
        for path in [params_file, output_file]:
            try:
                os.unlink(path)
            except OSError:
                pass

    decimals = get_token_decimals(checksum_to)
    dev_before = int(sim_raw.get("dev_before", "0"))
    dev_after = int(sim_raw.get("dev_after",  "0"))
    gas_used = sim_raw.get("gas_used")
    gas_price = sim_raw.get("gas_price") or w3.eth.gas_price

    decoded_events = decode_events(sim_raw.get("raw_logs", []), checksum_to)

    dev_spent = max(0, dev_before - dev_after)

    return {
        "success":         sim_raw["success"],
        "reverted":        sim_raw["reverted"],
        "revert_reason":   sim_raw.get("revert_reason"),
        "gas_used":        gas_used,
        "gas_cost":        format_amount(gas_used * gas_price) if gas_used and gas_price else None,
        "events_emitted":  decoded_events,
        "state_diff": {
            "sender_dev_before":     format_amount(dev_before),
            "sender_dev_after":      format_amount(dev_after),
            "sender_dev_spent":      format_amount(dev_spent),
            "token_balance_before":  format_amount(real_token_balance, decimals),
        },
        "simulation_note": sim_raw.get("simulation_note", "Hardhat fork simulation."),
    }


def _fallback_gas_estimate(
    sender: str,
    to: str,
    data: str,
    value: int,
    note: str = "Fallback: eth_estimateGas on live RPC.",
) -> dict:
    try:
        gas_estimate = w3.eth.estimate_gas({
            "from": Web3.to_checksum_address(sender),
            "to":   Web3.to_checksum_address(to),
            "data": data or "0x",
            "value": value,
        })
        gas_price = w3.eth.gas_price
        return {
            "success":        True,
            "reverted":       False,
            "revert_reason":  None,
            "gas_used":       gas_estimate,
            "gas_cost":       format_amount(gas_estimate * gas_price),
            "events_emitted": [],
            "state_diff":     {},
            "simulation_note": note,
        }
    except Exception as exc:
        err_str = str(exc)
        revert_reason = "execution reverted (no reason string)"
        if "execution reverted:" in err_str:
            revert_reason = err_str.split("execution reverted:", 1)[1].strip()
        elif "VM Exception" in err_str:
            try:
                err_dict = ast.literal_eval(err_str)
                msg = err_dict.get("message", revert_reason)
                if "VM Exception" not in msg:
                    revert_reason = msg
            except Exception:
                pass
        return {
            "success":        False,
            "reverted":       True,
            "revert_reason":  revert_reason,
            "gas_used":       None,
            "gas_cost":       None,
            "events_emitted": [],
            "state_diff":     {},
            "simulation_note": f"{note} — eth_estimateGas also failed.",
        }


def decode_events(raw_logs: list, contract_address: str) -> list:
    TRANSFER_TOPIC = w3.keccak(text="Transfer(address,address,uint256)").hex()
    APPROVAL_TOPIC = w3.keccak(text="Approval(address,address,uint256)").hex()
    APPROVAL_ALL_TOPIC = w3.keccak(
        text="ApprovalForAll(address,address,bool)").hex()

    UINT256_MAX = (2 ** 256) - 1

    decoded = []
    decimals = get_token_decimals(contract_address)

    for log in raw_logs:
        topics = log.get("topics", [])
        if not topics:
            continue
        topic0 = topics[0] if topics[0].startswith("0x") else "0x" + topics[0]

        try:
            if topic0 == TRANSFER_TOPIC:
                # Need at least topic0 + 2 indexed args
                from_addr = ("0x" + topics[1][-40:]
                             ) if len(topics) > 1 else "unknown"
                to_addr = ("0x" + topics[2][-40:]
                           ) if len(topics) > 2 else "unknown"
                amount_raw = int(log["data"], 16) if log.get(
                    "data", "0x") != "0x" else 0
                decoded.append({
                    "event":  "Transfer",
                    "from":   from_addr,
                    "to":     to_addr,
                    "amount": format_amount(amount_raw, decimals),
                })

            elif topic0 == APPROVAL_TOPIC:
                owner = ("0x" + topics[1][-40:]
                         ) if len(topics) > 1 else "unknown"
                spender = ("0x" + topics[2][-40:]
                           ) if len(topics) > 2 else "unknown"
                amount_raw = int(log["data"], 16) if log.get(
                    "data", "0x") != "0x" else 0

                # Flag unlimited approvals explicitly
                is_unlimited = (amount_raw >= UINT256_MAX)

                decoded.append({
                    "event":        "Approval",
                    "owner":        owner,
                    "spender":      spender,
                    "amount":       format_amount(amount_raw, decimals),
                    "is_unlimited": is_unlimited,
                    "warning":      "UNLIMITED APPROVAL — spender can drain all tokens" if is_unlimited else None,
                })

            elif topic0 == APPROVAL_ALL_TOPIC:
                owner = ("0x" + topics[1][-40:]
                         ) if len(topics) > 1 else "unknown"
                operator = ("0x" + topics[2][-40:]
                            ) if len(topics) > 2 else "unknown"
                approved = bool(int(log["data"], 16)) if log.get(
                    "data", "0x") != "0x" else False
                decoded.append({
                    "event":    "ApprovalForAll",
                    "owner":    owner,
                    "operator": operator,
                    "approved": approved,
                    "warning":  "FULL NFT COLLECTION APPROVAL — operator can transfer all NFTs" if approved else None,
                })

            else:
                decoded.append({
                    "event":    "unknown",
                    "topic":    topic0,
                    "raw_data": log.get("data", "0x"),
                })

        except Exception:
            decoded.append({"event": "decode_error", "raw": log})

    return decoded

#  layer 3 event scan


def scan_event_history(address: str) -> dict:
    try:
        checksum_addr = Web3.to_checksum_address(address)

        TRANSFER_TOPIC = w3.keccak(
            text="Transfer(address,address,uint256)").hex()
        APPROVAL_TOPIC = w3.keccak(
            text="Approval(address,address,uint256)").hex()
        APPROVAL_ALL_TOPIC = w3.keccak(
            text="ApprovalForAll(address,address,bool)").hex()

        latest = w3.eth.block_number
        from_block = max(0, latest - 1000)

        logs = w3.eth.get_logs({
            "address":   checksum_addr,
            "fromBlock": from_block,
            "toBlock":   "latest",
            "topics":    [[TRANSFER_TOPIC, APPROVAL_TOPIC, APPROVAL_ALL_TOPIC]]
        })

        transfers = [l for l in logs if l["topics"][0].hex() == TRANSFER_TOPIC]
        approvals = [l for l in logs if l["topics"][0].hex() in {
            APPROVAL_TOPIC, APPROVAL_ALL_TOPIC}]

        sample_recipients = list({
            "0x" + log["topics"][2].hex()[-40:]
            for log in transfers[:5]
            if len(log["topics"]) >= 3
        })

        return {
            "scanned_blocks":    f"{from_block} to {latest}",
            "past_transfers":    len(transfers),
            "past_approvals":    len(approvals),
            "sample_recipients": sample_recipients,
        }
    except Exception as exc:
        return {"error": f"Event scan failed: {str(exc)}"}


# layer 4, actually pwede wala to, very inaccurate

def get_bytecode_notes(address: str) -> dict:
    NOTABLE_OPCODES = {
        "f4": "DELEGATECALL (proxy/upgrade pattern)",
        "ff": "SELFDESTRUCT (contract can self-destruct)",
        "f5": "CREATE2 (deploys child contracts at deterministic address)",
    }
    try:
        checksum_addr = Web3.to_checksum_address(address)
        code = w3.eth.get_code(checksum_addr).hex()
        raw_code = code[2:] if code.startswith("0x") else code

        if len(raw_code) == 0:
            return {
                "is_contract":        False,
                "note":               "This address is a plain wallet, not a contract.",
                "structural_patterns": [],
            }

        found = []
        i = 0
        while i < len(raw_code) - 1:
            byte = raw_code[i:i+2]
            if byte in NOTABLE_OPCODES and NOTABLE_OPCODES[byte] not in found:
                found.append(NOTABLE_OPCODES[byte])
            i += 2

        return {
            "is_contract":         True,
            "bytecode_size_bytes": len(raw_code) // 2,
            "structural_patterns": found,
            "note": (
                "Structural patterns are informational only. "
                "False positives are possible without source code."
            ) if found else "No notable structural patterns detected.",
        }
    except Exception as exc:
        return {"error": f"Bytecode check failed: {str(exc)}"}


# trust registry heree

def check_trust_registry(address: str) -> dict:
    STATUS_LABELS = {0: "Unknown", 1: "Safe", 2: "Malicious"}
    try:
        status_code = registry_contract.functions.checkAddress(
            Web3.to_checksum_address(address)
        ).call()
        label = STATUS_LABELS.get(status_code, "Unknown")
        return {
            "status":             label,
            "is_flagged":         label == "Malicious",
            "is_verified_safe":   label == "Safe",
        }
    except Exception as exc:
        return {
            "status":           "Unknown",
            "is_flagged":       False,
            "is_verified_safe": False,
            "error":            str(exc),
        }


# polkadot identity

def get_polkadot_identity(address: str) -> dict:
    try:
        substrate = SubstrateInterface(url=PEOPLE_CHAIN_RPC)
        search_address = address
        if address.startswith("0x") and len(address) == 42:
            search_address = "0x" + address[2:].lower().zfill(64)
        result = substrate.query("Identity", "IdentityOf", [search_address])
        if result and result.value:
            display_data = result.value.get("info", {}).get("display", {})
            if "Raw" in display_data:
                raw_name = display_data["Raw"]
                name = (
                    bytes.fromhex(raw_name[2:]).decode("utf-8")
                    if raw_name.startswith("0x") else raw_name
                )
                return {"verified": True, "name": name}
        return {"verified": False, "name": None}
    except Exception as exc:
        return {"verified": False, "name": None, "error": str(exc)}


# main endpoints

@app.get("/")
async def root():
    return {"message": "A.E.G.I.S. Backend Online", "docs": "/docs"}


@app.post("/analyze-intent")
async def analyze_intent(tx_payload: TransactionRequest):
    sender = tx_payload.sender
    target = tx_payload.to
    data = tx_payload.data
    value = tx_payload.value

    intent = decode_calldata(data, target)

    simulation = simulate_with_hardhat(sender, target, data, value)

    history = scan_event_history(target)

    bytecode_notes = get_bytecode_notes(target)

    registry = check_trust_registry(target)

    identity = get_polkadot_identity(target)

    # Sender preflight
    preflight = {}
    try:
        sender_balance = w3.eth.get_balance(Web3.to_checksum_address(sender))
        sender_nonce = w3.eth.get_transaction_count(
            Web3.to_checksum_address(sender))
        preflight = {
            f"sender_balance_{CHAIN_CURRENCY.lower()}": format_amount(sender_balance),
            "sender_is_active": sender_nonce > 0,
            "sender_tx_count":  sender_nonce,
        }
    except Exception as exc:
        preflight = {"error": str(exc)}

    return {
        "target_address": target,
        "sender_address": sender,
        "intent":         intent,
        "preflight":      preflight,
        "simulation":     simulation,
        "history":        history,
        "bytecode_notes": bytecode_notes,
        "trust": {
            "registry":          registry,
            "polkadot_identity": identity,
        },
    }


# mga kalat na crud operations BAHAHAHAHA

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
    return session.query(UserTransaction).filter(
        UserTransaction.wallet_address == wallet_address).all()


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
            status_code=400,
            detail=f"Invalid status. Must be one of: {list(status_map.keys())}")
    tx.status = status_map[new_status]
    session.add(tx)
    session.commit()
    return {"message": f"Transaction status updated to '{new_status}'",
            "transaction_hash": tx_hash}


@app.delete("/transactions/{tx_hash}")
def delete_tx(tx_hash: str, session: Session = Depends(get_session)):
    tx = session.get(UserTransaction, tx_hash)
    if not tx:
        raise HTTPException(status_code=404, detail="Not found")
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
def delete_analysis(analysis_id: int, updated: AIAnalysis, session: Session = Depends(get_session)):
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
            UserThreatRecord.wallet_address == wallet_address)
    ).one()
    safe_transactions = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address,
            UserTransaction.risk_level == 0)
    ).one()
    total_scanned = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address)
    ).one()
    pending = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address,
            UserTransaction.status == 1)
    ).one()

    protection_rate = 0
    if total_scanned > 0:
        protection_rate = (safe_transactions / total_scanned) * 100

    return {
        "threats_blocked":   threats_blocked,
        "safe_transactions": safe_transactions,
        "total_scanned":     total_scanned,
        "pending":           pending,
        "protection_rate":   round(protection_rate, 2),
    }


@app.get("/auth/nonce/{wallet_address}")
def get_nonce(wallet_address: str, session: Session = Depends(get_session)):
    wallet = session.get(WalletUser, wallet_address)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    nonce = secrets.token_hex(16)
    auth = AuthSession(
        wallet_address=wallet_address,
        nonce=nonce,
        created_timestamp=datetime.now(timezone.utc)
    )
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
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Signature verification failed: {str(exc)}")

    if recovered_address.lower() != wallet_address.lower():
        raise HTTPException(
            status_code=400,
            detail="Signature does not match wallet address")

    auth.signature = signature
    session.add(auth)

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
