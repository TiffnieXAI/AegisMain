def generate_verdict(risk: dict) -> dict:
    """
    Converts a numerical risk score into a USER-FACING decision.

    This layer is CRITICAL because:
        → This is what the USER actually sees
        → Must be simple, clear, and decisive
        → No technical ambiguity

    Input:
        risk = {
            "score": int,
            "reasons": [...]
        }

    Output:
        {
            "status": str,
            "label": str,
            "color": str,
            "message": str
        }
    """
    score = risk.get("score", 0)

    # =====================================================
    # 1. HIGH RISK (BLOCK)
    # =====================================================
    if score >= 80:
        return {
            "status": "REJECT",              # used by frontend logic
            "label": "High Risk",            # user-readable
            "color": "red",                  # UI indicator
            "message": "🚫 Do NOT sign this transaction."
        }

    # =====================================================
    # 2. MEDIUM RISK (WARNING)
    # =====================================================

    elif score >= 50:
        return {
            "status": "WARNING",
            "label": "Suspicious",
            "color": "orange",
            "message": "⚠️ This transaction may be risky. Proceed only if you trust it."

        }

    else:
        return {
            "status": "SAFE",
            "label": "Safe",
            "color": "green",
            "message": "✅ This transaction looks safe."
        }