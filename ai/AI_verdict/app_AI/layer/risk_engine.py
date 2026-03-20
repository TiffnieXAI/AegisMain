def compute_risk_score(features: dict) -> dict:
    """
    Computes a risk score (0–100) AND explains how the score was built.

    This is NOT just scoring.
    This is:
        → Transparent decision-making
        → Debuggable logic
        → Future ML-ready structure

    Returns:
        {
            "score": int,
            "breakdown": dict,
            "reasons": list
        }
    """

    score = 0

    # This will store how much each signal contributed
    breakdown = {}

    # Human-readable explanations (VERY important for debugging + LLM later)
    reasons = []

    # -----------------------------
    # 1. CRITICAL SIGNALS (High Weight)
    # -----------------------------

    if features.get("grantsUnlimitedApproval"):
        breakdown["unlimitedApproval"] = 30
        score += 30
        reasons.append("Transaction grants unlimited token approval")

    if features.get("hasHighSeverityVuln"):
        breakdown["highSeverityVulnerability"] = 25
        score += 25
        reasons.append("High severity vulnerability detected in similar patterns")

    if features.get("hasScamEvidence"):
        breakdown["scamEvidence"] = 40
        score += 40
        reasons.append("Matches known scam patterns")

    # Address flagged malicious (TRUST REGISTRY)
    if features.get("isFlagged"):
        breakdown["flaggedAddress"] = 40
        score += 40
        reasons.append("Recipient address is flagged as malicious")

    # -----------------------------
    # 2. STRONG SIGNALS (Medium Weight)
    # -----------------------------

    if features.get("vulnConfidenceAvg", 0) > 0.6:
        breakdown["strongVulnConfidence"] = 15
        score += 15
        reasons.append("High confidence vulnerability match")

    if features.get("isUnusualBehavior"):
        breakdown["unusualBehavior"] = 10
        score += 10
        reasons.append("Transaction deviates from standard behavior")

    # Simulation detected risk
    if features.get("simulationHighRisk"):
        breakdown["simulationHighRisk"] = 25
        score += 25
        reasons.append("Simulation flagged this transaction as high risk")

    # Simulation warnings exist
    if features.get("hasSimulationWarnings"):
        breakdown["simulationWarnings"] = 15
        score += 15
        reasons.append("Simulation produced warnings")

    # =====================================================
    # 3. ECONOMIC / BEHAVIORAL SIGNALS (REAL EXECUTION)
    # =====================================================

    # 💸 User is losing funds (normal but still a signal)
    if features.get("userLosesFunds"):
        breakdown["fundsSpent"] = 10
        score += 10
        reasons.append("Transaction results in spending funds")

    # 📈 Contract gains funds (important in scams)
    if features.get("contractGainsFunds"):
        breakdown["contractReceivesFunds"] = 10
        score += 10
        reasons.append("Contract receives funds from user")

    # =====================================================
    # 4. TRUST SIGNALS (REPUTATION LAYER)
    # =====================================================

    # ❓ Unknown contract = mild risk
    if features.get("isUnknownContract"):
        breakdown["unknownContract"] = 10
        score += 10
        reasons.append("Interacting with unknown contract")

    # ✅ Verified safe reduces risk (VERY IMPORTANT)
    if features.get("isVerifiedSafe"):
        breakdown["verifiedSafe"] = -20
        score -= 20
        reasons.append("Contract is verified as safe")

    # =====================================================
    # 5. SUPPORTING SIGNALS (LOW IMPACT)
    # =====================================================

    if features.get("isPermitSignature"):
        breakdown["permitUsage"] = 5
        score += 5
        reasons.append("Uses permit signature (can bypass standard approvals)")

    if features.get("givesApproval"):
        breakdown["approvalAction"] = 5
        score += 5
        reasons.append("Transaction grants contract permissions")

    # =====================================================
    # 6. NORMALIZATION
    # =====================================================

    # Clamp score between 0 and 100
    final_score = max(0, min(score, 100))

    return {
        "score": final_score,
        "breakdown": breakdown,
        "reasons": reasons
    }