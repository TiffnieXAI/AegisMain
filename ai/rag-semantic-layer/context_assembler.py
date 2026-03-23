"""
A.E.G.I.S. — LLM Verdict Context Assembler
Utility module: formats RAG results into Structured Context Blocks.

Can be imported by api.py or used standalone for testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data classes (plain Python — no FastAPI/Pydantic dependency here)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EvidenceItem:
    text:       str
    source:     str
    confidence: float
    severity:   Optional[str] = None


@dataclass
class RAGResult:
    transaction_intent:     str
    standard_baseline:      Optional[EvidenceItem]      = None
    vulnerability_evidence: list[EvidenceItem]          = field(default_factory=list)
    status:                 str                         = "no_match"   # "match_found" | "no_match"


# ─────────────────────────────────────────────────────────────────────────────
# Core assembler
# ─────────────────────────────────────────────────────────────────────────────

def build_verdict_context(result: RAGResult) -> str:
    """
    Formats RAG results into a Structured Context Block for the LLM Verdict Engine.

    Spec:
        [CONTEXT START]
        [STANDARD_BEHAVIOR]: {text}
        [HISTORICAL_EXPLOIT_MATCH]: {text} | SEVERITY: {severity}
        [SEARCH_RELEVANCE]: {score}
        [CONTEXT END]

    Rules:
      - If no standard baseline exists, emits a 'Not found' placeholder.
      - If no vulnerability evidence exists, emits a 'Not found' placeholder.
      - SEARCH_RELEVANCE always immediately follows its parent block.
      - Severity is upper-cased; defaults to 'UNKNOWN' if not tagged.
    """
    if result.status == "no_match":
        return (
            "[CONTEXT START]\n"
            "[STATUS]: No specific match found — confidence below threshold.\n"
            "[CONTEXT END]"
        )

    lines = ["[CONTEXT START]"]

    # ── Standard baseline ────────────────────────────────────────────────────
    if result.standard_baseline:
        sb = result.standard_baseline
        lines.append(f"[STANDARD_BEHAVIOR]: {sb.text.strip()}")
        lines.append(f"[SEARCH_RELEVANCE]: {sb.confidence:.4f}")
    else:
        lines.append("[STANDARD_BEHAVIOR]: No standard baseline found for this function.")
        lines.append("[SEARCH_RELEVANCE]: N/A")

    # ── Historical exploit evidence ───────────────────────────────────────────
    if result.vulnerability_evidence:
        for vuln in result.vulnerability_evidence:
            severity = (vuln.severity or "unknown").upper()
            lines.append(
                f"[HISTORICAL_EXPLOIT_MATCH]: {vuln.text.strip()} | SEVERITY: {severity}"
            )
            lines.append(f"[SEARCH_RELEVANCE]: {vuln.confidence:.4f}")
    else:
        lines.append("[HISTORICAL_EXPLOIT_MATCH]: No historical exploit pattern matched.")
        lines.append("[SEARCH_RELEVANCE]: N/A")

    lines.append("[CONTEXT END]")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Convenience wrapper (used by api.py to bridge Pydantic → dataclass)
# ─────────────────────────────────────────────────────────────────────────────

def from_api_response(
    intent: str,
    standard_baseline,           # EvidenceMatch | None  (Pydantic model from api.py)
    vulnerability_evidence: list, # list[EvidenceMatch]
    status: str,
) -> str:
    """
    Bridge function: converts api.py Pydantic models into RAGResult
    and returns the formatted context string.
    """
    std = None
    if standard_baseline:
        std = EvidenceItem(
            text=standard_baseline.text,
            source=standard_baseline.source,
            confidence=standard_baseline.match_confidence,
        )

    vulns = [
        EvidenceItem(
            text=v.text,
            source=v.source,
            confidence=v.match_confidence,
            severity=v.severity,
        )
        for v in vulnerability_evidence
    ]

    result = RAGResult(
        transaction_intent=intent,
        standard_baseline=std,
        vulnerability_evidence=vulns,
        status=status,
    )
    return build_verdict_context(result)


# ─────────────────────────────────────────────────────────────────────────────
# Self-tests
# ─────────────────────────────────────────────────────────────────────────────

def _run_tests():
    print("─" * 60)
    print("TEST 1: Full match (standard + 2 vulns)")
    print("─" * 60)
    result = RAGResult(
        transaction_intent="User is calling setApprovalForAll to an unknown address",
        status="match_found",
        standard_baseline=EvidenceItem(
            text="setApprovalForAll(address operator, bool approved) — Enables or disables approval for a third party ('operator') to manage all of the caller's assets.",
            source="IERC721 Interface Standard",
            confidence=0.8912,
        ),
        vulnerability_evidence=[
            EvidenceItem(
                text="Critical: unrestricted setApprovalForAll allows malicious operator to drain entire NFT portfolio without per-token consent. Observed in 2023 OpenSea exploit pattern.",
                source="OpenZeppelin v5.6 Audit",
                confidence=0.7641,
                severity="critical",
            ),
            EvidenceItem(
                text="High: missing operator allowlist check in setApprovalForAll enables phishing-driven mass approvals to attacker-controlled contracts.",
                source="OpenZeppelin v5.5 Audit",
                confidence=0.7120,
                severity="high",
            ),
        ],
    )
    print(build_verdict_context(result))

    print("\n" + "─" * 60)
    print("TEST 2: No match (below confidence threshold)")
    print("─" * 60)
    no_match = RAGResult(
        transaction_intent="User is calling a completely novel obscure function",
        status="no_match",
    )
    print(build_verdict_context(no_match))

    print("\n" + "─" * 60)
    print("TEST 3: Standard match only (no vuln hits)")
    print("─" * 60)
    partial = RAGResult(
        transaction_intent="User calls transfer(address to, uint256 amount)",
        status="match_found",
        standard_baseline=EvidenceItem(
            text="transfer(address to, uint256 value) — Moves value tokens from the caller's account to the to account.",
            source="IERC20 Interface Standard",
            confidence=0.9305,
        ),
        vulnerability_evidence=[],
    )
    print(build_verdict_context(partial))


if __name__ == "__main__":
    _run_tests()
