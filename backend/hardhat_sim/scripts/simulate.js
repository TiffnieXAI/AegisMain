const hre = require("hardhat");
const fs  = require("fs");

function toBytes32Hex(n) { return "0x" + BigInt(n).toString(16).padStart(64, "0"); }
function toHex(n)        { return "0x" + BigInt(n).toString(16); }

function extractRevertReason(err) {
    if (err.reason) return String(err.reason);
    if (err.revert?.args?.length) return String(err.revert.args[0]);
    const msg = err.message || "";
    const m1 = msg.match(/execution reverted:\s*(.+)/i);
    if (m1) return m1[1].trim().replace(/['"]/g, "");
    const m2 = msg.match(/reverted with reason string\s+'(.+?)'/i);
    if (m2) return m2[1];
    return "execution reverted (no reason string)";
}

// Pull all unique addresses from log topics (potential senders/receivers)
function extractAddressesFromLogs(logs) {
    const addresses = new Set();
    for (const log of logs) {
        for (const topic of log.topics.slice(1)) {
            // Topics that are addresses are 32 bytes with 12 zero bytes padding
            if (topic.startsWith("0x000000000000000000000000")) {
                addresses.add("0x" + topic.slice(26));
            }
        }
    }
    return [...addresses];
}

async function main() {
    const paramsFile = process.env.SIM_PARAMS_FILE;
    const outputFile = process.env.SIM_OUTPUT_FILE;
    if (!paramsFile || !outputFile) throw new Error("SIM_PARAMS_FILE and SIM_OUTPUT_FILE required");

    const params = JSON.parse(fs.readFileSync(paramsFile, "utf8"));
    const { sender, to, data, value, real_dev_balance, token_balance_slot, real_token_balance } = params;

    const provider = hre.network.provider;
    const ethers   = hre.ethers;

    // ── Impersonate + seed ─────────────────────────────────────────────────
    await provider.request({ method: "hardhat_impersonateAccount", params: [sender] });
   
    const GAS_FLOOR = BigInt("2000000000000000000"); // 2 DEV — enough for any simulation
    const realBalance = BigInt(real_dev_balance || "0");
    const seedBalance = realBalance > GAS_FLOOR ? realBalance : GAS_FLOOR;

    await provider.request({
        method: "hardhat_setBalance",
        params: [sender, toHex(seedBalance)]
    });

    if (token_balance_slot != null && Number(real_token_balance) > 0) {
        await provider.request({
            method: "hardhat_setStorageAt",
            params: [to, toBytes32Hex(token_balance_slot), toBytes32Hex(real_token_balance)]
        });
    }

    // ── Snapshot BEFORE ────────────────────────────────────────────────────
    const senderEthBefore   = await ethers.provider.getBalance(sender);
    const contractEthBefore = await ethers.provider.getBalance(to);

    // Read storage slots 0-4 before (covers most ERC-20/721 balance mappings)
    const slotsBefore = {};
    for (let i = 0; i < 5; i++) {
        slotsBefore[i] = await ethers.provider.getStorage(to, i);
    }

    // ── Execute ────────────────────────────────────────────────────────────
    const signer = await ethers.getImpersonatedSigner(sender);
    let result;

    try {
        const logicAddr = "0x1dd54b55495827bf6d4b365c6a6468bcafe50627";
        const logicCode = await ethers.provider.getCode(logicAddr);
        console.error("LogicContract code length:", logicCode.length);
        console.error("LogicContract exists:", logicCode !== "0x");
        const tx = await signer.sendTransaction({
            to,
            data:     data || "0x",
            value:    BigInt(value || 0),
            gasLimit: 500_000n,
        });
        const receipt = await tx.wait();
        // After receipt = await tx.wait(), add:

        // Trace the transaction to detect dangerous opcodes (DELEGATECALL, SELFDESTRUCT, CREATE2)
        let opcodeFlags = [];
        try {
            const trace = await provider.request({
                method: "debug_traceTransaction",
                params: [receipt.hash, { disableMemory: true, disableStack: true }]
            });
            const logs = trace.structLogs || [];
            const seen = new Set();
            for (const step of logs) {
                if (!seen.has(step.op)) {
                    seen.add(step.op);
                    if (["DELEGATECALL", "SELFDESTRUCT", "CREATE", "CREATE2", "CALLCODE"].includes(step.op)) {
                        opcodeFlags.push(step.op);
                    }
                }
            }
        } catch (_) {
            // trace not available on all nodes — skip silently
        }
        // ── Snapshot AFTER ─────────────────────────────────────────────────
        const senderEthAfter   = await ethers.provider.getBalance(sender);
        const contractEthAfter = await ethers.provider.getBalance(to);

        // Read storage slots 0-4 after
        const slotsAfter = {};
        for (let i = 0; i < 5; i++) {
            slotsAfter[i] = await ethers.provider.getStorage(to, i);
        }

        // Find which slots actually changed
        const changedSlots = {};
        for (let i = 0; i < 5; i++) {
            if (slotsBefore[i] !== slotsAfter[i]) {
                changedSlots[i] = { before: slotsBefore[i], after: slotsAfter[i] };
            }
        }

        const rawLogs = (receipt.logs || []).map(log => ({
            topics: log.topics,
            data:   log.data || "0x",
            address: log.address,  // which contract emitted this
        }));

        console.error("RAW LOGS:", JSON.stringify(receipt.logs.map(l => ({
            topics: l.topics,
            data: l.data,
            address: l.address
        })), null, 2));
        // Check balances of all addresses seen in log topics
        const addressesInLogs = extractAddressesFromLogs(rawLogs);
        const balanceChanges  = {};
        for (const addr of addressesInLogs) {
            try {
                const before = await ethers.provider.getBalance(addr);
                balanceChanges[addr] = { eth_balance: before.toString() };
            } catch (_) {}
        }

        result = {
            success:            true,
            reverted:           false,
            revert_reason:      null,
            gas_used:           Number(receipt.gasUsed),
            gas_price:          receipt.gasPrice ? Number(receipt.gasPrice) : null,
            sender_eth_before:  senderEthBefore.toString(),
            sender_eth_after:   senderEthAfter.toString(),
            contract_eth_before: contractEthBefore.toString(),
            contract_eth_after:  contractEthAfter.toString(),
            changed_slots:      changedSlots,
            addresses_in_logs:  addressesInLogs,
            balance_changes:    balanceChanges,
            raw_logs:           rawLogs,
            opcode_flags:       opcodeFlags,
            simulation_note:    "Executed against forked chain state via Hardhat.",
        };

    } catch (err) {
        result = {
            success:             false,
            reverted:            true,
            revert_reason:       extractRevertReason(err),
            gas_used:            null,
            gas_price:           null,
            sender_eth_before:   senderEthBefore.toString(),
            sender_eth_after:    senderEthBefore.toString(),
            contract_eth_before: contractEthBefore.toString(),
            contract_eth_after:  contractEthBefore.toString(),
            changed_slots:       {},
            addresses_in_logs:   [],
            balance_changes:     {},
            raw_logs:            [],
            opcode_flags:       [],
            simulation_note:     "Transaction reverted during Hardhat fork simulation.",
        };
    }

    fs.writeFileSync(outputFile, JSON.stringify(result));
}

main().catch(err => {
    const outputFile = process.env.SIM_OUTPUT_FILE;
    if (outputFile) {
        fs.writeFileSync(outputFile, JSON.stringify({
            success: false, reverted: true,
            revert_reason: err.message || String(err),
            raw_logs: [], changed_slots: {}, simulation_note: "Hardhat script threw an error.",
        }));
    }
    process.exit(1);
});