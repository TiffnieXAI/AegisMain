from __future__ import annotations
from datetime import datetime, timezone, timedelta
from eth_account import Account
from eth_account.messages import encode_defunct
from substrateinterface import SubstrateInterface
from web3 import Web3
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, Query
from models.session import AuthSession
from models.analysis import ContractRegistryCache, SimulationResult, AIAnalysis
from models.wallet import WalletUser, UserTransaction, UserThreatRecord
from typing import Optional
from sqlalchemy import func
from sqlmodel import Session, select
from dbsettings import get_session, engine
from decimal import Decimal
import eth_abi
import hashlib
import subprocess
import tempfile
import secrets
import ast
import json
import asyncio
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

AI_VERDICT_PATH = os.path.join(ROOT_DIR, 'ai', 'AI_verdict')
if AI_VERDICT_PATH not in sys.path:
    sys.path.append(AI_VERDICT_PATH)

from app_AI.main import analyze_from_sources as ai_analyze_from_sources

app = FastAPI()
# --- CONFIGURATION ---

# Swap to Westend Hub before passing?:
#   CHAIN_RPC = "https://westend-asset-hub-eth-rpc.polkadot.io"
MOONBASE_RPC = "https://rpc.api.moonbase.moonbeam.network"
PEOPLE_CHAIN_RPC = "wss://polkadot-people-rpc.polkadot.io"


_CHAIN_CURRENCY_MAP: dict[int, str] = {
    1:        "ETH",    # Ethereum Mainnet
    5:        "ETH",    # Goerli testnet
    11155111: "ETH",    # Sepolia testnet
    137:      "POL",    # Polygon Mainnet
    80001:    "POL",    # Mumbai testnet (Polygon)
    56:       "BNB",    # BNB Smart Chain
    97:       "BNB",    # BNB testnet
    43114:    "AVAX",   # Avalanche C-Chain
    42161:    "ETH",    # Arbitrum One
    10:       "ETH",    # Optimism
    8453:     "ETH",    # Base
    1284:     "GLMR",   # Moonbeam
    1285:     "MOVR",   # Moonriver
    1287:     "DEV",    # Moonbase Alpha (testnet)
    1337:     "ETH",    # Hardhat / Ganache local
    420420421: "WND",   # Westend Asset Hub
}


def _detect_chain_currency(web3_instance: "Web3") -> str:
    """Detect the native token symbol from the connected chain's ID."""
    try:
        chain_id = web3_instance.eth.chain_id
        return _CHAIN_CURRENCY_MAP.get(chain_id, "ETH")
    except Exception:
        return "ETH"


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

CHAIN_CURRENCY = _detect_chain_currency(w3)

