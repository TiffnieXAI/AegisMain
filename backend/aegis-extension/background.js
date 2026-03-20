// background.js
const API_BASE = 'http://127.0.0.1:8000';

chrome.alarms.create('keepAlive', { periodInMinutes: 0.33 });
chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === 'keepAlive') console.log('[A.E.G.I.S. bg] Keepalive ping.');
});

console.log('[A.E.G.I.S. bg] Service worker started.');

// Pending decisions keyed by requestId
// When the popup posts accept/reject, we look up the right sendResponse here
const pendingDecisions = {};

// ── 1. Handle tx analysis requests from content.js ────────────────────────────
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!message.aegis) return false;

    if (message.direction === 'page-to-bg') {
        handleTxAnalysis(message, sendResponse);
        return true; // keep channel open for async
    }

    if (message.direction === 'popup-decision') {
        handlePopupDecision(message);
        return false;
    }

    return false;
});

async function handleTxAnalysis(message, sendResponse) {
    const { requestId, txData } = message;

    try {
        const raw = await fetchAnalysis(txData);
        console.log('[A.E.G.I.S. bg] Raw response:', raw);
        const analysis = normalizeAnalysisResponse(raw);

        // Store analysis + a pending decision slot in session storage
        await chrome.storage.session.set({
            [`pending_${requestId}`]: {
                requestId,
                txData,
                analysis,
            }
        });

        // Register the sendResponse so popup decision can resolve it
        pendingDecisions[requestId] = sendResponse;

        // Open the approval popup
        chrome.windows.create({
            url:    chrome.runtime.getURL(`popup.html?requestId=${requestId}`),
            type:   'popup',
            width:  420,
            height: 720,
            focused: true,
        });

    } catch (err) {
        console.error('[A.E.G.I.S. bg] Analysis failed:', err);
        sendResponse({ error: err.message });
    }
}

function handlePopupDecision(message) {
    const { requestId, decision } = message; // decision: 'accept' | 'reject'
    const sendResponse = pendingDecisions[requestId];
    if (!sendResponse) return;

    delete pendingDecisions[requestId];
    chrome.storage.session.remove(`pending_${requestId}`);

    // Send the decision (not the analysis) back to content.js -> inject.js
    // inject.js now waits for { decision: 'accept'|'reject' }, not { analysis }
    sendResponse({ decision });
}

// ── 2. Fetch and normalize ─────────────────────────────────────────────────────
async function fetchAnalysis(txData) {
    const response = await fetch(`${API_BASE}/analyze-full`, {
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

    return response.json();
}

function normalizeAnalysisResponse(raw) {
    const simulation = raw.simulation ?? {};
    const analysis   = raw.analysis   ?? {};
    const registry   = raw.trust?.registry ?? {};
    const pipeline   = raw.pipeline   ?? {};

    // Risk tier from pipeline takes priority if available
    const riskTier = pipeline.risk_tier ?? null;

    const isSafe =
        riskTier === 'CRITICAL'      ? false :
        riskTier === 'HIGH'          ? false :
        simulation.reverted          ? false :
        analysis.high_risk           ? false :
        registry.is_flagged          ? false :
        true;

    const severity =
        riskTier === 'CRITICAL'                          ? 'CRITICAL' :
        riskTier === 'HIGH'                              ? 'HIGH'     :
        riskTier === 'MEDIUM'                            ? 'MEDIUM'   :
        registry.is_flagged                              ? 'CRITICAL' :
        simulation.reverted || analysis.high_risk        ? 'HIGH'     :
        (simulation.warning_count > 0 || analysis.warning_count > 0) ? 'MEDIUM' :
        'LOW';

    // Pull scam and vulnerability evidence from RAG if available
    const scamEvidence  = (pipeline.scam_evidence          ?? []).map(e => e.text).filter(Boolean);
    const vulnEvidence  = (pipeline.vulnerability_evidence ?? []).map(e => e.text).filter(Boolean);

    const reasons = [
        simulation.reverted && simulation.revert_reason
            ? 'Simulation reverted: ' + simulation.revert_reason : null,
        analysis.high_risk ? 'High risk detected' : null,
        ...(analysis.warnings  ?? []).map(w => typeof w === 'string' ? w : w.detail ?? w.message ?? w.type ?? JSON.stringify(w)),
        ...(simulation.warnings ?? []).map(w => typeof w === 'string' ? w : w.detail ?? w.message ?? w.type ?? JSON.stringify(w)),
        registry.is_flagged ? 'Flagged in trust registry: ' + registry.status : null,
        ...scamEvidence,
        ...vulnEvidence,
    ].filter(Boolean);

    const title =
        riskTier === 'CRITICAL'     ? 'Critical risk detected'          :
        riskTier === 'HIGH'         ? 'High risk transaction detected'   :
        simulation.reverted         ? 'Transaction would revert'         :
        registry.is_flagged         ? 'Flagged contract'                  :
        'Transaction looks safe';

    return {
        safe:     isSafe,
        severity: severity,
        title:    title,
        reason:   reasons.join(' — ') || (isSafe ? 'No issues detected.' : 'Transaction flagged.'),
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
            warnings:      analysis.warnings ?? [],
            summary:       analysis.summary  ?? [],
        },
        registry_summary: {
            status:      registry.status,
            is_flagged:  registry.is_flagged,
            is_verified: registry.is_verified_safe,
        },
        // RAG pipeline results — shown in popup detail rows
        rag_summary: {
            risk_tier:    riskTier,
            rag_status:   pipeline.rag_status,
            intent:       pipeline.transaction_intent,
            scam_matches: scamEvidence,
            vuln_matches: vulnEvidence,
            llm_context:  pipeline.llm_context,
        },
        _raw: raw,
    };
}