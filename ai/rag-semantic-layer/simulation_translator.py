"""
A.E.G.I.S. — Simulation Layer Translator v2
Converts the full py-evm/Hardhat simulation output into a
natural language SimulationReport for POST /analyze-intent.

Handles both safe and unsafe simulation responses.

Usage:
    from simulation_translator import build_simulation_report, assess_risk_level
    report = build_simulation_report(simulation_output)
"""

from __future__ import annotations

import json
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _short_addr(addr: str) -> str:
    if addr and len(addr) > 12:
        return f"{addr[:6]}...{addr[-4:]}"
    return addr or "unknown"


# Plain transfer gas limit — 21000 is the exact cost of a native transfer
# anything above means contract interaction happened
PLAIN_TRANSFER_GAS = 21000


# ─────────────────────────────────────────────────────────────────────────────
# Risk signal extractor
# ─────────────────────────────────────────────────────────────────────────────

def _extract_signals(sim_output: dict) -> list[str]:
    signals  = []

    sim      = sim_output.get("simulation", {})
    analysis = sim_output.get("analysis", {})
    preflight= sim_output.get("preflight", {})
    trust    = sim_output.get("trust", {})
    history  = sim_output.get("history", {})
    target   = sim_output.get("target_address", "unknown")
    sender   = sim_output.get("sender_address", "unknown")

    gas_used      = sim.get("gas_used", 0)
    warning_count = sim.get("warning_count", 0)
    high_risk     = analysis.get("high_risk", False)
    reverted      = sim.get("reverted", False)
    events        = sim.get("events_emitted", [])
    warnings      = sim.get("warnings", [])
    summary       = analysis.get("summary", [])
    opcode_flags  = sim.get("opcode_flags", [])
    value_flows   = sim.get("value_flows", [])
    state_diff    = sim.get("state_diff", {})
    registry      = trust.get("registry", {})

    # ── SAFE path: plain native transfer, no events, no warnings ─────────────
    is_plain_transfer = (
        gas_used <= PLAIN_TRANSFER_GAS
        and not events
        and not warnings
        and not high_risk
        and not reverted
    )

    if is_plain_transfer:
        amount = state_diff.get("contract_eth_gained", {}).get("formatted", "unknown amount")
        signals.append(
            f"Plain native token transfer of {amount} from "
            f"{_short_addr(sender)} to {_short_addr(target)}. "
            f"No contract interaction, no events emitted, no warnings. "
            f"Read-only value transfer — low risk."
        )
        return signals  # return early, no need to check further

    # ── Event analysis ────────────────────────────────────────────────────────
    for event in events:
        event_name = event.get("event", "")

        if event_name == "Approval":
            if event.get("is_unlimited"):
                spender = event.get("spender", "unknown")
                signals.append(
                    f"UNLIMITED token approval granted — spender "
                    f"{_short_addr(spender)} has been approved for "
                    f"type(uint256).max tokens (unlimited spend allowance). "
                    f"This allows the spender to drain the entire token balance "
                    f"at any time without further consent from the owner."
                )
            else:
                amount  = event.get("amount", {}).get("formatted", "unknown")
                spender = event.get("spender", "unknown")
                signals.append(
                    f"Token approval granted to {_short_addr(spender)} "
                    f"for {amount}."
                )

        elif event_name == "Transfer":
            frm = event.get("from", "unknown")
            to  = event.get("to", "unknown")
            amt = event.get("amount", {}).get("formatted", "unknown")
            if frm.lower() == sender.lower():
                signals.append(
                    f"Token transfer of {amt} leaving sender wallet "
                    f"{_short_addr(frm)} to {_short_addr(to)}."
                )

        elif event_name == "ApprovalForAll":
            operator = event.get("operator", "unknown")
            approved = event.get("approved", False)
            if approved:
                signals.append(
                    f"setApprovalForAll granted to operator "
                    f"{_short_addr(operator)} — unlimited control over "
                    f"ALL NFTs in the collection without per-token consent."
                )

    # ── Simulation warnings ───────────────────────────────────────────────────
    for warning in warnings:
        wtype  = warning.get("type", "")
        detail = warning.get("detail", "")

        if wtype == "unlimited_approval":
            signals.append(
                f"Simulation engine warning: {detail}."
            )
        elif wtype == "high_value_transfer":
            signals.append(
                f"High value transfer warning: {detail}."
            )
        elif detail:
            signals.append(f"Warning detected: {detail}.")

    # ── Value flows ───────────────────────────────────────────────────────────
    for flow in value_flows:
        direction = flow.get("direction", "")
        amount    = flow.get("amount", {}).get("formatted", "unknown")
        if direction == "out":
            signals.append(
                f"Value flow: {amount} leaving the user wallet."
            )

    # ── Opcode flags ──────────────────────────────────────────────────────────
    for flag in opcode_flags:
        signals.append(f"Dangerous opcode detected: {flag}.")

    # ── Registry / Trust ──────────────────────────────────────────────────────
    if not registry.get("is_verified_safe"):
        signals.append(
            f"Contract {_short_addr(target)} has UNKNOWN registry status — "
            f"not a verified safe entity, no on-chain reputation established."
        )

    if registry.get("is_flagged"):
        signals.append(
            f"FLAGGED: Contract {_short_addr(target)} is blacklisted "
            f"in the Truth Registry Smart Contract."
        )

    # ── Interaction history ───────────────────────────────────────────────────
    past_approvals = history.get("past_approvals", 0)
    past_transfers = history.get("past_transfers", 0)

    if past_approvals == 0 and past_transfers == 0 and not is_plain_transfer:
        signals.append(
            f"Zero interaction history — contract {_short_addr(target)} "
            f"has no recorded past transfers or approvals. "
            f"Newly deployed or never interacted with contracts carry "
            f"higher risk of being phishing or scam deployments."
        )

    # ── High risk flag ────────────────────────────────────────────────────────
    if high_risk:
        signals.append(
            f"Simulation engine classified this transaction as HIGH RISK."
        )

    # ── Revert ────────────────────────────────────────────────────────────────
    if reverted:
        reason = sim.get("revert_reason", "unknown reason")
        signals.append(
            f"Transaction reverted during simulation: {reason}."
        )

    # ── Summary passthrough (from simulation layer analysis) ──────────────────
    for s in summary:
        if s and s not in " ".join(signals):
            signals.append(s)

    # ── Fallback ──────────────────────────────────────────────────────────────
    if not signals:
        signals.append(
            f"Transaction from {_short_addr(sender)} to "
            f"{_short_addr(target)} — no specific risk signals detected."
        )

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# Pre-flight risk tier (instant, no RAG needed)
# ─────────────────────────────────────────────────────────────────────────────

