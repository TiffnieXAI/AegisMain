"""
A.E.G.I.S. — Scam Pattern Knowledge Base
Curated scam detection patterns built from:
  - ScamSniffer 2023/2024/2025 annual reports ($800M+ tracked losses)
  - ScamSniffer 2026 signature phishing data (207% spike in Jan 2026)
  - Chainalysis 2025 Crime Report ($2.8B rug pull losses)
  - Token Sniffer honeypot detection patterns
  - DEXTools rug pull checklist 2026
  - Real drainer kit mechanics: Monkey Drainer, Inferno Drainer, Angel Drainer, Pink Drainer

To ingest:
    python scam_knowledge.py --ingest
"""

from __future__ import annotations

import argparse
import hashlib
import logging

log = logging.getLogger("aegis.scam_knowledge")

# ─────────────────────────────────────────────────────────────────────────────
# Scam Pattern Knowledge Base
# ─────────────────────────────────────────────────────────────────────────────

SCAM_PATTERNS = [

    # ── SIGNATURE PHISHING ────────────────────────────────────────────────────

    {
        "id":        "sig_permit_phishing",
        "scam_type": "signature_phishing",
        "severity":  "critical",
        "title":     "Permit / Permit2 signature phishing — primary wallet drainer method",
        "text": (
            "Permit and Permit2 signature phishing is the dominant wallet drainer method, "
            "accounting for 38% of large-case losses in 2025 according to ScamSniffer. "
            "The permit() function allows off-chain EIP-712 signed approvals that drain tokens "
            "without requiring an on-chain approval transaction first. "
            "The victim signs what appears to be a harmless message but is actually a Permit "
            "signature granting unlimited token spend allowance to the attacker's address. "
            "Unlike setApprovalForAll which requires an on-chain transaction, Permit signatures "
            "are gasless and harder to detect — the wallet shows a 'sign message' prompt "
            "rather than a transaction prompt. "
            "Uniswap Permit2 extends this to all ERC20 tokens simultaneously. "
            "A single Permit2 signature can grant unlimited spend access across an entire "
            "token portfolio in one signing action. "
            "Detection indicators: signature request mentioning 'permit', 'allowance', "
            "'spender', 'deadline' fields in an EIP-712 typed message. "
            "The verifyingContract should match the token address — if it does not, "
            "this is a phishing signature. "
            "In 2024, one victim lost $55 million in DAI via a single setOwner phishing "
            "signature targeting Proxy ownership modification."
        ),
    },
    {
        "id":        "sig_seaport_blur_phishing",
        "scam_type": "signature_phishing",
        "severity":  "critical",
        "title":     "Seaport / Blur NFT listing signature phishing",
        "text": (
            "NFT marketplace signature phishing abuses legitimate Seaport, Blur, and LooksRare "
            "order signing mechanisms to create fake listings that sell NFTs for near-zero value. "
            "The attacker tricks users into signing a valid Seaport order that lists their "
            "high-value NFT for 0.00001 ETH to the attacker's address. "
            "The signature appears as a legitimate marketplace listing prompt. "
            "Once signed, the attacker immediately fulfills the order, acquiring the NFT "
            "for effectively nothing with no further interaction from the victim. "
            "This bypasses traditional approval-based drainers entirely — no setApprovalForAll "
            "is needed, just one valid marketplace order signature. "
            "Detection indicators: Seaport/Blur/LooksRare signature with consideration "
            "amount below market value, unfamiliar counterparty address, "
            "triggered outside the legitimate marketplace UI."
        ),
    },
    {
        "id":        "sig_eip7702_phishing",
        "scam_type": "signature_phishing",
        "severity":  "critical",
        "title":     "EIP-7702 malicious delegation signature — emerged post-Pectra upgrade",
        "text": (
            "EIP-7702 malicious signature phishing emerged after the Ethereum Pectra upgrade "
            "in 2025, with 2 large cases recorded in August 2025 per ScamSniffer. "
            "EIP-7702 allows EOA wallets to temporarily delegate execution to a smart contract. "
            "A malicious EIP-7702 delegation signature grants the attacker's contract "
            "full execution control over the victim's EOA wallet address. "
            "Unlike standard approvals that grant token-specific access, EIP-7702 delegation "
            "grants arbitrary code execution — the attacker can drain all assets, "
            "execute any transaction, and interact with any contract as the victim. "
            "This is the most powerful known phishing vector as of 2026. "
            "Detection indicators: EIP-7702 authorization signature, "
            "delegate address not recognized, request outside expected wallet upgrade flow."
        ),
    },
    {
        "id":        "sig_numerical_address_bypass",
        "scam_type": "signature_phishing",
        "severity":  "high",
        "title":     "Numerical address bypass — Pink Drainer wallet security alert evasion",
        "text": (
            "Pink Drainer wallet security bypass technique: passing numerical representation "
            "of contract addresses instead of hex to exploit wallet normalization processes. "
            "The verifyingContract field in an EIP-712 signature uses the decimal integer "
            "representation of the address (e.g. 996101235222674412020337938588541139382869425796) "
            "instead of the standard hex format (e.g. 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84). "
            "The signature result is identical whether hex or decimal is used due to normalization, "
            "but the decimal representation makes the address unreadable in wallet UIs, "
            "bypassing existing security alerts and blacklist checks. "
            "Pink Drainer stole tens of millions using this technique. "
            "Detection: verifyingContract value does not start with 0x, "
            "large integer value in contract address field of EIP-712 signature."
        ),
    },

    # ── WALLET DRAINER KITS ───────────────────────────────────────────────────

    {
        "id":        "drainer_kit_patterns",
        "scam_type": "wallet_drainer",
        "severity":  "critical",
        "title":     "Wallet drainer kit mechanics — Inferno, Angel, Monkey, Pink Drainer",
        "text": (
            "Wallet drainer kits are SaaS malware sold to affiliates who deploy them on "
            "phishing websites. Major kits include Monkey Drainer, Inferno Drainer, "
            "Angel Drainer (replaced Inferno after exit), and Pink Drainer. "
            "ScamSniffer tracked over $800M stolen via these kits since 2023. "
            "In 2024 alone, $494M was stolen from 332,000 victims — 67% increase year-over-year. "
            "In 2025, losses dropped to $83.85M but the threat persists as old drainers "
            "exit and new ones replace them. "
            "Common drainer mechanics: "
            "1. Multicall aggregation: splits asset draining across multiple calls in one "
            "transaction to bypass per-token security checks. "
            "2. Create2 temporary addresses: dynamically generates fresh addresses for each "
            "attack to evade blacklists — the destination address is unknown until signing. "
            "3. Gasless permit draining: uses Permit/Permit2 to drain tokens without "
            "requiring victim to pay gas, reducing friction. "
            "4. Prioritizes high-value assets: checks wallet for NFTs, staked positions, "
            "LP tokens, and large ERC20 balances before targeting. "
            "Traffic sources: hacked Discord servers, compromised X/Twitter accounts, "
            "fake airdrop announcements, paid advertising, Telegram phishing bots."
        ),
    },
    {
        "id":        "drainer_create2_bypass",
        "scam_type": "wallet_drainer",
        "severity":  "high",
        "title":     "Create2 dynamic address generation to bypass blacklists",
        "text": (
            "Wallet drainers use CREATE2 opcode to generate fresh temporary contract addresses "
            "for each phishing attack, making blacklist-based protection ineffective. "
            "The destination address for stolen assets is computed deterministically from "
            "a salt value but is unknown until the victim signs — the attack contract "
            "does not exist at signing time and is only deployed in the same transaction. "
            "This means no blacklist can pre-emptively block the drain address. "
            "Similarly, CREATE (not CREATE2) is used to deploy throwaway contracts that "
            "carry out the asset sweep and self-destruct immediately after. "
            "Detection indicators: transaction calls CREATE or CREATE2 opcode internally, "
            "asset transfer destination is a freshly deployed contract with zero history, "
            "contract deployed in same block as the attack transaction."
        ),
    },

    # ── HONEYPOT TOKENS ───────────────────────────────────────────────────────

    {
        "id":        "honeypot_cant_sell",
        "scam_type": "honeypot",
        "severity":  "critical",
        "title":     "Honeypot token — buy enabled, sell disabled or taxed 90%+",
        "text": (
            "Honeypot tokens allow purchases but prevent or severely penalize selling "
            "through hidden smart contract logic. "
            "Common honeypot mechanics: "
            "1. Blacklist function: owner maintains a list of addresses blocked from selling, "
            "initially empty but victims are added after buying. "
            "2. Whitelist-only selling: only owner-approved addresses can execute sells. "
            "3. Dynamic sell tax: sell tax starts at 0% to attract buyers, then owner "
            "calls a function to raise it to 90-99% making selling economically impossible. "
            "4. Transfer condition manipulation: _transfer function checks msg.sender "
            "against a hidden condition that only the owner wallet passes. "
            "5. Pause function: owner can pause all transfers except buys. "
            "Detection on-chain: DEXTools shows only green buy candles with no red sell "
            "candles. Token Sniffer honeypot simulation fails. "
            "Simulation indicator: simulated sell transaction reverts or returns zero value. "
            "The 2021 Squid Game (SQUID) token is the most famous honeypot — "
            "price pumped 45,000x before the sell function was permanently disabled."
        ),
    },
    {
        "id":        "honeypot_hidden_owner_functions",
        "scam_type": "honeypot",
        "severity":  "high",
        "title":     "Hidden owner control functions — mint, blacklist, fee manipulation",
        "text": (
            "Scam tokens contain hidden owner-privileged functions that allow post-deployment "
            "manipulation of token economics and transfer restrictions. "
            "Common dangerous owner functions: "
            "1. Unlimited mint: owner can call mint() to create unlimited new tokens, "
            "diluting all holders and enabling a dump at any time. "
            "2. Fee manipulation: setTax(), setFee(), or updateFees() allow owner to "
            "change buy/sell tax to any value including 100% after attracting investors. "
            "3. Blacklist/whitelist: addToBlacklist() blocks specific addresses from selling, "
            "addToWhitelist() restricts selling to only approved addresses. "
            "4. Trading pause: pause() or enableTrading() can halt all transfers except "
            "owner-controlled addresses. "
            "5. Liquidity removal: owner can call removeLiquidity() or rugPull() to "
            "withdraw all trading liquidity, making the token worthless instantly. "
            "Detection: unverified contract source code, owner address has unusual permissions, "
            "token contract was deployed less than 7 days ago with no audit."
        ),
    },

    # ── RUG PULLS ─────────────────────────────────────────────────────────────

    {
        "id":        "rugpull_liquidity_removal",
        "scam_type": "rug_pull",
        "severity":  "critical",
        "title":     "Liquidity rug pull — unlocked LP removal drains trading pool",
        "text": (
            "Liquidity rug pulls occur when token developers remove all liquidity from a "
            "DEX trading pool, making the token unsellable and worthless. "
            "Chainalysis estimates rug pulls caused over $2.8 billion in losses in 2025. "
            "Mechanics: developer creates token, adds ETH/BNB liquidity to Uniswap/PancakeSwap, "
            "promotes token to attract buyers, then calls removeLiquidity() to withdraw all "
            "trading funds, leaving holders with tokens that have no buyers. "
            "Key risk indicators: "
            "1. Unlocked liquidity: LP tokens held in developer wallet, not locked in "
            "a time-locked contract like Unicrypt or Team Finance. "
            "2. Short lock periods: liquidity 'locked' for 7-30 days is effectively a "
            "short-term delay, not genuine commitment. "
            "3. Concentrated LP ownership: one address controls 90%+ of liquidity. "
            "4. No audit or KYC: anonymous team with unaudited contract. "
            "Detection: check if LP tokens are locked before buying. "
            "Simulating a large sell order reveals price impact from thin liquidity."
        ),
    },
    {
        "id":        "rugpull_token_dump",
        "scam_type": "rug_pull",
        "severity":  "critical",
        "title":     "Token dump rug pull — concentrated team holdings sold into liquidity",
        "text": (
            "Token dump rug pulls occur when team or insider wallets holding large token "
            "allocations sell into the market simultaneously, crashing the price. "
            "Over 5,000 new tokens launch every day across Ethereum, Solana, Base, and BSC "
            "as of 2026, providing continuous opportunities for this attack. "
            "Mechanics: team pre-mines or receives large token allocation in deployment, "
            "promotes token through social media and influencer campaigns to attract buyers, "
            "then executes coordinated dump of all holdings in a single block or rapid "
            "succession, profiting from the inflated price before it collapses. "
            "Risk indicators: "
            "1. Top holder concentration: one or few wallets hold 20-50% of total supply. "
            "2. Team allocation without vesting: team tokens unlocked at launch. "
            "3. Fresh wallet clusters: multiple new wallets receiving large allocations "
            "from the deployer, all connected by funding source. "
            "4. Fake volume: identical trade sizes, perfectly timed buys, "
            "volume/holders ratio mismatch indicating wash trading. "
            "5. Influencer coordination: multiple paid influencers promoting simultaneously "
            "with urgency messaging and no disclosure."
        ),
    },

    # ── FAKE AIRDROP / SOCIAL ENGINEERING ────────────────────────────────────

    {
        "id":        "fake_airdrop_nft_phishing",
        "scam_type": "fake_airdrop",
        "severity":  "critical",
        "title":     "Fake airdrop NFT phishing — malicious NFT airdropped with phishing link",
        "text": (
            "Fake airdrop phishing sends unsolicited NFTs to victim wallets containing "
            "phishing links in the NFT name or external URL field. "
            "The victim sees a new NFT in their wallet, clicks to view it, lands on a "
            "phishing site, and is prompted to 'claim' associated tokens or rewards. "
            "The claim transaction is actually a setApprovalForAll or Permit signature "
            "that drains the victim's real assets. "
            "Solana variant: phishing NFTs sent to ZERO, MEMEDROP, and Bonk token holders "
            "drained $4.17M from 3,947 victims per ScamSniffer. "
            "Even when wallet simulation shows a failure warning, victims sometimes "
            "proceed — drainers exploit anti-simulation techniques to fake successful results. "
            "Detection indicators: unsolicited NFT in wallet from unknown contract, "
            "NFT contains external URL or name with a domain, "
            "claim function triggers approvals rather than transfers TO the user, "
            "domain age less than 30 days, domain uses lookalike characters."
        ),
    },
    {
        "id":        "zero_value_transfer_poisoning",
        "scam_type": "address_poisoning",
        "severity":  "high",
        "title":     "Zero-value transfer address poisoning — copy-paste wallet address theft",
        "text": (
            "Address poisoning via zero-value transfers is a 2025-2026 emerging attack vector. "
            "Over 100 million zero-value transfer attempts were recorded on BSC alone in early 2026 "
            "per ScamSniffer. "
            "Attack mechanics: attacker monitors mempool for outgoing transfers from victim. "
            "Immediately after a legitimate transfer, attacker sends a 0-value transfer FROM "
            "a lookalike address (same first and last 4-6 characters as the legitimate recipient) "
            "TO the victim's wallet. "
            "The lookalike transaction appears in the victim's transaction history. "
            "Next time the victim wants to send to the same address, they copy from history "
            "and paste the attacker's lookalike address instead of the legitimate one. "
            "Zero-value transfers cost almost nothing, allowing automation at massive scale. "
            "Detection: always verify the full 42-character address, never copy from "
            "transaction history without full verification, use address book features."
        ),
    },
    {
        "id":        "supply_chain_frontend_compromise",
        "scam_type": "supply_chain",
        "severity":  "critical",
        "title":     "Frontend compromise and supply chain attacks — malicious code injected into legitimate dApps",
        "text": (
            "Supply chain and frontend compromise attacks inject malicious transaction "
            "requests into legitimate dApp interfaces, making phishing indistinguishable "
            "from normal usage. "
            "Attack vectors tracked by ScamSniffer in 2025: "
            "1. npm package compromise: stolen npm publish credentials used to inject "
            "malicious code into open-source packages depended on by DeFi frontends. "
            "Self-replicating worms backdoored hundreds of packages, exfiltrating "
            "environment variables and private keys. "
            "2. Frontend DNS/CDN hijack: attacker takes control of a dApp's CDN or DNS "
            "to serve a malicious version of the frontend from the same URL. "
            "3. X/Twitter account compromise: project social accounts hijacked to post "
            "phishing links to fake versions of the project site. "
            "4. Bybit incident (Feb 2025, $1.46B): Lazarus Group compromised a Safe Wallet "
            "developer machine, injecting code that spoofed the multisig signing interface — "
            "17x the entire year's total signature phishing losses in one attack. "
            "Detection: transaction details in wallet should match what dApp UI shows. "
            "Any discrepancy between displayed action and wallet prompt is a critical red flag."
        ),
    },
    {
        "id":        "whale_hunting_targeted_phishing",
        "scam_type": "targeted_phishing",
        "severity":  "critical",
        "title":     "Whale hunting — targeted high-value wallet phishing replacing mass campaigns",
        "text": (
            "Phishing strategy shifted in 2025-2026 from mass retail targeting to "
            "whale hunting: fewer victims but dramatically higher per-victim losses. "
            "ScamSniffer reported November 2025 anomaly: losses surged 137% while victim "
            "count dropped 42%, with average loss per victim rising to $1,225. "
            "Signature phishing losses jumped 207% in January 2026 vs December 2025. "
            "Whale hunting mechanics: "
            "1. On-chain reconnaissance: attackers identify wallets holding $100K+ in assets "
            "by querying token balances and NFT holdings. "
            "2. Social engineering: personalized outreach via Discord, Telegram, or LinkedIn "
            "posing as investors, collaborators, or project team members. "
            "3. Fake meeting malware: 'investor call' links deploy info-stealer malware "
            "that extracts private keys and browser wallet data. "
            "4. Targeted permit requests: crafted specifically for the victim's largest "
            "holdings to maximize extraction value. "
            "AI tools have accelerated social engineering by generating convincing "
            "personalized messages at scale."
        ),
    },
    {
        "id":        "proxy_upgrade_scam",
        "scam_type": "proxy_scam",
        "severity":  "high",
        "title":     "Proxy upgrade scam — owner silently replaces contract logic post-deployment",
        "text": (
            "Proxy upgrade scams deploy an apparently legitimate upgradeable contract, "
            "attract TVL from users, then silently upgrade the implementation to malicious "
            "logic that drains all deposited funds. "
            "Mechanics: UUPS or Transparent Proxy pattern with owner-controlled upgrades. "
            "Initial implementation is legitimate and audited. "
            "After attracting significant TVL, owner calls upgradeTo() with a new "
            "implementation that adds a drain function or removes withdrawal restrictions. "
            "The upgrade transaction appears as a routine admin action with no user warning. "
            "Risk indicators: "
            "1. Upgradeable proxy with no timelock: upgrades can be executed instantly "
            "without a waiting period for users to exit. "
            "2. Single owner controls upgrade: no multisig, no governance vote required. "
            "3. No upgrade history: first upgrade since deployment is suspicious. "
            "4. Owner address is fresh wallet with no history. "
            "Detection: check if contract is a proxy, verify upgrade mechanism has timelock "
            "or multisig governance, monitor for unexpected upgrade transactions."
        ),
    },
    {
        "id":        "infinite_mint_backdoor",
        "scam_type": "rug_pull",
        "severity":  "critical",
        "title":     "Infinite mint backdoor — hidden owner mint function enables supply dilution",
        "text": (
            "Infinite mint backdoors are hidden or obfuscated mint functions in token contracts "
            "that allow the owner to create unlimited new tokens at any time. "
            "The contract appears to have a fixed supply at deployment but contains "
            "a privileged mint function callable only by the owner address. "
            "Attack sequence: deploy token with apparent fixed supply, attract buyers "
            "and liquidity, call hidden mint function to create billions of new tokens, "
            "dump newly minted tokens into the liquidity pool, drain all ETH/BNB, exit. "
            "Obfuscation techniques: "
            "1. Unverified contract: source code not published on Etherscan. "
            "2. Obfuscated function name: mint function named transferHelper(), "
            "updateRewards(), or other innocuous names. "
            "3. Proxy hidden mint: mint logic hidden in implementation contract "
            "behind a proxy that shows a different interface. "
            "Detection: verify contract source code on Etherscan, check for any "
            "function that increases totalSupply beyond initial amount, "
            "Token Sniffer mint permission check."
        ),
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion
# ─────────────────────────────────────────────────────────────────────────────

def stable_id(text: str, prefix: str = "scam") -> str:
    return f"{prefix}_{hashlib.sha256(text.encode()).hexdigest()[:16]}"


def ingest_scam_patterns(collection, embedder) -> int:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    ids, docs, metas, embeds = [], [], [], []

    for pattern in SCAM_PATTERNS:
        chunks = splitter.split_text(pattern["text"])
        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) < 40:
                continue
            doc_id = stable_id(chunk, prefix=f"scam_{pattern['id']}")
            ids.append(doc_id)
            docs.append(chunk)
            metas.append({
                "category":  "scam",
                "scam_type": pattern["scam_type"],
                "severity":  pattern["severity"],
                "source":    "AEGIS Scam Intelligence",
                "title":     pattern["title"],
            })
            embeds.append(
                embedder.encode(chunk, normalize_embeddings=True).tolist()
            )

    if ids:
        collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)
        log.info("✓ Scam patterns: %d chunks upserted.", len(ids))

    return len(ids)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Ingest scam patterns into ChromaDB")
    parser.add_argument("--ingest", action="store_true", help="Run ingestion")
    parser.add_argument("--list",   action="store_true", help="List all patterns")
    args = parser.parse_args()

    if args.list:
        print(f"\n{'─'*70}")
        print(f"{'ID':<40} {'TYPE':<20} {'SEV'}")
        print(f"{'─'*70}")
        for p in SCAM_PATTERNS:
            print(f"  {p['id']:<38} {p['scam_type']:<20} {p['severity']}")
        print(f"{'─'*70}")
        print(f"  Total: {len(SCAM_PATTERNS)} scam patterns\n")
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

        # Remove old scam chunks first (clean upsert)
        try:
            old = collection.get(where={"category": {"$eq": "scam"}})
            if old["ids"]:
                collection.delete(ids=old["ids"])
                print(f"  Deleted {len(old['ids'])} old scam chunks.")
        except Exception as e:
            print(f"  No old scam chunks to delete: {e}")

        count = ingest_scam_patterns(collection, embedder)
        print(f"\n✅ Done. {count} scam pattern chunks ingested.")
        print(f"   Total docs in collection: {collection.count()}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
