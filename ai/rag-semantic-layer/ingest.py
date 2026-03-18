"""
Usage:
    python ingest.py --standards --audits --intel
    python ingest.py --all
"""

import os
import re
import time
import hashlib
import logging
import argparse
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

os.environ["ANONYMIZED_TELEMETRY"] = "False"

# ── Optional PDF support ──────────────────────────────────────────────────────
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("PyMuPDF not installed. PDF ingestion will be skipped. Run: pip install pymupdf")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("aegis.ingest")

# ── Configuration ─────────────────────────────────────────────────────────────
CHROMA_PATH   = "./aegis_db"
COLLECTION    = "library_of_truth"
EMBED_MODEL   = "all-MiniLM-L6-v2"
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 100

# Severity keywords that gate vulnerability chunk storage
HIGH_SEVERITY_MARKERS = ["High", "Critical", "HIGH", "CRITICAL"]

AUDIT_SOURCES = [
    {
        "path": "audits/openzeppelin_v5_6.pdf",
        "label": "OpenZeppelin v5.6 Audit",
        "version": "5.6",
    },
    {
        "path": "audits/openzeppelin_v5_5.pdf",
        "label": "OpenZeppelin v5.5 Audit",
        "version": "5.5",
    },
    {
        "path": "audits/openzeppelin_erc4626.pdf",
        "label": "OpenZeppelin ERC4626 Audit",
        "version": "ERC4626",
    },
]

STANDARD_SOURCES = [
    {
        "path": "standards/IERC20.sol",
        "label": "IERC20 Interface Standard",
        "interface": "ERC20",
    },
    {
        "path": "standards/IERC721.sol",
        "label": "IERC721 Interface Standard",
        "interface": "ERC721",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def stable_id(text: str, prefix: str = "") -> str:
    """Deterministic document ID from content hash."""
    digest = hashlib.sha256(text.encode()).hexdigest()[:16]
    return f"{prefix}_{digest}" if prefix else digest


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    return splitter.split_text(text)

def contains_high_severity(text: str) -> bool:
    """Return True only if the chunk mentions a High/Critical finding."""
    return any(marker in text for marker in HIGH_SEVERITY_MARKERS)

def is_meaningful_chunk(text: str) -> bool:
    """Filter out PDF artifacts: TOC lines, underscore separators, page numbers."""
    # Reject if more than 10% of characters are underscores
    if text.count("_") / max(len(text), 1) > 0.1:
        return False
    # Reject if it's mostly newlines (table of contents artifact)
    if text.count("\n") / max(len(text), 1) > 0.15:
        return False
    # Reject if no real sentences (less than 3 words per line on average)
    words = text.split()
    if len(words) < 20:
        return False
    return True

def extract_pdf_text(path: str) -> str:
    if not PDF_AVAILABLE:
        log.warning("Skipping PDF %s — PyMuPDF not available.", path)
        return ""
    doc = fitz.open(path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def read_solidity(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


# ─────────────────────────────────────────────────────────────────────────────
# ChromaDB client + collection
# ─────────────────────────────────────────────────────────────────────────────

def get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},  # cosine similarity → 1 = identical
    )
    log.info("Connected to collection '%s' (docs: %d)", COLLECTION, collection.count())
    return collection


def get_embedder() -> SentenceTransformer:
    log.info("Loading embedding model: %s", EMBED_MODEL)
    return SentenceTransformer(EMBED_MODEL)


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion: Standards (Solidity interfaces)
# ─────────────────────────────────────────────────────────────────────────────

def ingest_standards(collection: chromadb.Collection, embedder: SentenceTransformer) -> None:
    log.info("── Ingesting Standards ──────────────────────────────")
    total = 0

    for src in STANDARD_SOURCES:
        if not Path(src["path"]).exists():
            log.warning("Standard file not found, skipping: %s", src["path"])
            continue

        raw = read_solidity(src["path"])
        chunks = chunk_text(raw)

        ids, docs, metas, embeds = [], [], [], []
        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) < 40:          # skip trivial fragments
                continue
            doc_id = stable_id(chunk, prefix="std")
            ids.append(doc_id)
            docs.append(chunk)
            metas.append({
                "category":  "standard",
                "source":    src["label"],
                "interface": src["interface"],
            })
            embeds.append(embedder.encode(chunk, normalize_embeddings=True).tolist())

        if ids:
            collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)
            log.info("  ✓ %s — %d chunks stored", src["label"], len(ids))
            total += len(ids)

    log.info("Standards ingestion complete: %d chunks.", total)


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion: Vulnerabilities (OpenZeppelin PDF audits)
# ─────────────────────────────────────────────────────────────────────────────

