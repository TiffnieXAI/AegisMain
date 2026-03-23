from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.layer.feature_extractor import extract_features
from app.layer.risk_engine import compute_risk_score
from app.layer.llm_reasoner import generate_explanation  # Layer 3
from app.layer.verdict_engine import generate_verdict
app = FastAPI()

# ✅ Allow frontend (VERY IMPORTANT)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze")
def analyze_from_sources(data: dict):
    """
    Accepts SEPARATE JSONs and merges internally.

    Input:
    {
        "rag": {...},
        "simulation": {...}
    }
    """

    # -----------------------------
    # 1. MERGE (NORMALIZE FORMAT)
    # -----------------------------
    combined = {
        "rag": data.get("rag", {}),
        "simulation": data.get("simulation", {})
    }

    # -----------------------------
    # 2. RUN PIPELINE (reuse logic)
    # -----------------------------
    features = extract_features(combined)
    risk = compute_risk_score(features)
    verdict = generate_verdict(risk)

    ai = generate_explanation(
        rag=combined["rag"],
        simulation=combined["simulation"],
        features=features,
        risk=risk
    )

    return {
        "verdict": verdict,
        "ai": ai,
        "meta": risk
    }