def assess_risk_level(sim_output: dict) -> str:
    """
    Instant pre-flight risk tier before RAG analysis.
    Returns: CRITICAL | HIGH | MEDIUM | LOW
    """
    sim      = sim_output.get("simulation", {})
    analysis = sim_output.get("analysis", {})
    events   = sim.get("events_emitted", [])
    warnings = sim.get("warnings", [])
    gas_used = sim.get("gas_used", 0)
    high_risk= analysis.get("high_risk", False)
    registry = sim_output.get("trust", {}).get("registry", {})

    # CRITICAL: unlimited approval
    for event in events:
        if event.get("event") == "Approval" and event.get("is_unlimited"):
            return "CRITICAL"
        if event.get("event") == "ApprovalForAll" and event.get("approved"):
            return "CRITICAL"

    # CRITICAL: flagged in registry
    if registry.get("is_flagged"):
        return "CRITICAL"

    # HIGH: simulation says high risk
    if high_risk:
        return "HIGH"

    # HIGH: any warnings present
    if warnings:
        return "HIGH"

    # MEDIUM: contract interaction but no warnings
    if gas_used > PLAIN_TRANSFER_GAS:
        return "MEDIUM"

    # LOW: plain transfer, no events, no warnings
    return "LOW"


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def build_simulation_report(sim_output: dict) -> dict:
    """
    Converts full simulation layer JSON into an AEGIS SimulationReport
    ready to POST to /analyze-intent.

    Returns:
        {
            "transaction_intent": str,
            "chain_id":           str,
            "contract":           str,
            "caller":             str,
        }
    """
    signals = _extract_signals(sim_output)

    return {
        "transaction_intent": " ".join(signals),
        "chain_id":  "polkadot",
        "contract":  sim_output.get("target_address", ""),
        "caller":    sim_output.get("sender_address", ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────

UNSAFE_SAMPLE = {
    "target_address": "0xeE5D7Ee56E2085EAE248dD0ACfbf736A1722fA7B",
    "sender_address": "0x9Fa19B5662DDecc1B6fd3183B0dC08ADb17a42d4",
    "preflight": {"sender_tx_count": 18, "sender_is_active": True},
    "simulation": {
        "success": True, "reverted": False, "revert_reason": None,
        "gas_used": 50865,
        "events_emitted": [{
            "event": "Approval",
            "owner":   "0xee5d7ee56e2085eae248dd0acfbf736a1722fa7b",
            "spender": "0x9fa19b5662ddecc1b6fd3183b0dc08adb17a42d4",
            "amount":  {"raw": 1.157920892373162e+77, "formatted": "115792089237316195423570985 DEV"},
            "is_unlimited": True
        }],
        "warnings": [{
            "type":    "unlimited_approval",
            "detail":  "Spender 0x9fa19b5662ddecc1b6fd3183b0dc08adb17a42d4 approved for UNLIMITED tokens — can drain everything",
            "spender": "0x9fa19b5662ddecc1b6fd3183b0dc08adb17a42d4"
        }],
        "warning_count": 1, "value_flows": [], "opcode_flags": [],
        "state_diff": {}, "simulation_note": "Hardhat fork."
    },
    "analysis": {"warnings": [], "warning_count": 1, "summary": [], "high_risk": True, "opcode_flags": []},
    "history":  {"past_transfers": 0, "past_approvals": 0},
    "trust":    {"registry": {"status": "Unknown", "is_flagged": False, "is_verified_safe": False}}
}

SAFE_SAMPLE = {
    "target_address": "0xB9A29b2DBEc411D290F382b73231512dd7323f63",
    "sender_address": "0x9Fa19B5662DDecc1B6fd3183B0dC08ADb17a42d4",
    "preflight": {"sender_tx_count": 18, "sender_is_active": True},
    "simulation": {
        "success": True, "reverted": False, "revert_reason": None,
        "gas_used": 21000,
        "events_emitted": [], "warnings": [], "warning_count": 0,
        "value_flows": [], "opcode_flags": [],
        "state_diff": {
            "contract_eth_gained": {"formatted": "0.100000 DEV"}
        },
        "simulation_note": "Hardhat fork."
    },
    "analysis": {
        "warnings": [], "warning_count": 0,
        "summary": ["Plain DEV transfer — sending 0.100000 DEV directly to a wallet address. No contract involved."],
        "high_risk": False, "opcode_flags": []
    },
    "history": {"past_transfers": 0, "past_approvals": 0},
    "trust":   {"registry": {"status": "Unknown", "is_flagged": False, "is_verified_safe": False}}
}


if __name__ == "__main__":
    for label, sample in [("UNSAFE", UNSAFE_SAMPLE), ("SAFE", SAFE_SAMPLE)]:
        report     = build_simulation_report(sample)
        risk_level = assess_risk_level(sample)

        print("=" * 65)
        print(f"SAMPLE: {label}")
        print("=" * 65)
        print(f"RISK TIER : {risk_level}")
        print(f"INTENT    : {report['transaction_intent']}")
        print()