# CORS middleware here (frontend integration ito)
origin = ["http://localhost:5500", "http://127.0.0.1:5500"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origin,
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

# Expanded topic database — covers most DeFi/NFT events
KNOWN_TOPICS = {
    "0x" + w3.keccak(text="Transfer(address,address,uint256)").hex():
        {"name": "Transfer",          "type": "erc20"},
    "0x" + w3.keccak(text="Approval(address,address,uint256)").hex():
        {"name": "Approval",          "type": "erc20"},
    "0x" + w3.keccak(text="ApprovalForAll(address,address,bool)").hex():
        {"name": "ApprovalForAll",    "type": "erc721"},
    "0x" + w3.keccak(text="Transfer(address,address,uint256,uint256)").hex():
        {"name": "TransferSingle",    "type": "erc1155"},
    "0x" + w3.keccak(text="TransferBatch(address,address,address,uint256[],uint256[])").hex():
        {"name": "TransferBatch",     "type": "erc1155"},
    "0x" + w3.keccak(text="Deposit(address,uint256)").hex():
        {"name": "Deposit",           "type": "defi"},
    "0x" + w3.keccak(text="Withdrawal(address,uint256)").hex():
        {"name": "Withdrawal",        "type": "defi"},
    "0x" + w3.keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex():
        {"name": "Swap",              "type": "dex"},
    "0x" + w3.keccak(text="OwnershipTransferred(address,address)").hex():
        {"name": "OwnershipTransferred", "type": "admin"},
    "0x" + w3.keccak(text="Upgraded(address)").hex():
        {"name": "Upgraded",          "type": "proxy"},
    "0x" + w3.keccak(text="AdminChanged(address,address)").hex():
        {"name": "AdminChanged",      "type": "proxy"},
    "0x" + w3.keccak(text="Paused(address)").hex():
        {"name": "Paused",            "type": "admin"},
    "0x" + w3.keccak(text="Unpaused(address)").hex():
        {"name": "Unpaused",          "type": "admin"},
}

UINT256_MAX = (2 ** 256) - 1


# token formatting function, pwede lipat another file

def format_amount(raw: int, decimals: int = 18, symbol: str | None = None) -> dict:
    """Format a raw wei/token amount.

    Args:
        raw:      The raw integer amount (in the smallest unit, e.g. wei).
        decimals: Token decimal places (default 18).
        symbol:   Override the display symbol. Falls back to CHAIN_CURRENCY
                  so native-token amounts auto-label correctly per chain.
    """
    divisor = Decimal(10 ** decimals)
    human = Decimal(raw) / divisor
    display_symbol = symbol if symbol is not None else CHAIN_CURRENCY
    return {
        "raw": raw,
        "human": float(human),
        "formatted": f"{human:.6f} {display_symbol}",
    }


def get_token_symbol(token_address: str) -> str:
    """Fetch the ERC-20 symbol for a contract address.
    Falls back to CHAIN_CURRENCY (native token) on any error,
    so plain ETH/DEV/etc. transfers still label correctly.
    """
    SYMBOL_ABI = [{
        "inputs": [], "name": "symbol",
        "outputs": [{"type": "string"}],
        "stateMutability": "view", "type": "function"
    }]
    try:
        token = w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=SYMBOL_ABI
        )
        return token.functions.symbol().call()
    except Exception:
        return CHAIN_CURRENCY


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
            symbol = get_token_symbol(contract_address)

            if selector in {"a9059cbb", "095ea7b3", "39509351"}:
                recipient = "0x" + data[34:74]
                amount_raw = int(data[74:138], 16)
                result["args"] = {
                    "recipient_or_spender": recipient,
                    "amount": format_amount(amount_raw, decimals, symbol),
                }

            elif selector == "23b872dd":
                from_addr = "0x" + data[34:74]
                to_addr = "0x" + data[98:138]
                amount_raw = int(data[138:202], 16)
                result["args"] = {
                    "from": from_addr,
                    "to": to_addr,
                    "amount": format_amount(amount_raw, decimals, symbol),
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
    native_before = int(sim_raw.get("sender_eth_before", "0"))
    native_after = int(sim_raw.get("sender_eth_after",  "0"))
    gas_used = sim_raw.get("gas_used")
    gas_price = sim_raw.get("gas_price") or w3.eth.gas_price

    decoded = decode_events(sim_raw.get("raw_logs", []),
                            checksum_to, checksum_sender)

    # Detect native token drain into contract
    contract_eth_before = int(sim_raw.get("contract_eth_before", "0"))
    contract_eth_after = int(sim_raw.get("contract_eth_after",  "0"))
    contract_eth_gained = max(0, contract_eth_after - contract_eth_before)

    return {
        "success":        sim_raw["success"],
        "reverted":       sim_raw["reverted"],
        "revert_reason":  sim_raw.get("revert_reason"),
        "gas_used":       gas_used,
        "gas_cost":       format_amount(gas_used * gas_price) if gas_used and gas_price else None,
        "events_emitted": decoded["events"],
        # ← specific danger signals
        "warnings":       decoded["warnings"],
        "value_flows":    decoded["value_flows"],     # ← who gained/lost what
        "warning_count":  decoded["warning_count"],
        "state_diff": {
            "sender_native_before":  format_amount(native_before),
            "sender_native_after":   format_amount(native_after),
            "sender_native_spent":   format_amount(max(0, native_before - native_after)),
            "contract_eth_before":   format_amount(contract_eth_before),
            "contract_eth_after":    format_amount(contract_eth_after),
            "contract_eth_gained":   format_amount(contract_eth_gained),
            "token_balance_before":  format_amount(real_token_balance, decimals),
            "changed_storage_slots": sim_raw.get("changed_slots", {}),
        },
        "opcode_flags":   sim_raw.get("opcode_flags", []),
        "simulation_note": sim_raw.get("simulation_note"),
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


def decode_events(raw_logs: list, contract_address: str, sender: str) -> dict:
    decimals = get_token_decimals(contract_address)
    symbol = get_token_symbol(contract_address)
    sender_lower = sender.lower()

    events = []
    warnings = []

    # Track value flows: address -> {received, sent}
    flows = {}

    def add_flow(addr, direction, amount_raw):
        addr = addr.lower()
        if addr not in flows:
            flows[addr] = {"received_raw": 0, "sent_raw": 0}
        if direction == "in":
            flows[addr]["received_raw"] += amount_raw
        else:
            flows[addr]["sent_raw"] += amount_raw

    for log in raw_logs:
        topics = log.get("topics", [])
        if not topics:
            continue

        topic0 = topics[0] if topics[0].startswith("0x") else "0x" + topics[0]
        known = KNOWN_TOPICS.get(topic0)

        try:
            if known and known["name"] == "Transfer":
                from_addr = ("0x" + topics[1][-40:]
                             ) if len(topics) > 1 else "unknown"
                to_addr = ("0x" + topics[2][-40:]
                           ) if len(topics) > 2 else "unknown"
                amount_raw = int(log["data"], 16) if log.get(
                    "data", "0x") != "0x" else 0

                add_flow(from_addr, "out", amount_raw)
                add_flow(to_addr,   "in",  amount_raw)

                # Warn if sender is losing tokens they didn't intend to transfer
                if from_addr.lower() == sender_lower:
                    warnings.append({
                        "type":    "token_leaving_sender",
                        "detail":  f"Tokens moving OUT of your wallet to {to_addr}",
                        "amount":  format_amount(amount_raw, decimals, symbol),
                    })

                events.append({
                    "event":  "Transfer",
                    "from":   from_addr,
                    "to":     to_addr,
                    "amount": format_amount(amount_raw, decimals, symbol),
                })

            elif known and known["name"] == "Approval":
                # Standard: owner in topics[1], spender in topics[2], amount in data
                # Non-standard: all args packed into data (1 topic only)
                if len(topics) >= 3:
                    owner = "0x" + topics[1][-40:]
                    spender = "0x" + topics[2][-40:]
                    amount_raw = int(log["data"], 16) if log.get(
                        "data", "0x") != "0x" else 0
                else:
                    # Decode from data: owner (32 bytes) + spender (32 bytes) + amount (32 bytes)
                    raw = log.get("data", "0x")[2:]  # strip 0x
                    if len(raw) >= 192:
                        owner = "0x" + raw[24:64]
                        spender = "0x" + raw[88:128]
                        amount_raw = int(raw[128:192], 16)
                    else:
                        # Only amount in data, owner/spender unknown
                        owner = "unknown"
                        spender = "unknown"
                        amount_raw = int(log["data"], 16) if log.get(
                            "data", "0x") != "0x" else 0

                is_unlimited = amount_raw >= UINT256_MAX
                if is_unlimited:
                    warnings.append({
                        "type":    "unlimited_approval",
                        "detail":  f"Spender {spender} approved for UNLIMITED tokens — can drain everything",
                        "spender": spender,
                    })
                events.append({
                    "event":        "Approval",
                    "owner":        owner,
                    "spender":      spender,
                    "amount":       format_amount(amount_raw, decimals, symbol),
                    "is_unlimited": is_unlimited,
                })

            elif known and known["name"] == "ApprovalForAll":
                owner = ("0x" + topics[1][-40:]
                         ) if len(topics) > 1 else "unknown"
                operator = ("0x" + topics[2][-40:]
                            ) if len(topics) > 2 else "unknown"
                approved = bool(int(log["data"], 16)) if log.get(
                    "data", "0x") != "0x" else False

                if approved:
                    warnings.append({
                        "type":     "approve_all_nft",
                        "detail":   f"Operator {operator} approved for ALL NFTs in collection",
                        "operator": operator,
                    })

                events.append({
                    "event":    "ApprovalForAll",
                    "owner":    owner,
                    "operator": operator,
                    "approved": approved,
                })

            elif known and known["name"] == "OwnershipTransferred":
                prev_owner = ("0x" + topics[1][-40:]
                              ) if len(topics) > 1 else "unknown"
                new_owner = ("0x" + topics[2][-40:]
                             ) if len(topics) > 2 else "unknown"
                warnings.append({
                    "type":      "ownership_transferred",
                    "detail":    f"Contract ownership transferred from {prev_owner} to {new_owner}",
                    "new_owner": new_owner,
                })
                events.append({"event": "OwnershipTransferred",
                              "from": prev_owner, "to": new_owner})

            elif known and known["name"] == "Upgraded":
                new_impl = ("0x" + topics[1][-40:]
                            ) if len(topics) > 1 else "unknown"
                warnings.append({
                    "type":   "contract_upgraded",
                    "detail": f"Proxy contract logic upgraded to new implementation: {new_impl}",
                })
                events.append(
                    {"event": "Upgraded", "new_implementation": new_impl})

            elif known and known["name"] in ("Deposit", "Withdrawal"):
                addr = ("0x" + topics[1][-40:]
                        ) if len(topics) > 1 else "unknown"
                amount_raw = int(log["data"], 16) if log.get(
                    "data", "0x") != "0x" else 0
                events.append({
                    "event":  known["name"],
                    "who":    addr,
                    "amount": format_amount(amount_raw, decimals, symbol),
                })

            elif known:
                # Known event type but no special handling — still record it
                events.append({
                    "event":  known["name"],
                    "type":   known["type"],
                    "topics": topics,
                    "data":   log.get("data", "0x"),
                })

            else:
                # Completely unknown — still useful for AI layer
                events.append({
                    "event":    "unknown",
                    "topic":    topic0,
                    "raw_data": log.get("data", "0x"),
                    "emitter":  log.get("address", "unknown"),
                })

        except Exception:
            events.append({"event": "decode_error", "raw": log})

    # Build human-readable flow summary
    flow_summary = []
    for addr, flow in flows.items():
        if flow["sent_raw"] > 0 or flow["received_raw"] > 0:
            flow_summary.append({
                "address":  addr,
                "sent":     format_amount(flow["sent_raw"],     decimals, symbol),
                "received": format_amount(flow["received_raw"], decimals, symbol),
                "is_sender": addr == sender_lower,
            })

    return {
        "events":       events,
        "warnings":     warnings,
        "value_flows":  flow_summary,
        "warning_count": len(warnings),
    }

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


def enrich_intent_from_events(intent: dict, events: list) -> dict:
    UINT256_MAX = (2 ** 256) - 1

    for event in events:
        if event.get("event") == "Approval":
            amount_raw = event.get("amount", {}).get("raw", 0)
            spender = event.get("spender", "unknown")
            is_unlimited = event.get(
                "is_unlimited") or amount_raw >= UINT256_MAX

            if is_unlimited:
                intent["intent_summary"] = (
                    f"⚠️ UNLIMITED APPROVAL detected via simulation. "
                    f"Spender {spender} will be able to drain ALL tokens from this contract. "
                    f"Original function selector 0x{intent.get('selector','?')} is non-standard."
                )
                intent["risk_hint"] = "unlimited_approval"
            else:
                intent["intent_summary"] = (
                    f"Approval detected via simulation. "
                    f"Grants {event.get('amount', {}).get('formatted', '?')} to {spender}."
                )
            break

        if event.get("event") == "ApprovalForAll" and event.get("approved"):
            intent["intent_summary"] = (
                f"⚠️ APPROVE ALL detected. "
                f"Operator {event.get('operator', 'unknown')} gains control over entire NFT collection."
            )
            intent["risk_hint"] = "approve_all"
            break

    return intent


def analyze_simulation(simulation: dict, sender: str, target: str, value: int) -> dict:
    # event-based warnings already decoded
    warnings = list(simulation.get("warnings", []))
    new_warns = []
    summary = []

    state = simulation.get("state_diff", {})
    opcodes = simulation.get("opcode_flags", [])
    slots = state.get("changed_storage_slots", {})
    events = simulation.get("events_emitted", [])

    if simulation.get("reverted"):
        new_warns.append({
            "type":   "reverted",
            "detail": f"Transaction will revert: {simulation.get('revert_reason', 'no reason given')}",
        })
        summary.append("Transaction will revert on-chain.")

    if "DELEGATECALL" in opcodes:
        new_warns.append({
            "type":   "delegatecall_executed",
            "detail": "Contract executed DELEGATECALL — it ran external code inside its own "
                      "storage context. If that external contract is malicious or upgradeable, "
                      "it can modify any state.",
        })
        summary.append("Contract used DELEGATECALL during execution.")

    if "SELFDESTRUCT" in opcodes:
        new_warns.append({
            "type":   "selfdestruct_executed",
            "detail": "SELFDESTRUCT opcode executed — contract destroyed itself and swept its ETH balance.",
        })
        summary.append("Contract self-destructed during simulation.")

    if "CREATE" in opcodes or "CREATE2" in opcodes:
        new_warns.append({
            "type":   "deploys_contract",
            "detail": "Transaction deploys a new child contract during execution.",
        })
        summary.append("Contract deployed a child contract.")

    if "CALLCODE" in opcodes:
        new_warns.append({
            "type":   "callcode_executed",
            "detail": "CALLCODE detected — deprecated opcode similar to DELEGATECALL, high risk.",
        })
        summary.append("Contract used deprecated CALLCODE opcode.")

    if slots:
        for slot_idx, change in slots.items():
            before = int(change["before"], 16)
            after = int(change["after"],  16)

            if before != 0 and after == 0:
                new_warns.append({
                    "type":   "storage_wiped",
                    "slot":   slot_idx,
                    "detail": f"Storage slot {slot_idx} was wiped (set to zero) — a balance or state was erased.",
                })
                summary.append(f"Storage slot {slot_idx} wiped to zero.")

            elif before == 0 and after != 0:
                summary.append(
                    f"Storage slot {slot_idx} written: {after} (0x{after:x})")

            else:
                new_warns.append({
                    "type":   "storage_modified",
                    "slot":   slot_idx,
                    "detail": f"Storage slot {slot_idx} changed from {before} to {after}.",
                })
                summary.append(
                    f"Storage slot {slot_idx} modified: {before} → {after}.")

    try:
        target_code = w3.eth.get_code(Web3.to_checksum_address(target))
        is_wallet = len(target_code) <= 2
    except Exception:
        is_wallet = False

    if is_wallet and value > 0 and simulation.get("success"):
        summary.append(
            f"Plain {CHAIN_CURRENCY} transfer — "
            f"sending {format_amount(value)['formatted']} directly to a wallet address. "
            f"No contract involved."
        )

    contract_gained = state.get("contract_eth_gained", {}).get("raw", 0)
    sender_spent = state.get("sender_native_spent", {}).get("raw", 0)
    gas_cost = simulation.get("gas_cost") or {}
    gas_raw = gas_cost.get("raw", 0)
    net_loss = sender_spent - gas_raw

    if net_loss > 0 and not is_wallet:
        if contract_gained > 0:
            new_warns.append({
                "type":   "eth_sent_to_contract",
                "detail": f"{format_amount(net_loss)['formatted']} sent to contract and retained — not forwarded to any recipient.",
                "amount": format_amount(net_loss),
            })
            summary.append(
                f"Contract retained {format_amount(net_loss)['formatted']} of {CHAIN_CURRENCY}.")
        else:
            new_warns.append({
                "type":   "native_value_sent",
                "detail": f"{format_amount(net_loss)['formatted']} of {CHAIN_CURRENCY} sent — contract forwarded it to a recipient.",
                "amount": format_amount(net_loss),
            })
            summary.append(
                f"Sender paid {format_amount(net_loss)['formatted']} in {CHAIN_CURRENCY} (forwarded by contract to recipient).")

    for flow in simulation.get("value_flows", []):
        if flow.get("is_sender") and flow["sent"]["raw"] > 0:
            summary.append(
                f"Your wallet sent {flow['sent']['formatted']} in tokens.")
        elif not flow.get("is_sender") and flow["received"]["raw"] > 0:
            summary.append(
                f"{flow['address'][:10]}... received {flow['received']['formatted']}.")

    if not events and not slots and not opcodes and simulation.get("success") and not is_wallet:
        summary.append(
            "No state changes detected — transaction has no observable on-chain effect.")

    all_warnings = warnings + new_warns
    high_risk_types = {
        "unlimited_approval", "approve_all_nft", "selfdestruct_executed",
        "storage_wiped", "eth_sent_to_contract", "delegatecall_executed",
        "callcode_executed", "token_leaving_sender",
    }
    is_high_risk = any(w["type"] in high_risk_types for w in all_warnings)

    return {
        "warnings":      all_warnings,
        "warning_count": len(all_warnings),
        "summary":       summary,
        "high_risk":     is_high_risk,
        "opcode_flags":  opcodes,
    }


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


def save_analysis_to_db(
    sender: str,
    target: str,
    simulation: dict,
    analysis: dict,
    pipeline: dict,
    transaction_hash: str | None = None,
) -> dict:
    """Persist analysis payloads into MySQL-backed tables.

    This uses SQLModel objects in models.analysis and models.wallet.
    """
    if transaction_hash is None:
        transaction_hash = hashlib.sha256(
            f"{sender}|{target}|{simulation.get('simulation_id','')}|{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()

    sim_summary = "; ".join(analysis.get("summary", []))
    ai_summary = pipeline.get("transaction_intent") or ""
    warning_text = "; ".join([w.get("detail", "") for w in analysis.get("warnings", [])])
    trust_score = 0

    # simple trust score inference
    if pipeline.get("rag_status") == "error":
        trust_score = 0
    elif analysis.get("high_risk"):
        trust_score = 20
    elif pipeline.get("risk_tier") == "LOW":
        trust_score = 90
    else:
        trust_score = 50

    try:
        with Session(engine) as session:
            # Ensure a user transaction is stored for cross-table cleanup and listing
            user_tx = UserTransaction(
                transaction_hash=transaction_hash,
                wallet_address=sender,
                address_destination=target,
                chain_id=str(w3.eth.chain_id),
                contract_address=target,
                gasUsed=str(simulation.get("gas_cost", {}).get("raw", 0)),
                gasCost=str(simulation.get("gas_cost", {}).get("human", "0")),
                method_called=analysis.get("summary", ["unknown"])[0][:100],
                timestamp=datetime.now(timezone.utc),
                status=0,
            )
            session.add(user_tx)

            sim_row = SimulationResult(
                transaction_hash=transaction_hash,
                simulation_summary=sim_summary[:255],
            )
            session.add(sim_row)

            ai_row = AIAnalysis(
                transaction_hash=transaction_hash,
                ai_summary=ai_summary[:255],
                recommendation=str(pipeline.get("standard_baseline", ""))[:255],
                warning=warning_text[:255],
                trust_score=int(trust_score),
            )
            session.add(ai_row)

            session.commit()

        return {"saved": True, "transaction_hash": transaction_hash}

    except Exception as exc:
        return {"saved": False, "error": str(exc), "transaction_hash": transaction_hash}


# main endpoints

@app.get("/")
async def root():
    return {"message": "A.E.G.I.S. Backend Online", "docs": "/docs"}


@app.post("/analyze-full")
async def analyze_full(tx_payload: TransactionRequest):
    sender = tx_payload.sender
    target = tx_payload.to
    data = tx_payload.data
    value = tx_payload.value

    simulation = simulate_with_hardhat(sender, target, data, value)

    analysis = analyze_simulation(simulation, sender, target, value)

    history = scan_event_history(target)

    registry = check_trust_registry(target)

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

    # transaction_hash is synthetic (no real chain tx yet) and used for local persistence keys
    simulated_tx_hash = hashlib.sha256(
        f"{sender}|{target}|{data}|{value}|{datetime.now(timezone.utc).isoformat()}".encode()
    ).hexdigest()

    sim_output = {
        "transaction_hash": simulated_tx_hash,
        "target_address": target,
        "sender_address": sender,
        "preflight":      preflight,
        "simulation":     simulation,
        "analysis":       analysis,
        "history":        history,
        "trust":          {"registry": registry},
    }

    loop = asyncio.get_event_loop()
    pipeline = await loop.run_in_executor(None, run_pipeline, "tx", sim_output)

    if "error" in pipeline:
        error_response = {
            **sim_output,
            "pipeline": {
                "risk_tier":              None,
                "rag_status":             "error",
                "rag_error":              pipeline["error"],
                "transaction_intent":     None,
                "standard_baseline":      None,
                "vulnerability_evidence": [],
                "scam_evidence":          [],
                "llm_context":            None,
                "latency_ms":             None,
            }
        }
        save_result = save_analysis_to_db(
            sender, target, simulation, analysis, pipeline,
            transaction_hash=simulated_tx_hash,
        )
        error_response["storage"] = save_result
        return error_response

    save_result = save_analysis_to_db(
        sender, target, simulation, analysis, pipeline,
        transaction_hash=simulated_tx_hash,
    )

    final_response = {
        **sim_output,
        "pipeline": pipeline,
        "storage":  save_result,
    }

    # Layer 3: AI verdict from AI_verdict/app/main.py
    try:
        ai_input = {
            "rag": final_response.get("pipeline", {}),
            "simulation": final_response.get("simulation", {}),
        }
        ai_output = ai_analyze_from_sources(ai_input)
        final_response["ai_verdict"] = ai_output
    except Exception as exc:
        final_response["ai_verdict"] = {
            "error": "ai_analysis_failed",
            "error_detail": str(exc),
        }

    return final_response


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
# {"approved": 2, "pending": 1, "rejected": 0} status
# {} risk
# query.filter(UserTransaction.status == )
# endpoint def get_Transactions_by_filter(walletaddress, session, statusfilter, riskfilter)
# query.filter(blahblah.status == (statusfilter == "All"? {0,1,2}: statusfilter))


@app.get("/transactions/filter")
def get_transactions_by_filter(
    status_filter: int,  # -1 for all
    risk_filter: int,  # -1 for all
    wallet_address: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
):

    query = session.query(UserTransaction, UserThreatRecord).join(UserThreatRecord,
                                                                  UserThreatRecord.transaction_hash == UserTransaction.transaction_hash,
                                                                  isouter=True).filter(UserTransaction.wallet_address == wallet_address)

    if status_filter != -1:
        query = query.filter(UserTransaction.status == status_filter)

    if risk_filter != -1:
        query = query.filter(UserThreatRecord.risk_level == risk_filter)

    results = query.order_by(UserTransaction.timestamp.desc()).all()

    return results


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
            UserTransaction.wallet_address == wallet_address,
            UserTransaction.status == 2)
    ).one()
    safe_transactions = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address,
            UserTransaction.status == 1)
    ).one()
    total_scanned = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address)
    ).one()
    pending = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address,
            UserTransaction.status == 0)
    ).one()
    high_threats_blocked = session.exec(
        select(func.count()).select_from(UserTransaction).join(
            UserThreatRecord,
            UserTransaction.transaction_hash == UserThreatRecord.transaction_hash
        ).where(
            UserTransaction.wallet_address == wallet_address,
            UserThreatRecord.risk_level >= 2)
    ).one()
    protection_rate = 100
    if threats_blocked > 0:
        protection_rate -= ((high_threats_blocked / threats_blocked) * 100)
    return {
        "threats_blocked":   threats_blocked,
        "safe_transactions": safe_transactions,
        "total_scanned":     total_scanned,
        "pending":           pending,
        "protection_rate":   round(protection_rate, 2),
    }


