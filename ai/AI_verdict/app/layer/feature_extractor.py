def extract_features(data: dict) -> dict:
    """
    Converts MULTI-SOURCE transaction intelligence into clean, usable features.

    This layer now fuses:
    - RAG (semantic understanding)
    - Simulation (actual on-chain effects)
    - Trust Registry (reputation)

    This is STILL the MOST important layer because:
    - Garbage in → garbage out
    - Clean signals → strong decisions

    Input:
    {
        "rag": {...},
        "simulation": {...}
    }

    Output:
    Structured feature dictionary
    """

    # =====================================================
    # 1. SAFE EXTRACTION (No crashes, always fallback)
    # =====================================================

    rag = data.get("rag", {})
    sim_data = data.get("simulation", {})

    simulation = sim_data.get("simulation", {})
    analysis = sim_data.get("analysis", {})
    trust = sim_data.get("trust", {}).get("registry", {})

    state = simulation.get("state_diff", {})

    # -----------------------------
    # RAG SAFE EXTRACTION
    # -----------------------------
    intent_text = rag.get("transaction_intent", "")
    intent_text = intent_text.lower()

    baseline = rag.get("standard_baseline", {})
    vulnerabilities = rag.get("vulnerability_evidence", [])
    scam = rag.get("scam_evidence", [])

    # =====================================================
    # 2. INTENT FEATURES (RAG)
    # =====================================================

    is_permit_signature = "permit" in intent_text

    grants_unlimited_approval = (
        "unlimited" in intent_text
        or "max" in intent_text
        or "infinite" in intent_text
    )

    gives_approval = (
        "approve" in intent_text
        or "allowance" in intent_text
    )

    # =====================================================
    # 3. BASELINE SIGNAL (RAG)
    # =====================================================

    baseline_confidence = baseline.get("match_confidence", 0)

    # Lower confidence → more suspicious
    is_unusual_behavior = baseline_confidence < 0.8

    # =====================================================
    # 4. VULNERABILITY ANALYSIS (RAG)
    # =====================================================

    vuln_count = len(vulnerabilities)

    has_high_severity_vuln = any(
        v.get("severity") == "high" for v in vulnerabilities
    )

    severity_levels = {"low": 1, "medium": 2, "high": 3}
    max_severity = "none"
    max_score = 0

    for v in vulnerabilities:
        sev = v.get("severity", "low")
        score = severity_levels.get(sev, 0)

        if score > max_score:
            max_score = score
            max_severity = sev

    if vuln_count > 0:
        avg_vuln_conf = sum(
            v.get("match_confidence", 0) for v in vulnerabilities
        ) / vuln_count
    else:
        avg_vuln_conf = 0

    # =====================================================
    # 5. SCAM SIGNALS (RAG)
    # =====================================================

    has_scam_evidence = len(scam)

    max_scam_conf = max(
        [s.get("match_confidence", 0) for s in scam],
        default=0
    )

    # =====================================================
    # 6. SIMULATION FEATURES (NEW 🔥)
    # =====================================================

    # 💸 How much user actually spends
    spent = state.get("sender_native_spent", {}).get("human", 0)

    # 📈 How much contract gains
    gained = state.get("contract_eth_gained", {}).get("human", 0)

    # Boolean signals
    user_loses_funds = spent > 0
    contract_gains_funds = gained > 0

    # ⚠️ Simulation warnings
    sim_warning_count = simulation.get("warning_count", 0)
    has_sim_warnings = sim_warning_count > 0

    # 🚨 Simulation risk flag
    sim_high_risk = analysis.get("high_risk", False)

    # ⛽ Gas usage (optional signal for anomalies)
    gas_used = simulation.get("gas_used", 0)

    # =====================================================
    # 7. TRUST REGISTRY FEATURES (NEW 🛡️)
    # =====================================================

    is_flagged = trust.get("is_flagged", False)
    is_verified_safe = trust.get("is_verified_safe", False)
    trust_status = trust.get("status", "Unknown")

    is_unknown_contract = trust_status == "Unknown"

    # =====================================================
    # 8. FINAL FEATURE OBJECT
    # =====================================================

    features = {
        # -------------------------
        # RAG (existing)
        # -------------------------
        "isPermitSignature": is_permit_signature,
        "grantsUnlimitedApproval": grants_unlimited_approval,
        "givesApproval": gives_approval,

        "baselineConfidence": baseline_confidence,
        "isUnusualBehavior": is_unusual_behavior,

        "numVulnerabilities": vuln_count,
        "hasHighSeverityVuln": has_high_severity_vuln,
        "maxSeverity": max_severity,
        "vulnConfidenceAvg": avg_vuln_conf,

        "hasScamEvidence": has_scam_evidence,
        "maxScamConfidence": max_scam_conf,

        # -------------------------
        # SIMULATION (NEW)
        # -------------------------
        "userLosesFunds": user_loses_funds,
        "contractGainsFunds": contract_gains_funds,
        "amountSpent": spent,
        "amountGained": gained,
        "hasSimulationWarnings": has_sim_warnings,
        "simulationWarningCount": sim_warning_count,
        "simulationHighRisk": sim_high_risk,
        "gasUsed": gas_used,

        # -------------------------
        # TRUST (NEW)
        # -------------------------
        "isFlagged": is_flagged,
        "isVerifiedSafe": is_verified_safe,
        "isUnknownContract": is_unknown_contract,
        "trustStatus": trust_status
    }

    return features