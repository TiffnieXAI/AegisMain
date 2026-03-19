// background.js

// Keep the service worker alive — Chrome suspends it after ~30s of inactivity.
// This dummy alarm wakes it up every 20 seconds.
chrome.alarms.create('keepAlive', { periodInMinutes: 0.33 });
chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === "keepAlive") console.log("[A.E.G.I.S. bg] Keepalive ping.");
});

console.log("[A.E.G.I.S. bg] Service worker started.");

const API_BASE = 'http://127.0.0.1:8000';

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!message.aegis || message.direction !== 'page-to-bg') return false;

    analyzeTransaction(message.txData)
        .then((analysis) => sendResponse({ analysis }))
        .catch((err)     => sendResponse({ error: err.message }));

    return true;
});

async function analyzeTransaction(txData) {
    const response = await fetch(`${API_BASE}/analyze-intent`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            sender: txData.sender,
            to:     txData.to,
            data:   txData.data,
            value:  parseInt(txData.value ?? '0x0', 16),
        }),
    });

    if (!response.ok) {
        const errText = await response.text();
        console.error('[A.E.G.I.S. bg] Backend error:', response.status, errText);
        throw new Error(`Backend returned ${response.status}`);
    }

    const raw = await response.json();
    console.log('[A.E.G.I.S. bg] Raw response:', raw);

    return normalizeAnalysisResponse(raw);
}

// ── Normalizer — field paths matched to the actual backend response shape ──────
//
// raw shape:
// {
//   target_address, sender_address,
//   preflight:  { sender_balance_dev, sender_is_active, sender_tx_count },
//   simulation: { success, reverted, revert_reason, gas_used, warnings,
//                 warning_count, value_flows, opcode_flags, state_diff },
//   analysis:   { warnings, warning_count, summary, high_risk, opcode_flags },
//   history:    { past_transfers, past_approvals, sample_recipients },
//   trust:      { registry: { status, is_flagged, is_verified_safe, error } }
// }

function normalizeAnalysisResponse(raw) {
    const simulation = raw.simulation ?? {};
    const analysis   = raw.analysis   ?? {};
    const registry   = raw.trust?.registry ?? {};

    // ── Safe / unsafe verdict ──────────────────────────────────────────────────
    // Priority: simulation revert → analysis high_risk → registry flagged → safe
    const isSafe =
        simulation.reverted      ? false :
        analysis.high_risk       ? false :
        registry.is_flagged      ? false :
        true;

    // ── Severity ───────────────────────────────────────────────────────────────
    const severity =
        registry.is_flagged                           ? 'CRITICAL' :
        simulation.reverted || analysis.high_risk     ? 'HIGH'     :
        (simulation.warning_count > 0 ||
         analysis.warning_count   > 0)                ? 'MEDIUM'   :
        'LOW';

    // ── Human-readable reason ──────────────────────────────────────────────────
    const reasons = [
        simulation.reverted && simulation.revert_reason
            ? 'Simulation reverted: ' + simulation.revert_reason
            : null,
        analysis.high_risk
            ? 'High risk detected by analysis'
            : null,
        ...(analysis.warnings  ?? []).map(w => typeof w === 'string' ? w : w.message ?? w.msg ?? JSON.stringify(w)),
        ...(simulation.warnings ?? []).map(w => typeof w === 'string' ? w : w.message ?? w.msg ?? JSON.stringify(w)),
        registry.is_flagged
            ? 'Contract flagged in trust registry (status: ' + registry.status + ')'
            : null,
    ].filter(Boolean);

    // ── Title ──────────────────────────────────────────────────────────────────
    const title =
        simulation.reverted  ? 'Transaction would revert'      :
        analysis.high_risk   ? 'High risk transaction detected' :
        registry.is_flagged  ? 'Flagged contract'               :
        'Transaction looks safe';

    return {
        safe:     isSafe,
        severity: severity,
        title:    title,
        reason:   reasons.join(' — ') || (isSafe ? 'No issues detected.' : 'Transaction flagged.'),
        // Extra fields for the dashboard threat popup detail rows
        simulation_summary: {
            gas_used:      simulation.gas_used,
            gas_cost:      simulation.gas_cost?.formatted,
            warning_count: simulation.warning_count,
            reverted:      simulation.reverted,
            revert_reason: simulation.revert_reason,
        },
        analysis_summary: {
            warning_count: analysis.warning_count,
            high_risk:     analysis.high_risk,
            warnings:      analysis.warnings,
            summary:       analysis.summary,
        },
        registry_summary: {
            status:       registry.status,
            is_flagged:   registry.is_flagged,
            is_verified:  registry.is_verified_safe,
        },
        _raw: raw,
    };
}