@app.get("/stats/L7D/{wallet_address}")
def get_stats_L7D(wallet_address: str, session: Session = Depends(get_session)):
    wallet = session.get(WalletUser, wallet_address)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    L7D = datetime.now(timezone.utc) - timedelta(days=7)
    threats_blocked_L7D = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address,
            UserTransaction.status == 2,
            UserTransaction.timestamp >= L7D)
    ).one()
    threats_blocked = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address,
            UserTransaction.status == 2)
    ).one()
    transactions_approved = session.exec(
        select(func.count()).where(
            UserTransaction.wallet_address == wallet_address,
            UserTransaction.status == 1,
            UserTransaction.timestamp >= L7D)
    ).one()
    high_threats_blocked = session.exec(
        select(func.count()).select_from(UserTransaction).join(
            UserThreatRecord,
            UserTransaction.transaction_hash == UserThreatRecord.transaction_hash
        ).where(
            UserTransaction.wallet_address == wallet_address,
            UserTransaction.status == 0,
            UserThreatRecord.risk_level >= 2)
    ).one()

    protection_rate = 100
    if threats_blocked > 0:
        protection_rate -= ((high_threats_blocked / threats_blocked) * 100)
    return {
        "threats_blocked":   threats_blocked_L7D,
        "transactions_approved": transactions_approved,
        "protection_rate":   round(protection_rate, 2)
    }


