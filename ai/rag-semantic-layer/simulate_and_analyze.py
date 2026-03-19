"""
A.E.G.I.S. — Full Pipeline (Steps 1-5)
Simulation → Translator → RAG → JSON output for LLM Verdict Engine

Usage:
    py simulate_and_analyze.py
"""

from __future__ import annotations

import argparse
import json
import httpx
from simulation_translator import build_simulation_report, assess_risk_level

RAG_API = "http://localhost:8000/analyze-intent"

# ─────────────────────────────────────────────────────────────────────────────
# Pipeline — Steps 1 to 5
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(label: str, simulation: dict) -> dict:
    """
    Runs Steps 1-5 and returns a structured JSON payload
    ready for the LLM Verdict Engine.
    """

    # ── Step 1: Pre-flight risk tier ──────────────────────────────────────
    risk_tier = assess_risk_level(simulation)

    # ── Step 2: Fast-track LOW risk ───────────────────────────────────────
    if risk_tier == "LOW":
        payload = {
            "risk_tier":            "LOW",
            "rag_status":           "skipped",
            "transaction_intent":   "Plain value transfer — no contract interaction.",
            "contract":             simulation.get("target_address"),
            "caller":               simulation.get("sender_address"),
            "standard_baseline":    None,
            "vulnerability_evidence": [],
            "scam_evidence":        [],
            "llm_context":          None,
            "latency_ms":           0,
        }
        return payload

    # ── Step 3: Build intent string ───────────────────────────────────────
    report = build_simulation_report(simulation)

    # ── Step 4: Send to RAG ───────────────────────────────────────────────
    try:
        response = httpx.post(RAG_API, json=report, timeout=15)
        rag      = response.json()
    except httpx.ConnectError:
        return {"error": "api.py is not running. Start it with: py api.py"}

    # ── Step 5: Assemble verdict payload for LLM ─────────────────────────
    return{
        "risk_tier":              risk_tier,
        "rag_status":             rag.get("status"),
        "transaction_intent":     rag.get("transaction_intent"),
        "contract":               simulation.get("target_address"),
        "caller":                 simulation.get("sender_address"),
        "standard_baseline":      rag.get("standard_baseline"),
        "vulnerability_evidence": rag.get("vulnerability_evidence", []),
        "scam_evidence":          rag.get("scam_evidence", []),
        "llm_context":            rag.get("llm_context"),
        "latency_ms":             rag.get("latency_ms"),
    }
