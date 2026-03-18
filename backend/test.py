import requests

rpc_url = "https://rpc.api.moonbase.moonbeam.network"

payload = {
    "jsonrpc": "2.0",
    "method": "debug_traceCall",
    "params": [
        {
            "from": "0x0000000000000000000000000000000000000000",
            "to": "0x0000000000000000000000000000000000000000",
            "data": "0x"
        },
        "latest",
        {"tracer": "callTracer"}
    ],
    "id": 1
}

resp = requests.post(rpc_url, json=payload).json()
print(resp)
