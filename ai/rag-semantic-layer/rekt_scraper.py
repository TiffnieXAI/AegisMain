"""
A.E.G.I.S. — REKT News Live Intelligence Scraper
Replaces the placeholder stub in ingest.py.

Scrapes rekt.news for recent DeFi hack post-mortems, extracts structured
exploit intelligence, and upserts it into ChromaDB as 'intelligence' chunks.

Usage (standalone):
    python rekt_scraper.py                  # last 7 days
    python rekt_scraper.py --days 30        # last 30 days
    python rekt_scraper.py --pages 3        # first 3 index pages only
    python rekt_scraper.py --full           # all 41 pages (initial seed)

Schedule weekly via cron:
    0 3 * * 1  cd /path/to/aegis && python rekt_scraper.py --days 7
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import chromadb
import httpx
from bs4 import BeautifulSoup
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

log = logging.getLogger("aegis.rekt_scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Configuration ─────────────────────────────────────────────────────────────
CHROMA_PATH     = "./aegis_db"
COLLECTION_NAME = "library_of_truth"
EMBED_MODEL     = "all-MiniLM-L6-v2"
CHUNK_SIZE      = 800
CHUNK_OVERLAP   = 100

BASE_URL        = "https://rekt.news"
REQUEST_DELAY   = 1.2          # seconds between HTTP requests (be polite)
REQUEST_TIMEOUT = 15           # seconds
MAX_PAGES       = 41           # rekt.news has 41 index pages as of March 2026

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AEGIS-SecurityBot/1.0; "
        "+https://github.com/your-org/aegis)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

REKT_BOILERPLATE = [
    "rekt serves as a public platform",
    "donate (eth",
    "donate (eth/erc20)",
    "0x3c5c2f4bcec51a36494682f91dbc6ca7c63b514c",
    "all content copyright",
    "run by rekthq",
    "founded by julien",
]

# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RektArticle:
    title:       str
    slug:        str
    url:         str
    date_str:    str                     # e.g. "Tuesday, March 10, 2026"
    date:        Optional[datetime]
    tags:        list[str]
    excerpt:     str
    body:        str                     # full article text
    amount_lost: Optional[str] = None   # extracted dollar figure if present


# HTTP client
# ─────────────────────────────────────────────────────────────────────────────

def make_client() -> httpx.Client:
    return httpx.Client(
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    )


# Index page scraper  (rekt.news/?page=N)
# ─────────────────────────────────────────────────────────────────────────────

DATE_PATTERN = re.compile(
    r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
    r"(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s+\d{4}"
)
AMOUNT_PATTERN = re.compile(r"\$[\d,]+(?:\.\d+)?\s*(?:million|billion|thousand|M|B|K)?", re.I)


def parse_date(date_str: str) -> Optional[datetime]:
    """Convert 'Tuesday, March 10, 2026' → datetime (UTC, midnight)."""
    try:
        # strip day-of-week prefix
        parts = date_str.split(", ", 1)
        date_part = parts[1] if len(parts) == 2 else date_str
        return datetime.strptime(date_part.strip(), "%B %d, %Y").replace(tzinfo=timezone.utc)
    except (ValueError, IndexError):
        return None


def scrape_index_page(client: httpx.Client, page: int) -> list[dict]:
    """
    Returns a list of article stubs from one index page:
    [{title, slug, url, date_str, tags, excerpt}, ...]
    """
    url = f"{BASE_URL}/" if page == 0 else f"{BASE_URL}/?page={page}"
    try:
        resp = client.get(url)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("Index page %d fetch failed: %s", page, exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []

    # Each article on the index is wrapped in an <h5> title + surrounding text
    # Structure: <h5><a href="/slug">Title</a></h5> ... date ... tags ... excerpt
    for h5 in soup.find_all("h5"):
        a_tag = h5.find("a", href=True)
        if not a_tag:
            continue

        href  = a_tag["href"]
        title = a_tag.get_text(strip=True)
        slug  = href.lstrip("/")
        url   = f"{BASE_URL}/{slug}"

        # Grab the sibling text block (date, tags, excerpt)
        # Walk siblings after the <h5> until the next <h5>
        sibling_text = []
        tag_links    = []
        for sib in h5.next_siblings:
            if sib.name == "h5":
                break
            if hasattr(sib, "find_all"):
                tag_links += [
                    a.get_text(strip=True)
                    for a in sib.find_all("a", href=lambda h: h and "?tag=" in h)
                ]
                sibling_text.append(sib.get_text(" ", strip=True))
            elif isinstance(sib, str) and sib.strip():
                sibling_text.append(sib.strip())

        full_text = " ".join(sibling_text)

        # Extract date
        date_match = DATE_PATTERN.search(full_text)
        date_str   = date_match.group(0) if date_match else ""

        # Extract excerpt (everything after tags/date noise)
        excerpt = full_text
        for tag in tag_links:
            excerpt = excerpt.replace(tag, "")
        if date_str:
            excerpt = excerpt.replace(date_str, "")
        excerpt = re.sub(r"\s{2,}", " ", excerpt).strip(" -·")

        articles.append({
            "title":    title,
            "slug":     slug,
            "url":      url,
            "date_str": date_str,
            "tags":     tag_links,
            "excerpt":  excerpt,
        })

    log.info("  Index page %d → %d article stubs", page, len(articles))
    return articles


# Full article scraper
# ─────────────────────────────────────────────────────────────────────────────

def scrape_article(client: httpx.Client, stub: dict) -> Optional[RektArticle]:
    """Fetches the full article body and returns a populated RektArticle."""
    try:
        resp = client.get(stub["url"])
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("  Article fetch failed (%s): %s", stub["slug"], exc)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove nav, footer, header, scripts, styles
    for tag in soup(["nav", "footer", "header", "script", "style", "img"]):
        tag.decompose()

    # Main body: everything inside the article content area
    # rekt.news renders article body as a series of <p>, <h2>, <h3> etc.
    # We collect all paragraph-level text after the title/date header
    body_parts = []

    for el in soup.find_all(["p", "h2", "h3", "h4", "li", "blockquote"]):
        text = el.get_text(" ", strip=True)
        if not text or len(text) < 30:
            continue
        # Filter out common boilerplate phrases that add noise to embeddings
        if any(bp in text.lower() for bp in REKT_BOILERPLATE):
            continue
        body_parts.append(text)

    body = "\n\n".join(body_parts)

    # Extract money amounts for metadata
    amounts = AMOUNT_PATTERN.findall(body or stub["excerpt"])
    amount_lost = amounts[0] if amounts else None

    return RektArticle(
        title       = stub["title"],
        slug        = stub["slug"],
        url         = stub["url"],
        date_str    = stub["date_str"],
        date        = parse_date(stub["date_str"]),
        tags        = stub["tags"],
        excerpt     = stub["excerpt"],
        body        = body if body else stub["excerpt"],
        amount_lost = amount_lost,
    )


# ChromaDB helpers
# ─────────────────────────────────────────────────────────────────────────────

def stable_id(text: str, prefix: str = "intel") -> str:
    return f"{prefix}_{hashlib.sha256(text.encode()).hexdigest()[:16]}"


def get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def build_chunk_text(article: RektArticle, chunk: str) -> str:
    """
    Prepend article metadata to each chunk so semantic search can match
    on protocol name, exploit type, and amount — not just raw body text.
    """
    tags_str = ", ".join(article.tags) if article.tags else "unknown"
    amount   = f" | AMOUNT_LOST: {article.amount_lost}" if article.amount_lost else ""
    return (
        f"EXPLOIT: {article.title} | DATE: {article.date_str} | "
        f"TAGS: {tags_str}{amount}\n\n{chunk}"
    )


def upsert_article(
    article:    RektArticle,
    collection: chromadb.Collection,
    embedder:   SentenceTransformer,
    splitter:   RecursiveCharacterTextSplitter,
) -> int:
    """Chunks, embeds, and upserts one article. Returns chunk count stored."""
    raw_chunks = splitter.split_text(article.body)
    if not raw_chunks:
        raw_chunks = [article.excerpt]

    ids, docs, metas, embeds = [], [], [], []

    for chunk in raw_chunks:
        chunk = chunk.strip()
        if len(chunk) < 60:
            continue

        enriched = build_chunk_text(article, chunk)
        doc_id   = stable_id(enriched)

        ids.append(doc_id)
        docs.append(enriched)
        metas.append({
            "category":    "intelligence",
            "source":      "REKT News",
            "title":       article.title,
            "slug":        article.slug,
            "url":         article.url,
            "date":        article.date_str,
            "tags":        ", ".join(article.tags),
            "amount_lost": article.amount_lost or "",
        })
        embeds.append(embedder.encode(enriched, normalize_embeddings=True).tolist())

    if ids:
        collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)

    return len(ids)


# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def run_scraper(
    since_days:  int  = 7,
    max_pages:   int  = 3,
    full_seed:   bool = False,
) -> dict:
    """
    Main entry point for the live REKT News ingestion.

    Args:
        since_days:  Only ingest articles published within this many days.
                     Ignored when full_seed=True.
        max_pages:   How many index pages to scan (each has ~12 articles).
        full_seed:   If True, scrape all 41 pages regardless of date filter.

    Returns:
        Summary dict: {articles_found, articles_stored, chunks_stored}
    """
    t0 = time.perf_counter()

    cutoff = (
        datetime.min.replace(tzinfo=timezone.utc)    # no cutoff for full seed
        if full_seed
        else datetime.now(timezone.utc) - timedelta(days=since_days)
    )

    if full_seed:
        max_pages = MAX_PAGES
        log.info("Full seed mode: scraping all %d index pages", max_pages)
    else:
        log.info("Incremental mode: articles from last %d days, max %d pages",
                 since_days, max_pages)

    collection = get_collection()
    embedder   = SentenceTransformer(EMBED_MODEL)
    splitter   = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )

    stats = {"articles_found": 0, "articles_stored": 0, "chunks_stored": 0}

    _seen_slugs: set[str] = set()

    with make_client() as client:
        for page_num in range(max_pages):
            stubs = scrape_index_page(client, page_num)
            if not stubs:
                log.info("Empty index page %d — stopping.", page_num)
                break

            page_has_recent = False

            for stub in stubs:
                stats["articles_found"] += 1

                # Date gate
                parsed_date = parse_date(stub["date_str"])
                if parsed_date and parsed_date < cutoff:
                    log.debug("  Skipping (too old): %s | %s", stub["slug"], stub["date_str"])
                    continue

                page_has_recent = True
                time.sleep(REQUEST_DELAY)  # polite crawling

                article = scrape_article(client, stub)
                if article is None:
                    continue

                chunk_count = upsert_article(article, collection, embedder, splitter)
                stats["articles_stored"] += 1
                stats["chunks_stored"]   += chunk_count

                log.info(
                    "  ✓ [%s] %s → %d chunks | tags: %s",
                    article.date_str,
                    article.title,
                    chunk_count,
                    ", ".join(article.tags[:3]),
                )

            # If the entire page was older than cutoff, stop paginating
            new_slugs = {s["slug"] for s in stubs} - _seen_slugs
            _seen_slugs.update(new_slugs)
            if not new_slugs:
                log.info("Page %d returned only already-seen articles — stopping.", page_num)
                break

            if not page_has_recent and not full_seed:
                log.info("Page %d had no recent articles — stopping early.", page_num)
                break

            time.sleep(REQUEST_DELAY)

    elapsed = time.perf_counter() - t0
    stats["elapsed_seconds"] = round(elapsed, 1)
    stats["total_docs_in_db"] = collection.count()

    log.info(
        "✅ REKT scrape complete | articles_found=%d | stored=%d | chunks=%d | "
        "total_db_docs=%d | elapsed=%.1fs",
        stats["articles_found"],
        stats["articles_stored"],
        stats["chunks_stored"],
        stats["total_docs_in_db"],
        elapsed,
    )
    return stats


# Drop-in replacement for ingest.py's placeholder function
# ─────────────────────────────────────────────────────────────────────────────

def ingest_rekt_intelligence(
    collection: chromadb.Collection,
    embedder:   SentenceTransformer,
    since_days: int = 7,
) -> None:
    """
    Signature-compatible replacement for the stub in ingest.py.
    Call this from ingest.py instead of the placeholder.

    Example (in ingest.py):
        from rekt_scraper import ingest_rekt_intelligence
        ...
        if args.all or args.intel:
            ingest_rekt_intelligence(collection, embedder)
    """
    run_scraper(since_days=since_days, max_pages=5)


# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="A.E.G.I.S. — Live REKT News intelligence scraper"
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Ingest articles published in the last N days (default: 7)"
    )
    parser.add_argument(
        "--pages", type=int, default=3,
        help="Max index pages to scan (default: 3, ~36 articles)"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Full seed: scrape all 41 pages regardless of date (initial run)"
    )
    args = parser.parse_args()

    stats = run_scraper(
        since_days=args.days,
        max_pages=args.pages,
        full_seed=args.full,
    )

    print("\n── Scrape Summary ──────────────────────────────────")
    for k, v in stats.items():
        print(f"  {k:25s}: {v}")


if __name__ == "__main__":
    main()
