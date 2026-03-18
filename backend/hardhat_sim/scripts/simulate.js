/**
 * AEGIS — Hardhat Fork Simulation Script
 *
 * Called by Python via subprocess.  Communication is through two temp files:
 *   SIM_PARAMS_FILE  (env)  →  JSON input written by Python
 *   SIM_OUTPUT_FILE  (env)  →  JSON result written by this script, read by Python
 *
 * Steps:
 *   1. Read params (sender, to, calldata, value, real balances)
 *   2. Impersonate sender on the forked network
 *   3. Seed real DEV / native balance
 *   4. Seed real token storage slot (slot-0 mapping — covers most ERC-20s)
 *   5. Send transaction, capture receipt
 *   6. Return: success, revert_reason, gas_used, gas_price, state diff, raw logs
 */

const hre = require("hardhat");
const fs = require("fs");

// ─── helpers ─────────────────────────────────────────────────────────────────

/** Left-pad a BigInt to a 32-byte (64 hex char) hex string, WITH 0x prefix. */
function toBytes32Hex(n) {
  return "0x" + BigInt(n).toString(16).padStart(64, "0");
}

/** Convert a BigInt or number to a minimal hex string WITH 0x prefix. */
function toHex(n) {
  return "0x" + BigInt(n).toString(16);
}

/** Pull a revert reason from an ethers error object. */
function extractRevertReason(err) {
  // ethers v6 wraps revert data in err.reason or err.revert.args
  if (err.reason) return String(err.reason);
  if (err.revert && err.revert.args && err.revert.args.length > 0) {
    return String(err.revert.args[0]);
  }
  const msg = err.message || "";
  // "execution reverted: Reason string"
  const m1 = msg.match(/execution reverted:\s*(.+)/i);
  if (m1) return m1[1].trim().replace(/['"]/g, "");
  // "reverted with reason string 'Reason'"
  const m2 = msg.match(/reverted with reason string\s+'(.+?)'/i);
  if (m2) return m2[1];
  // "revert Reason"
  const m3 = msg.match(/revert\s+(.+)/i);
  if (m3) return m3[1].trim();
  return "execution reverted (no reason string)";
}

// ─── main ─────────────────────────────────────────────────────────────────────

async function main() {
  const paramsFile = process.env.SIM_PARAMS_FILE;
  const outputFile = process.env.SIM_OUTPUT_FILE;

  if (!paramsFile || !outputFile) {
    throw new Error("SIM_PARAMS_FILE and SIM_OUTPUT_FILE env vars are required");
  }

  const params = JSON.parse(fs.readFileSync(paramsFile, "utf8"));
  const {
    sender,
    to,
    data,
    value,
    real_dev_balance,   // string — wei, from Python
    token_balance_slot, // number | null
    real_token_balance, // number — raw token units
  } = params;

  const provider = hre.network.provider;   // low-level JSON-RPC provider
  const ethers   = hre.ethers;             // patched ethers bound to Hardhat network

  // ── 1. Impersonate sender ──────────────────────────────────────────────────
  await provider.request({
    method: "hardhat_impersonateAccount",
    params: [sender],
  });

  // ── 2. Seed real native balance ────────────────────────────────────────────
  await provider.request({
    method: "hardhat_setBalance",
    params: [sender, toHex(BigInt(real_dev_balance || "0"))],
  });

  // ── 3. Seed real token balance at storage slot 0 (ERC-20 mapping) ─────────
  if (token_balance_slot != null && Number(real_token_balance) > 0) {
    await provider.request({
      method: "hardhat_setStorageAt",
      params: [
        to,
        toBytes32Hex(token_balance_slot),
        toBytes32Hex(real_token_balance),
      ],
    });
  }

  // ── 4. Snapshot state BEFORE ───────────────────────────────────────────────
  const devBefore = await ethers.provider.getBalance(sender);

  // ── 5. Execute transaction ─────────────────────────────────────────────────
  const signer = await ethers.getImpersonatedSigner(sender);

  let result;
  try {
    const tx = await signer.sendTransaction({
      to,
      data: data || "0x",
      value: BigInt(value || 0),
      gasLimit: 500_000n,
    });

    const receipt = await tx.wait();
    const devAfter = await ethers.provider.getBalance(sender);

    // Serialize logs — keep topics as 0x-prefixed strings, data as hex
    const rawLogs = (receipt.logs || []).map((log) => ({
      topics: log.topics,           // string[] in ethers v6
      data:   log.data || "0x",
    }));

    result = {
      success:         true,
      reverted:        false,
      revert_reason:   null,
      gas_used:        Number(receipt.gasUsed),
      gas_price:       receipt.gasPrice ? Number(receipt.gasPrice) : null,
      dev_before:      devBefore.toString(),
      dev_after:       devAfter.toString(),
      raw_logs:        rawLogs,
      simulation_note: "Executed against forked chain state via Hardhat.",
    };
  } catch (err) {
    result = {
      success:         false,
      reverted:        true,
      revert_reason:   extractRevertReason(err),
      gas_used:        null,
      gas_price:       null,
      dev_before:      devBefore.toString(),
      dev_after:       devBefore.toString(),
      raw_logs:        [],
      simulation_note: "Transaction reverted during Hardhat fork simulation.",
    };
  }

  // ── 6. Write output ────────────────────────────────────────────────────────
  fs.writeFileSync(outputFile, JSON.stringify(result));
}

main().catch((err) => {
  const outputFile = process.env.SIM_OUTPUT_FILE;
  const errResult = {
    success:         false,
    reverted:        true,
    revert_reason:   err.message || String(err),
    gas_used:        null,
    gas_price:       null,
    dev_before:      "0",
    dev_after:       "0",
    raw_logs:        [],
    simulation_note: "Hardhat simulation script threw an unhandled error.",
  };
  if (outputFile) {
    try { fs.writeFileSync(outputFile, JSON.stringify(errResult)); } catch (_) {}
  }
  process.exit(1);
});