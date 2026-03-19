// background.js
// Extension service worker — the only place that can reach your FastAPI backend
// without CORS issues (extensions bypass CORS for declared host_permissions).

const API_BASE = 'http://127.0.0.1:8000';

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!message.aegis || message.direction !== 'page-to-bg') return false;

    // Handle async — must return true to keep the message channel open
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
            value:  txData.value,
        }),
    });

    if (!response.ok) {
        const errText = await response.text();
        console.error('[A.E.G.I.S. bg] Backend error:', response.status, errText);
        throw new Error(`Backend returned ${response.status}`);
    }

    const raw = await response.json();
    console.log('[A.E.G.I.S. bg] Raw response:', raw);

    // ── DEBUG MODE: always safe, log the full shape ──────────────────────────
    // Remove this block and return normalizeAnalysisResponse(raw) when ready
    return {
        safe:     true,
        reason:   'DEBUG — check service worker console for raw shape',
        severity: 'LOW',
        title:    'Debug mode',
        _raw:     raw,
    };

    // ── Production (uncomment when done inspecting) ──────────────────────────
    // return normalizeAnalysisResponse(raw);
}

function normalizeAnalysisResponse(raw) {
    const analysis   = raw.analysis   ?? {};
    const simulation = raw.simulation ?? {};
    const preflight  = raw.preflight  ?? {};
    const registry   = raw.trust?.registry ?? {};

    const isSafe =
        analysis.safe       !== undefined ? Boolean(analysis.safe)       :
        simulation.reverted !== undefined ? !simulation.reverted          :
        preflight.passed    !== undefined ? Boolean(preflight.passed)     :
        true;

    const reasons = [
        analysis.reason      ?? analysis.verdict  ?? null,
        simulation.revert_reason                  ?? null,
        preflight.warning                         ?? null,
        registry.flagged
            ? `Flagged in trust registry: ${registry.label ?? 'unknown'}`
            : null,
    ].filter(Boolean);

    const severity =
        analysis.severity ??
        (registry.flagged ? 'CRITICAL' : !isSafe ? 'HIGH' : 'LOW');

    return {
        safe:     isSafe,
        reason:   reasons.join(' — ') || (isSafe ? 'No issues detected.' : 'Transaction flagged.'),
        severity: severity.toUpperCase(),
        title:    analysis.title ?? (isSafe ? 'Transaction Cleared' : 'Threat Detected'),
        _raw:     raw,
    };
}