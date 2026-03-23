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
        console.log('[A.E.G.I.S bg] AI Verdict: ', raw.ai_verdict);
        const analysis = normalizeAnalysisResponse(raw);

        // Store analysis + a pending decision slot in session storage
        await chrome.storage.session.set({
            [`pending_${requestId}`]: {
                requestId,
                txData,
                analysis,
                timestamp: Date.now()
            }
        });

        const verify = await chrome.storage.session.get(`pending_${requestId}`);
        if (!verify[`pending_${requestId}`]){
            throw new Error('Failed to write to session storage');
        }
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

        setTimeout(() => {
            if(pendingDecisions[requestId]) {
                console.warn('[A.E.G.I.S. bg] Popup timeout - cleaning up');
                delete pendingDecisions[requestId];
                chrome.storage.session.remove(`pending_${requestId}`);
                sendResponse({ error: 'User did not respond in time'});
            }
        }, 300000);
    
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
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    try {
        const response = await fetch(`${API_BASE}/analyze-full`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sender: txData.sender,
                to:     txData.to,
                data:   txData.data,
                value:  parseInt(txData.value ?? '0x0', 16),
            }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);
        if (!response.ok) {
            const errText = await response.text();
            console.error('[A.E.G.I.S. bg] Backend error:', response.status, errText);
            throw new Error(`Backend returned ${response.status}`);
        }

        return response.json();
    } catch (err) {
        clearTimeout(timeoutId);
        if(err.name == 'AbortError') {
            throw new Error('Backend request timed out.');
        }
        throw err;
    }
    
}

function normalizeAnalysisResponse(raw) {
    const aiVerdict = raw?.ai_verdict ?? { verdict: {label: 'Unknown'}};
    const simulation = raw?.simulation ?? {};
    const analysis   = raw?.analysis   ?? {};
    const registry   = raw?.trust?.registry ?? {};
    const pipeline   = raw?.pipeline   ?? {};

    // Risk tier from pipeline takes priority if available
    const riskTier = aiVerdict?.verdict?.label ?? 'Unknown';
    

    const isSafe =
        riskTier === 'High Risk'      ? false :
        riskTier === 'Suspicious'          ? false :
        simulation.reverted          ? false :
        true;

    const severity =
        riskTier === 'High Risk'                         ? 'HIGH'     :
        riskTier === 'Suspicious'                        ? 'MEDIUM'   :
        simulation?.reverted                              ? 'MEDIUM'   :
        (simulation?.warning_count > 0 || analysis?.warning_count > 0) ? 'MEDIUM' :
        registry?.is_flagged                              ? 'LOW' :
        'LOW';

    // Pull scam and vulnerability evidence from RAG if available
    const scamEvidence  = (pipeline?.scam_evidence          ?? []).map(e => e.text).filter(Boolean);
    const vulnEvidence  = (pipeline?.vulnerability_evidence ?? []).map(e => e.text).filter(Boolean);

    const title =
        riskTier === 'High Risk'     ? 'Critical risk detected'          :
        riskTier === 'Suspicious'         ? 'High risk transaction detected'   :
        simulation?.reverted         ? 'Transaction would revert'         :
        registry?.is_flagged         ? 'Flagged contract'                  :
        'Transaction looks safe';

    return {
        safe:     isSafe,
        severity: severity,
        title:    title,
        reason:   aiVerdict?.meta?.reason?.join(' — ') || (isSafe ? 'No issues detected.' : 'Transaction flagged.'),
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
        ai_verdict: aiVerdict,
        _raw: raw,
    };
}


async function testBackendConnection() {
    try {
        console.log('[A.E.G.I.S. bg] Testing backend connection...');
        const response = await fetch('http://127.0.0.1:8000/', {
            method: 'GET',
            signal: AbortSignal.timeout(5000) // 5 second timeout
        });
        
        if (response.ok) {
            console.log('[A.E.G.I.S. bg] Backend connection successful');
        } else {
            console.warn('[A.E.G.I.S. bg] Backend responded but with status:', response.status);
        }
    } catch (err) {
        console.error('[A.E.G.I.S. bg] Backend connection failed:', err.message);
        console.error('[A.E.G.I.S. bg] Make sure the backend server is running at http://127.0.0.1:8000');
    }
}


testBackendConnection();