def ingest_audits(collection: chromadb.Collection, embedder: SentenceTransformer) -> None:
    log.info("── Ingesting Audit PDFs ─────────────────────────────")
    total = 0

    for src in AUDIT_SOURCES:
        if not Path(src["path"]).exists():
            log.warning("Audit PDF not found, skipping: %s", src["path"])
            continue

        raw = extract_pdf_text(src["path"])
        if not raw.strip():
            log.warning("  Empty PDF content for %s, skipping.", src["path"])
            continue

        chunks = chunk_text(raw)
        high_chunks = [c for c in chunks if contains_high_severity(c) and is_meaningful_chunk(c)]
        log.info("  %s → %d total chunks, %d High/Critical chunks retained",
                 src["label"], len(chunks), len(high_chunks))

        ids, docs, metas, embeds = [], [], [], []
        for chunk in high_chunks:
            chunk = chunk.strip()
            if len(chunk) < 80:
                continue
            doc_id = stable_id(chunk, prefix="vuln")
            ids.append(doc_id)
            docs.append(chunk)
            metas.append({
                "category": "vulnerability",
                "severity":  "high",
                "source":    src["label"],
                "version":   src["version"],
            })
            embeds.append(embedder.encode(chunk, normalize_embeddings=True).tolist())

        if ids:
            collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)
            log.info("  ✓ %s — %d high-severity chunks stored", src["label"], len(ids))
            total += len(ids)

    log.info("Audit ingestion complete: %d high-severity chunks.", total)


# ─────────────────────────────────────────────────────────────────────────────
# Intelligence: REKT News weekly scraper (placeholder)
# ─────────────────────────────────────────────────────────────────────────────

def ingest_rekt_intelligence(
    collection: chromadb.Collection,
    embedder: SentenceTransformer,
    since_days: int = 7,
) -> None:
    """
    Live REKT News intelligence feed — scrapes rekt.news for recent
    DeFi hack post-mortems and upserts them into ChromaDB.

    Delegates to rekt_scraper.py which handles pagination, article
    body extraction, chunking, embedding, and idempotent upserts.
    """
    log.info("── REKT Intelligence Feed (live scraper) ────────────")
    try:
        import sys, os
        _here = os.path.dirname(os.path.abspath(__file__))
        if _here not in sys.path:
            sys.path.insert(0, _here)
        from rekt_scraper import run_scraper
        stats = run_scraper(since_days=since_days, max_pages=5)
        log.info(
            "  ✓ REKT scrape done | articles_stored=%d | chunks=%d",
            stats.get("articles_stored", 0),
            stats.get("chunks_stored", 0),
        )
    except ImportError as exc:
        log.error("  ✗ Import failed: %s", exc)
    except Exception as exc:
        log.error("  ✗ REKT scrape failed: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry-point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="A.E.G.I.S. — Library of Truth Ingestion")
    parser.add_argument("--standards", action="store_true", help="Ingest Solidity interface standards")
    parser.add_argument("--audits",    action="store_true", help="Ingest OpenZeppelin audit PDFs")
    parser.add_argument("--intel",     action="store_true", help="Run REKT News intelligence scraper")
    parser.add_argument("--all",       action="store_true", help="Run all ingestion pipelines")
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    t0 = time.perf_counter()

    collection = get_collection()
    embedder   = get_embedder()

    if args.all or args.standards:
        ingest_standards(collection, embedder)

    if args.all or args.audits:
        ingest_audits(collection, embedder)

    if args.all or args.intel:
        ingest_rekt_intelligence(collection, embedder)

    elapsed = time.perf_counter() - t0
    log.info("✅ Ingestion complete in %.2fs | Total docs in collection: %d",
             elapsed, collection.count())


if __name__ == "__main__":
    main()