@app.get("/alerts/recent/{wallet_address}")
def get_recent_alerts(wallet_address: str, session: Session = Depends(get_session)):
    try:
        limit = 3
        wallet = session.get(WalletUser, wallet_address)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        txData = (select(UserTransaction.transaction_hash,
                         UserThreatRecord.risk_level,
                         UserThreatRecord.threat_description,
                         UserTransaction.timestamp)
                  .join(UserThreatRecord, UserTransaction.transaction_hash == UserThreatRecord.transaction_hash)
                  .where(UserTransaction.wallet_address == wallet_address,
                         UserTransaction.status == 0,
                         UserThreatRecord.risk_level >= 2)
                  .order_by(UserTransaction.timestamp.desc()).limit(limit))

        results = session.exec(txData).all()

        alerts = []

        now = datetime.now(timezone.utc)

        for tx_hash, risk_level, description, timestamp in results:
            if risk_level == 5:
                severity = "UNKNOWN"
            elif risk_level == 4:
                severity = "CRITICAL"
            elif risk_level >= 2:
                severity = "WARNING"

            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            delta = now - timestamp
            if delta.days >= 1:
                timeAgo = f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
            elif delta.seconds >= 3600:
                hours = delta.seconds // 3600
                timeAgo = f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif delta.seconds >= 60:
                minutes = delta.seconds // 60
                timeAgo = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                timeAgo = "Just now"

            alerts.append({
                "title": description,
                "severity": severity,
                "timeAgo": timeAgo
            })
        return alerts
    except Exception as e:
        print("Eror in alerts:", e)
        return {"alerts": [], "error": str(e)}


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
