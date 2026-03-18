"""
A.E.G.I.S. — FastAPI Semantic Analysis Backend
POST /analyze-intent  → structured RAG response in < 500 ms
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Optional

import chromadb
from chromadb.config import Settings
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

log = logging.getLogger("aegis.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Configuration
CHROMA_PATH        = "./aegis_db"
COLLECTION_NAME    = "library_of_truth"
EMBED_MODEL        = "all-MiniLM-L6-v2"
MIN_CONFIDENCE     = 0.63          # below this → "No specific match found"
N_SCAM_HITS        = 2
N_STANDARD_HITS    = 1
N_VULN_HITS        = 2

#  Shared singletons (initialised in lifespan) 
_embedder:   SentenceTransformer | None = None
_collection: chromadb.Collection | None = None


# Lifespan — warm-up on startup, clean-up on shutdown
# ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _embedder, _collection

    log.info("⚙  Loading embedding model: %s", EMBED_MODEL)
    _embedder = SentenceTransformer(EMBED_MODEL)

    log.info("⚙  Connecting to ChromaDB at: %s", CHROMA_PATH)
    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False),
    )
    _collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    log.info("✅ Ready — collection has %d documents.", _collection.count())
    yield
    log.info("🛑 Shutting down A.E.G.I.S. backend.")


# FastAPI app
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="A.E.G.I.S. RAG Semantic Layer API",
    description="Semantic RAG Layer for analyzing transaction intents.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────

# This is the raw input from the Polkadot extension simulation layer, which may be noisy and unstructured. The analysis engine will process this and attempt to match it against known patterns in the RAG knowledge base.
class SimulationReport(BaseModel):
    """Raw transaction intent from the Polkadot extension simulation layer."""
    transaction_intent: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        example="User is calling setApprovalForAll to an unknown address",
    )
    chain_id:   Optional[str]  = Field(None, example="polkadot")
    contract:   Optional[str]  = Field(None, example="0xdead...beef")
    caller:     Optional[str]  = Field(None, example="0xabc...123")

# This pulls the evidence as to how the analysis engine reached its decision, which the LLM Verdict Engine will use as context for final classification and explanation generation.
class EvidenceMatch(BaseModel):
    text:             str
    source:           str
    match_confidence: float
    severity:         Optional[str] = None

# The structured output of the analysis engine, which includes the match status, the top evidence found, and a pre-formatted context block for the LLM Verdict Engine.
class AnalysisResponse(BaseModel):
    status:                 str                        # "match_found" | "no_match"
    transaction_intent:     str
    standard_baseline:      Optional[EvidenceMatch]    # Top standard match
    vulnerability_evidence: list[EvidenceMatch]        # Top-2 audit matches
    scam_evidence:          list[EvidenceMatch]
    latency_ms:             float

    # Pre-formatted context block ready for the *LLM Verdict Engine*
    llm_context:            Optional[str] = None


# Core helpers
# ─────────────────────────────────────────────────────────────────────────────

def _embed(text: str) -> list[float]:
    """Encode query text to a unit-normalised vector (fast, cached at call-site)."""
    return _embedder.encode(text, normalize_embeddings=True).tolist()  # type: ignore[union-attr]


def _chroma_distance_to_confidence(distance: float) -> float:
    """
    ChromaDB cosine space returns *distance* (0 = identical, 2 = opposite).
    Convert to a 0–1 confidence score: confidence = 1 - (distance / 2).
    """
    return round(max(0.0, 1.0 - distance / 2.0), 4)


def _query_by_category(
    query_embedding: list[float],
    category: str,
    n_results: int,
) -> list[dict]:
    """
    Synchronous ChromaDB query filtered by metadata category.
    Returns list of {text, source, severity, confidence}.
    """
    try:
        results = _collection.query(  # type: ignore[union-attr]
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"category": {"$eq": category}},
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        log.error("ChromaDB query failed for category=%s: %s", category, exc)
        return []

    hits = []
    docs      = results.get("documents", [[]])[0]
    metas     = results.get("metadatas",  [[]])[0]
    distances = results.get("distances",  [[]])[0]

    for doc, meta, dist in zip(docs, metas, distances):
        hits.append({
            "text":       doc,
            "source":     meta.get("source", "unknown"),
            "severity":   meta.get("severity"),
            "confidence": _chroma_distance_to_confidence(dist),
        })

    return hits



# Context assembler (FOR LLM VERDICT ENGINE)
# ─────────────────────────────────────────────────────────────────────────────

def build_llm_context(
    standard: Optional[EvidenceMatch],
    vulnerabilities: list[EvidenceMatch],
    scam_matches: list[EvidenceMatch] = [],
) -> str:
    lines = ["[CONTEXT START]"]
 
    if standard:
        lines.append(f"[STANDARD_BEHAVIOR]: {standard.text}")
        lines.append(f"[SEARCH_RELEVANCE]: {standard.match_confidence}")
    else:
        lines.append("[STANDARD_BEHAVIOR]: No standard baseline found.")
 
    for vuln in vulnerabilities:
        severity = vuln.severity.upper() if vuln.severity else "UNKNOWN"
        lines.append(f"[HISTORICAL_EXPLOIT_MATCH]: {vuln.text} | SEVERITY: {severity}")
        lines.append(f"[SEARCH_RELEVANCE]: {vuln.match_confidence}")
 
    if not vulnerabilities:
        lines.append("[HISTORICAL_EXPLOIT_MATCH]: No historical exploit match found.")
 
    for scam in scam_matches:
        scam_type = scam.severity.upper() if scam.severity else "UNKNOWN"
        lines.append(f"[SCAM_PATTERN_MATCH]: {scam.text} | SEVERITY: {scam_type}")
        lines.append(f"[SEARCH_RELEVANCE]: {scam.match_confidence}")
 
    lines.append("[CONTEXT END]")
    return "\n".join(lines)


# /analyze-intent endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/analyze-intent", response_model=AnalysisResponse)
async def analyze_intent(report: SimulationReport) -> AnalysisResponse:
    t0 = time.perf_counter()
 
    if _embedder is None or _collection is None:
        raise HTTPException(status_code=503, detail="A.E.G.I.S. backend not initialised.")
 
    intent = report.transaction_intent.strip()
 
    # ── 1. Embed once ────────────────────────────────────────────────────────
    query_vec = await asyncio.get_event_loop().run_in_executor(
        None, _embed, intent
    )
 
    # ── 2. Parallel retrieval — 4 categories ─────────────────────────────────
    std_task   = asyncio.get_event_loop().run_in_executor(
        None, _query_by_category, query_vec, "standard", N_STANDARD_HITS
    )
    vuln_task  = asyncio.get_event_loop().run_in_executor(
        None, _query_by_category, query_vec, "vulnerability", N_VULN_HITS
    )
    intel_task = asyncio.get_event_loop().run_in_executor(
        None, _query_by_category, query_vec, "intelligence", N_VULN_HITS
    )
    scam_task  = asyncio.get_event_loop().run_in_executor(
        None, _query_by_category, query_vec, "scam", N_SCAM_HITS
    )
 
    std_hits, vuln_hits, intel_hits, scam_hits = await asyncio.gather(
        std_task, vuln_task, intel_task, scam_task
    )
 
    # ── 3. Apply confidence threshold ────────────────────────────────────────
    def threshold(hits: list[dict]) -> list[dict]:
        return [h for h in hits if h["confidence"] >= MIN_CONFIDENCE]
 
    std_hits      = threshold(std_hits)
    all_vuln_hits = threshold(vuln_hits) + threshold(intel_hits)
    all_vuln_hits = sorted(
        all_vuln_hits, key=lambda h: h["confidence"], reverse=True
    )[:N_VULN_HITS]
    all_scam_hits = sorted(
        threshold(scam_hits), key=lambda h: h["confidence"], reverse=True
    )[:N_SCAM_HITS]
 
    # ── 4. Match decision — vuln OR scam evidence required ───────────────────
    top_vuln_score = max((h["confidence"] for h in all_vuln_hits), default=0.0)
    top_scam_score = max((h["confidence"] for h in all_scam_hits), default=0.0)
    top_score      = max(top_vuln_score, top_scam_score)
    has_any_match  = bool(all_vuln_hits or all_scam_hits) and top_score >= MIN_CONFIDENCE
 
    # ── 5. Build structured output ────────────────────────────────────────────
    standard_baseline: Optional[EvidenceMatch] = None
    if std_hits:
        h = std_hits[0]
        standard_baseline = EvidenceMatch(
            text=h["text"],
            source=h["source"],
            match_confidence=h["confidence"],
        )
 
    vulnerability_evidence: list[EvidenceMatch] = [
        EvidenceMatch(
            text=h["text"],
            source=h["source"],
            severity=h.get("severity"),
            match_confidence=h["confidence"],
        )
        for h in all_vuln_hits
    ]
 
    scam_evidence: list[EvidenceMatch] = [
        EvidenceMatch(
            text=h["text"],
            source=h["source"],
            severity=h.get("severity"),
            match_confidence=h["confidence"],
        )
        for h in all_scam_hits
    ]
 
    # ── 6. Status and context block ───────────────────────────────────────────
    status = "match_found" if has_any_match else "no_match"
 
    llm_context = None
    if has_any_match:
        llm_context = build_llm_context(
            standard_baseline, vulnerability_evidence, scam_evidence
        )
 
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    log.info("analyze-intent | status=%s | score=%.4f | latency=%.1fms",
             status, top_score, latency_ms)
 
    if latency_ms > 500:
        log.warning("⚠  Latency budget exceeded: %.1fms > 500ms", latency_ms)
 
    return AnalysisResponse(
        status=status,
        transaction_intent=intent,
        standard_baseline=standard_baseline,
        vulnerability_evidence=vulnerability_evidence,
        scam_evidence=scam_evidence,
        match_confidence=round(top_score, 4),
        latency_ms=latency_ms,
        llm_context=llm_context,
    )


# Health check: Just to verify the API is up and can access the collection (and return current doc count).
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    doc_count = _collection.count() if _collection else -1
    return {
        "status": "ok",
        "model":  EMBED_MODEL,
        "docs":   doc_count,
    }


# Dev runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False, workers=1)
