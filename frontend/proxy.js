const originalRequest = window.ethereum.request;

window.ethereum.request = async (args) => {
    if (args.method === 'eth_sendTransaction') {
        console.log("Intercepted tx:", args.params);

        const tx = args.params[0];
        const sender = tx.from;
        const contract = tx.to;
        const calldata = tx.data;
        const value = tx.value;

        const isSafe = await analyzeTx(sender, contract, calldata, value);


        const res = await fetch("http://127.0.0.1:8000/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(tx)
        });

        const result = await res.json();

        if (result.risk === "HIGH") {
            alert("⚠️ Dangerous transaction blocked!");
            return; // stop execution
        }
    }

    return originalRequest(args);
};

