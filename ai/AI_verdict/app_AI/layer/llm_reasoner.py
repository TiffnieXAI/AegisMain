from google import genai
from app.config import GEMINI_API_KEY
import json
import re
# Initialize client
client = genai.Client(api_key=GEMINI_API_KEY)


def generate_explanation(rag: dict, simulation: dict, features: dict, risk: dict) -> dict:
    """
    Uses Gemini to generate a human-readable explanation.

    IMPORTANT:
    - Does NOT compute risk
    - ONLY explains based on:
        → Intent (RAG)
        → Actual behavior (Simulation)
        → Final decision (Risk engine)

    This keeps your system:
        Deterministic (logic) + Explainable (AI)
    """
    # =====================================================
    # 1. EXTRACT CLEAN CONTEXT (VERY IMPORTANT)
    # =====================================================

    intent = rag.get("transaction_intent", "Unknown action")

    state = simulation.get("simulation", {}).get("state_diff", {})
    trust = simulation.get("trust", {}).get("registry", {})

    # Safe extraction
    spent = state.get("sender_native_spent", {}).get("formatted", "unknown amount")
    gained = state.get("contract_eth_gained", {}).get("formatted", "unknown amount")

    trust_status = trust.get("status", "Unknown")

    # =====================================================
    # 2. BUILD CONTROLLED PROMPT (LESS NOISE = BETTER OUTPUT)
    # =====================================================
    prompt = f"""
    You are a Web3 security assistant.

    Explain the transaction clearly for a normal user.

    Context:
    - User action: {intent}
    - Funds spent: {spent}
    - Funds received by contract: {gained}
    - Contract status: {trust_status}
    - Risk level: {risk.get("score")}/100
    - Key concerns: {risk.get("reasons")}

    ---

    Explain:

    1. What this transaction is doing
    2. Why it is risky (if it is)
    3. What could happen to the user
    4. Final recommendation

    Rules:
    - Non-technical language
    - Be direct
    - No fluff
    - Do NOT mention "features", "scores", or internal analysis

    Respond ONLY in JSON:

    {{
      "what_is_happening": "",
      "why_risky": "",
      "what_can_happen": "",
      "recommendation": ""
    }}
    """

    # -----------------------------
    # CALL GEMINI (NEW STYLE)
    # -----------------------------
    response = client.models.generate_content(
        model="gemini-3-flash-preview",  # or "gemini-1.5-flash"
        contents=prompt
    )

    raw = response.text.strip()

    # =====================================================
    # 4. SAFE JSON EXTRACTION (CRITICAL FIX)
    # =====================================================

    json_match = re.search(r"\{.*\}", raw, re.DOTALL)

    if json_match:
        json_text = json_match.group(0)
    else:
        json_text = raw

    try:
        parsed = json.loads(json_text)
    except:
        # Fallback (never crash system)
        parsed = {
            "what_is_happening": raw,
            "why_risky": "",
            "what_can_happen": "",
            "recommendation": "Unknown"
        }

    return parsed