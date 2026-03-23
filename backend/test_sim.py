

# Usage:
#     python test_sim.py


import json
from aegis import simulate_with_hardhat


NATIVE_TRANSFER = {
    # any address with balance on Moonbase
    "sender": "0x0000000000000000000000000000000000000001",
    "to":     "0x0000000000000000000000000000000000000002",
    "data":   "0x",
    "value":  0,
}

ERC20_APPROVE = {
    "sender": "0xYOUR_MOONBASE_ADDRESS",
    "to":     "0xYOUR_TOKEN_CONTRACT",
    "data":   (
        # approve(address,uint256)
        "0x095ea7b3"
        "000000000000000000000000SPENDER_ADDRESS_WITHOUT_0x"     # spender
        # 1 token (18 dec)
        "0000000000000000000000000000000000000000000000000de0b6b3a7640000"
    ),
    "value":  0,
}


def run(label, **kwargs):
    print(f"TEST: {label}")
    result = simulate_with_hardhat(**kwargs)
    print(json.dumps(result, indent=2))
    print(f"\nsimulation_note: {result['simulation_note']}")
    print(f"success: {result['success']}  |  reverted: {result['reverted']}")
    if result.get("gas_used"):
        print(f"gas_used: {result['gas_used']}")
    if result.get("events_emitted"):
        print(f"events: {result['events_emitted']}")


if __name__ == "__main__":
    run("Native transfer (no calldata)", **NATIVE_TRANSFER)
    # run("ERC-20 approve", **ERC20_APPROVE)
