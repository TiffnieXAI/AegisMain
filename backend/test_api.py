
# Run po mga ito::
#     # Terminal 1 — start the server
#     uvicorn app:app --reload

#     # Terminal 2 — run this
#     python test_api.py


import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"


def post(path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()}


print("1. Simple Test — GET /")
req = urllib.request.urlopen(f"{BASE_URL}/", timeout=5)
print(json.loads(req.read()))


print("2. analyze-intent w/ native transfer (0x calldata)")
result = post("/analyze-intent", {
    "sender": "0x0000000000000000000000000000000000000001",
    "to":     "0x0000000000000000000000000000000000000002",
    "data":   "0x",
    "value":  0,
})
sim = result.get("simulation", {})
print(f"intent function : {result.get('intent', {}).get('function')}")
print(f"sim success     : {sim.get('success')}")
print(f"sim note        : {sim.get('simulation_note')}")
print(f"gas_used        : {sim.get('gas_used')}")
print(
    f"trust registry  : {result.get('trust', {}).get('registry', {}).get('status')}")


print("3. analyze-intent — ERC-20 approve decode")
result = post("/analyze-intent", {
    "sender": "0x0000000000000000000000000000000000000001",
    # Use any real contract address on Moonbase Alpha here
    "to":     "0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000",
    "data":   (
        "0x095ea7b3"
        "000000000000000000000000AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "0000000000000000000000000000000000000000000000000de0b6b3a7640000"
    ),
    "value":  0,
})
intent = result.get("intent", {})
print(f"function        : {intent.get('function')}")
print(f"decoded_via     : {intent.get('decoded_via')}")
print(f"intent_summary  : {intent.get('intent_summary')}")
sim = result.get("simulation", {})
print(f"sim success     : {sim.get('success')}")
print(f"sim note        : {sim.get('simulation_note')}")

print("4. analyze-intent — unknown selector")
result = post("/analyze-intent", {
    "sender": "0x0000000000000000000000000000000000000001",
    "to":     "0x0000000000000000000000000000000000000002",
    "data":   "0xdeadbeef",
    "value":  0,
})
print(f"function        : {result.get('intent', {}).get('function')}")
print(f"decoded_via     : {result.get('intent', {}).get('decoded_via')}")
sim = result.get("simulation", {})
print(f"sim success     : {sim.get('success')}")
print(f"reverted        : {sim.get('reverted')}")
print(f"revert_reason   : {sim.get('revert_reason')}")


print("\n\nAll tests done.")
