"""
A.E.G.I.S. — Curated Audit Knowledge Base
Hand-curated findings extracted directly from the 3 OpenZeppelin PDFs.

Why hand-curated instead of PDF scraping?
  - ERC4626:  1 real High finding, rest are Low/Notes
  - v5.5:     0 High/Critical findings at all
  - v5.6:     0 High/Critical findings (only Medium/Low)

The PDF text chunker was catching TOC lines like "High Severity __ 7"
as false positives. This module replaces that with precise, structured
knowledge that will produce high-quality semantic matches.

To re-ingest after editing:
    python audit_knowledge.py --ingest
"""

from __future__ import annotations

import argparse
import hashlib
import logging

log = logging.getLogger("aegis.audit_knowledge")

# ─────────────────────────────────────────────────────────────────────────────
# Curated findings — extracted verbatim / summarized from the actual PDFs
# ─────────────────────────────────────────────────────────────────────────────

CURATED_FINDINGS = [

    # ── ERC4626 Audit (Nov 2022) ── H-01 ─────────────────────────────────────
    {
        "id":       "erc4626_h01_body",
        "source":   "OpenZeppelin ERC4626 Audit",
        "version":  "ERC4626",
        "severity": "high",
        "finding":  "H-01",
        "title":    "Vault deposits can be front-run and user funds stolen",
        "text": (
            "H-01 Vault deposits can be front-run and user funds stolen. "
            "The ERC4626 contract is susceptible to an underlying asset balance manipulation attack. "
            "When a user performs a deposit, the amount of shares received is calculated by taking "
            "assets provided multiplied by existing shares divided by all assets owned by the vault, "
            "rounded down. The problem arises when totalAssets is manipulated to induce unfavorable "
            "rounding for new depositors at the benefit of existing shareholders. "
            "In the most extreme case: the first user deposits 1 asset for 1 share. "
            "An attacker front-runs the next deposit of 1e18 tokens by directly transferring 1e18 "
            "of the underlying asset to the vault. The vault supply remains 1 while totalAssets is "
            "now 1e18+1. The victim receives 1 * 1e18 / (1e18+1) = 0 shares, losing their entire deposit. "
            "The attacker can repeat this attack in perpetuity, draining all depositors. "
            "This is a classic ERC4626 inflation attack / share price manipulation exploit. "
            "Status: Acknowledged, not resolved. OpenZeppelin will implement mitigations."
        ),
    },
    {
        "id":       "erc4626_h01_context",
        "source":   "OpenZeppelin ERC4626 Audit",
        "version":  "ERC4626",
        "severity": "high",
        "finding":  "H-01",
        "title":    "ERC4626 vault inflation attack — flash loan and rebasing token risks",
        "text": (
            "ERC4626 vault inflation attack additional context: "
            "The underlying asset balance of the vault is used to calculate the ratio of shares to assets. "
            "Vaults that allow transfers of underlying assets for more than one block create a time window "
            "where the underlying asset is out of the vault, allowing malicious users to mint shares at "
            "below true cost, diluting all existing positions. "
            "Vaults should never approve spenders for the underlying asset. "
            "If underlying assets are moved out without burning shares, malicious actors can artificially "
            "dilute every user holding shares at little to no cost. "
            "If ERC4626 tokens are flash-loanable, withdraw and redeem functions may suffer from an "
            "inflation attack where the owner inflates their balance to manipulate outcomes. "
            "Rebasing tokens may have a similar dilution effect and should be carefully analyzed. "
            "The _isVaultCollateralized invariant stops deposits when totalSupply > 0 and totalAssets = 0, "
            "but only applies to deposit, not mint — meaning users can still mint shares for free "
            "if the invariant is broken in a custom implementation."
        ),
    },

    # ── v5.5 Audit (Oct 2025) — no High/Critical, include Medium-impact Lows ─
    {
        "id":       "v55_l01_sig_normalization",
        "source":   "OpenZeppelin Contracts v5.5 Audit",
        "version":  "5.5",
        "severity": "low",
        "finding":  "L-01",
        "title":    "Inconsistent v normalization between 64-byte and 65-byte ECDSA signatures",
        "text": (
            "L-01 Inconsistent v normalization between signatures. "
            "The parse and parseCalldata helper functions split ECDSA signatures into v, r, s components "
            "for both 65-byte and EIP-2098 64-byte encodings. "
            "In the 64-byte path, v is derived from vs and normalized to 27 or 28. "
            "In the 65-byte path, v is taken as-is. "
            "This yields inconsistent outputs: 65-byte inputs may return v = 0 or 1, "
            "while 64-byte inputs return 27 or 28. "
            "Downstream code expecting canonical v can misbehave. "
            "Calls to ecrecover with v = 0 or 1 will return the zero address, causing silent failures. "
            "Silent ecrecover failures returning zero address can bypass signature validation checks "
            "if the caller does not explicitly verify the recovered address is non-zero. "
            "Status: Resolved in PR #5990."
        ),
    },
    {
        "id":       "v55_l02_invalid_length_check",
        "source":   "OpenZeppelin Contracts v5.5 Audit",
        "version":  "5.5",
        "severity": "low",
        "finding":  "L-02",
        "title":    "Incorrect hardcoded value in isValidERC1271SignatureNow length check",
        "text": (
            "L-02 Incorrect value in isValidERC1271SignatureNow. "
            "In SignatureChecker, the isValidERC1271SignatureNow function has an incorrect hardcoded value. "
            "The comparison against returndatasize() checks if return data is greater than 0x19 (25 bytes) "
            "but should ensure return data is greater than 0x1f (31 bytes). "
            "This incorrect length check can cause signature validation to incorrectly accept or reject "
            "ERC-1271 signatures from smart contract wallets. "
            "ERC-1271 is used by multisigs, smart wallets, and DAOs to validate signatures on-chain. "
            "An incorrect length check bypasses proper return data validation. "
            "Status: Resolved in PR #5973."
        ),
    },

    # ── v5.6 Audit (Feb 2026) — Medium findings ───────────────────────────────
    {
        "id":       "v56_m01_memory_aliasing",
        "source":   "OpenZeppelin Contracts v5.6 Audit",
        "version":  "5.6",
        "severity": "medium",
        "finding":  "M-01",
        "title":    "Memory aliasing for single-byte RLP inputs causes silent data corruption",
        "text": (
            "M-01 Memory aliasing for single-byte inputs. "
            "The RLP encode and readList functions return the input directly without copying "
            "when the input is a single byte with value less than 128. "
            "The returned bytes memory shares the same memory location as the input. "
            "Any subsequent modification to the input also modifies the encoded result, and vice versa. "
            "Protocols using this for security-sensitive operations such as transaction encoding, "
            "Merkle proofs, or cross-chain messaging may experience silent data corruption "
            "if the input is modified after encoding. "
            "The affected edge case covers common values including small nonces, chain IDs under 128, "
            "and boolean representations. Since no error is produced, such corruption is difficult to diagnose. "
            "Status: Resolved in PR #6342 — single-byte inputs below 128 now return a fresh bytes copy."
        ),
    },
    {
        "id":       "v56_m02_receive_id_dos",
        "source":   "OpenZeppelin Contracts v5.6 Audit",
        "version":  "5.6",
        "severity": "medium",
        "finding":  "M-02",
        "title":    "receiveId check causes accidental DoS with empty receiveId gateways",
        "text": (
            "M-02 receiveId check causes accidental DoS/incompatibility with empty receiveId gateways. "
            "ERC7786Recipient implements replay protection keyed by (gateway, receiveId) using a bitmap. "
            "If an authorized gateway delivers more than one message with receiveId == bytes32(0), "
            "the first message succeeds and all subsequent messages revert, regardless of sender or payload. "
            "EIP-7786 allows receiveId to be empty. A compliant gateway using empty IDs or zero as sentinel "
            "can unintentionally cause permanent message delivery failure after the first message. "
            "This creates a cross-chain DoS vector where valid messages are permanently blocked. "
            "Status: Resolved in PR #6346."
        ),
    },
    {
        "id":       "v56_l02_webauthn_bypass",
        "source":   "OpenZeppelin Contracts v5.6 Audit",
        "version":  "5.6",
        "severity": "low",
        "finding":  "L-02",
        "title":    "WebAuthn-specific validations bypassed by falling back to raw P256 verification",
        "text": (
            "L-02 Bypassing WebAuthn-specific validations in SignerWebAuthn._rawSignatureValidation. "
            "If WebAuthn verification returns false, the contract falls back to raw P256 signature verification. "
            "This allows bypassing WebAuthn-specific validations such as UV (user verification). "
            "An attacker with a valid P256 signature but no valid WebAuthn credential can bypass "
            "the stronger WebAuthn authentication requirements. "
            "Smart contract wallets using SignerWebAuthn for authentication may be vulnerable to "
            "attackers who obtain only a raw P256 key without the full WebAuthn authenticator. "
            "Status: Resolved in PR #6337."
        ),
    },
    {
        "id":       "v56_l03_message_loss",
        "source":   "OpenZeppelin Contracts v5.6 Audit",
        "version":  "5.6",
        "severity": "low",
        "finding":  "L-03",
        "title":    "Possible permanent message loss in ERC7786Recipient cross-chain message processing",
        "text": (
            "L-03 Possible permanent message loss in ERC7786Recipient._processMessage. "
            "In ERC7786Recipient.receiveMessage, the received flag is set before _processMessage is called. "
            "If _processMessage does not revert on failure but silently exits without processing the message, "
            "the message is permanently lost — it cannot be re-delivered because it is already marked as received. "
            "Cross-chain messages carrying value or state-changing instructions could be silently dropped. "
            "This is a check-effects-interactions pattern violation in cross-chain messaging. "
            "Status: Resolved in PR #6330."
        ),
    },
    {
        "id":       "v56_l09_trie_proof",
        "source":   "OpenZeppelin Contracts v5.6 Audit",
        "version":  "5.6",
        "severity": "low",
        "finding":  "L-09",
        "title":    "TrieProof rejects valid Merkle-Patricia proofs with inline extension leaf nodes",
        "text": (
            "L-09 TrieProof rejects valid Merkle-Patricia proofs with inline extension leaf nodes. "
            "tryTraverse fails to verify valid Ethereum Merkle-Patricia trie proofs when an extension node "
            "references an inline (non-hashed) child node. Traversal reaches the end of the provided proof "
            "without returning a value and incorrectly reports ProofError.INVALID_PROOF. "
            "This is incompatible with the Ethereum MPT specification and standard client proofs. "
            "Protocols relying on TrieProof for on-chain verification of storage slots, transactions, "
            "or account state may fail to verify otherwise correct proofs. "
            "While invalid proofs are not accepted (no security vulnerability), valid proofs are rejected, "
            "causing operational failures in cross-chain bridges and storage proof systems. "
            "Status: Resolved in PR #6351."
        ),
    },

    # ── Cross-cutting vulnerability patterns from all 3 audits ───────────────
    {
        "id":       "cross_erc4626_custom_impl_risk",
        "source":   "OpenZeppelin ERC4626 Audit",
        "version":  "ERC4626",
        "severity": "high",
        "finding":  "Introduction",
        "title":    "ERC4626 custom implementation pitfalls — share price manipulation and dilution",
        "text": (
            "ERC4626 custom implementation security risks: "
            "The ERC4626 standard defines a tokenized vault where shares represent underlying asset ownership. "
            "Key attack vectors in custom implementations: "
            "1. Share price manipulation: totalAssets can be manipulated by directly transferring assets "
            "to the vault contract, inflating the denominator and causing victims to receive fewer shares. "
            "2. Mint vs deposit asymmetry: _isVaultCollateralized only guards deposit, not mint — "
            "users can mint shares for free if the invariant is broken in custom implementations. "
            "3. Flash loan inflation: if ERC4626 tokens are flash-loanable, withdraw/redeem can be "
            "manipulated by artificially inflating the owner's balance. "
            "4. Rebasing token risk: rebasing tokens used as underlying assets can cause unexpected "
            "dilution for all shareholders. "
            "5. Spender approval risk: vaults should never approve spenders for the underlying asset "
            "as this creates a window for malicious share minting at below-market cost."
        ),
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion
# ─────────────────────────────────────────────────────────────────────────────

def stable_id(text: str, prefix: str = "audit") -> str:
    return f"{prefix}_{hashlib.sha256(text.encode()).hexdigest()[:16]}"


def ingest_curated_findings(collection, embedder) -> int:
    """
    Upserts all curated findings into ChromaDB.
    Returns total chunks stored.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    ids, docs, metas, embeds = [], [], [], []

    for finding in CURATED_FINDINGS:
        # Each finding may be split if > 800 chars, but most fit in one chunk
        chunks = splitter.split_text(finding["text"])
        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if len(chunk) < 40:
                continue
            doc_id = stable_id(chunk, prefix=f"audit_{finding['id']}")
            ids.append(doc_id)
            docs.append(chunk)
            metas.append({
                "category": "vulnerability",
                "severity":  finding["severity"],
                "source":    finding["source"],
                "version":   finding["version"],
                "finding":   finding["finding"],
                "title":     finding["title"],
            })
            embeds.append(
                embedder.encode(chunk, normalize_embeddings=True).tolist()
            )

    if ids:
        collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)
        log.info("✓ Curated audit findings: %d chunks upserted.", len(ids))

    return len(ids)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Ingest curated audit findings into ChromaDB")
    parser.add_argument("--ingest", action="store_true", help="Run ingestion")
    parser.add_argument("--list",   action="store_true", help="List all findings")
    args = parser.parse_args()

    if args.list:
        print(f"\n{'─'*65}")
        print(f"{'ID':<35} {'SEV':<8} {'SOURCE'}")
        print(f"{'─'*65}")
        for f in CURATED_FINDINGS:
            print(f"  {f['id']:<33} {f['severity']:<8} {f['source']}")
        print(f"{'─'*65}")
        print(f"  Total: {len(CURATED_FINDINGS)} findings\n")
        return

    if args.ingest:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer

        client = chromadb.PersistentClient(
            path="./aegis_db",
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(
            name="library_of_truth",
            metadata={"hnsw:space": "cosine"},
        )
        embedder = SentenceTransformer("all-MiniLM-L6-v2")

        # Remove old noisy audit chunks first
        print("Removing old PDF-scraped audit chunks...")
        try:
            old = collection.get(where={"category": {"$eq": "vulnerability"}})
            if old["ids"]:
                collection.delete(ids=old["ids"])
                print(f"  Deleted {len(old['ids'])} old vulnerability chunks.")
        except Exception as e:
            print(f"  Could not delete old chunks: {e}")

        count = ingest_curated_findings(collection, embedder)
        print(f"\n✅ Done. {count} clean curated findings ingested.")
        print(f"   Total docs in collection: {collection.count()}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
