// popup.js — runs inside the extension popup window

const requestId = new URLSearchParams(window.location.search).get('requestId');

// ── Load analysis from session storage ────────────────────────────────────────
async function init() {
    if (!requestId) { renderError('No request ID found.'); return; }

    // Poll briefly — background.js writes to session storage just before
    // opening the window, so it's almost always ready immediately
    let pending = null;
    for (let i = 0; i < 20; i++) {
        const result = await chrome.storage.session.get(`pending_${requestId}`);
        pending = result[`pending_${requestId}`];
        if (pending) break;
        await new Promise(r => setTimeout(r, 100));
    }

    if (!pending) { renderError('Analysis data not found.'); return; }

    renderPopup(pending.txData, pending.analysis);
}

// ── Send decision back to background.js ───────────────────────────────────────
function sendDecision(decision) {
    chrome.runtime.sendMessage({
        aegis:     true,
        direction: 'popup-decision',
        requestId,
        decision,  // 'accept' or 'reject'
    });
    window.close();
}

// ── Helper functions ───────────────────────────────────────────────────────────
function getRiskColor(severity) {
    return { CRITICAL:'#dc2626', HIGH:'#ef4444', MEDIUM:'#f97316', LOW:'#22c55e' }[severity] ?? '#f97316';
}

function getTrustBadge(score) {
    if (score >= 80) return { text:'High Trust',  color:'#22c55e', bg:'rgba(34,197,94,0.1)' };
    if (score >= 60) return { text:'Medium',       color:'#f97316', bg:'rgba(249,115,22,0.1)' };
    if (score >= 40) return { text:'Low Trust',    color:'#ef4444', bg:'rgba(239,68,68,0.1)' };
    return               { text:'Untrusted',    color:'#dc2626', bg:'rgba(220,38,38,0.1)' };
}

function shortAddr(addr) {
    if (!addr) return 'N/A';
    return addr.slice(0,6) + '...' + addr.slice(-4);
}

function copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="ri-check-line" style="color:#22c55e"></i>';
        setTimeout(() => btn.innerHTML = orig, 1500);
    });
}

// ── Render ─────────────────────────────────────────────────────────────────────
function renderError(msg) {
    document.getElementById('root').innerHTML = `
        <div class="loading-state">
            <span style="color:#f87171">${msg}</span>
            <button onclick="window.close()" style="padding:8px 20px;border-radius:8px;border:1px solid rgba(255,255,255,0.1);background:transparent;color:#94a3b8;cursor:pointer;">Close</button>
        </div>`;
}

function renderPopup(txData, analysis) {
    const riskColor  = getRiskColor(analysis.severity);
    const isHighRisk = ['HIGH','CRITICAL'].includes(analysis.severity);
    const now        = new Date();
    const dateStr    = now.toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' });
    const timeStr    = now.toLocaleTimeString('en-US', { hour:'2-digit', minute:'2-digit' });

    // Build summary text from analysis_summary
    const summaryArr = analysis.analysis_summary?.summary ?? [];
    const summaryText = Array.isArray(summaryArr) && summaryArr.length > 0
        ? summaryArr.map(s => typeof s === 'string' ? s : s.detail ?? s.message ?? JSON.stringify(s)).join(' ')
        : analysis.reason ?? 'No additional analysis available.';

    // Warnings list
    const warnings = analysis.analysis_summary?.warnings ?? [];
    const warningTexts = warnings.map(w => typeof w === 'string' ? w : w.detail ?? w.message ?? w.type ?? JSON.stringify(w));

    const html = `
    <div class="popup-card">
        <div class="popup-header">
            <div class="logo-section">
                <svg width="36" height="36" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
                    <defs><linearGradient id="g" x1="0" x2="1"><stop offset="0%" stop-color="#4f46e5"/><stop offset="100%" stop-color="#06b6d4"/></linearGradient></defs>
                    <path d="M32 4l18 6v10c0 15-11 27-18 30-7-3-18-15-18-30V10z" fill="url(#g)"/>
                    <circle cx="32" cy="26" r="6" fill="rgba(255,255,255,0.9)"/>
                </svg>
                <div class="logo-text">
                    <h2>A.E.G.I.S.</h2>
                    <p>Transaction Guard</p>
                </div>
            </div>
            <button class="close-btn" id="closeBtn">&times;</button>
        </div>

        <div class="popup-content">
            <span class="tx-label">TRANSACTION ANALYSIS</span>
            <h3 class="tx-title">${analysis.title}</h3>

            <div class="address-section">
                <i class="ri-file-code-line" style="color:#8b5cf6;font-size:14px"></i>
                <span class="address-label">Contract:</span>
                <code class="address-value" style="color:#8b5cf6">${shortAddr(txData.to)}</code>
                <button class="copy-btn" data-copy="${txData.to ?? ''}"><i class="ri-file-copy-line"></i></button>
            </div>

            <div class="address-section">
                <i class="ri-user-line" style="color:#4da3ff;font-size:14px"></i>
                <span class="address-label">From:</span>
                <code class="address-value" style="color:#4da3ff">${shortAddr(txData.sender)}</code>
                <button class="copy-btn" data-copy="${txData.sender ?? ''}"><i class="ri-file-copy-line"></i></button>
            </div>

            <div class="risk-section" style="background:${riskColor}11; border-color:${riskColor}33;">
                <div>
                    <span style="color:#94a3b8;font-size:10px;text-transform:uppercase;">RISK LEVEL</span><br>
                    <span class="risk-level-badge" style="background:${riskColor};color:${analysis.severity==='MEDIUM'?'#1e293b':'white'};margin-top:6px;display:inline-block;">${analysis.severity}</span>
                </div>
                <div style="text-align:right">
                    <span style="color:#94a3b8;font-size:10px;text-transform:uppercase;">GAS COST</span><br>
                    <span style="font-size:18px;font-weight:700;color:#e2e8f0">${analysis.simulation_summary?.gas_cost ?? 'N/A'}</span>
                </div>
            </div>

            <div class="datetime-section">
                <div class="datetime-item"><i class="ri-calendar-line"></i><span>${dateStr}</span></div>
                <div class="datetime-item"><i class="ri-time-line"></i><span>${timeStr}</span></div>
            </div>

            <div class="gas-section">
                <div class="gas-card">
                    <span class="gas-label">Gas Used</span>
                    <div class="gas-value">
                        <span class="gas-number">${(analysis.simulation_summary?.gas_used ?? 0).toLocaleString()}</span>
                        <span class="gas-unit">units</span>
                    </div>
                </div>
                <div class="gas-card">
                    <span class="gas-label">Simulation</span>
                    <div class="gas-value">
                        <span class="gas-number" style="font-size:14px;color:${analysis.simulation_summary?.reverted ? '#f87171' : '#22c55e'}">
                            ${analysis.simulation_summary?.reverted ? 'Would Revert' : 'Would Succeed'}
                        </span>
                    </div>
                </div>
            </div>

            <div class="metrics-section">
                <div class="metric-card">
                    <div class="metric-header"><i class="ri-shield-star-line" style="color:#8b5cf6"></i><span>Registry</span></div>
                    <div class="metric-main">
                        <span class="metric-percentage" style="font-size:13px">${analysis.registry_summary?.status ?? 'Unknown'}</span>
                        <span class="metric-badge" style="color:${analysis.registry_summary?.is_flagged ? '#f87171' : '#22c55e'};background:${analysis.registry_summary?.is_flagged ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.1)'}">
                            ${analysis.registry_summary?.is_flagged ? 'Flagged' : analysis.registry_summary?.is_verified ? 'Verified' : 'Unknown'}
                        </span>
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-header"><i class="ri-alert-line" style="color:#f97316"></i><span>Warnings</span></div>
                    <div class="metric-main">
                        <span class="metric-percentage">${analysis.analysis_summary?.warning_count ?? 0}</span>
                        <span class="metric-badge" style="color:${(analysis.analysis_summary?.warning_count ?? 0) === 0 ? '#22c55e' : '#f97316'};background:${(analysis.analysis_summary?.warning_count ?? 0) === 0 ? 'rgba(34,197,94,0.1)' : 'rgba(249,115,22,0.1)'}">
                            ${(analysis.analysis_summary?.warning_count ?? 0) === 0 ? 'None' : 'Detected'}
                        </span>
                    </div>
                </div>
            </div>

            <div class="analysis-section">
                <div class="analysis-header"><i class="ri-shield-check-line"></i><h4>Security Analysis</h4></div>
                <p class="analysis-text">${summaryText}</p>
            </div>

            ${warningTexts.length > 0 ? `
            <div class="warnings-section">
                <div class="warnings-header" id="warningsHeader">
                    <i class="ri-alert-line"></i>
                    <h4>Security Warnings (${warningTexts.length})</h4>
                    <i class="ri-arrow-down-s-line collapse-icon" id="collapseIcon"></i>
                </div>
                <div class="warnings-content" id="warningsContent">
                    <ul class="warnings-list">
                        ${warningTexts.map(w => `<li>${w}</li>`).join('')}
                    </ul>
                </div>
            </div>` : ''}

            ${isHighRisk ? `
            <div class="risk-acknowledgment">
                <input type="checkbox" id="riskCheckbox">
                <label for="riskCheckbox">
                    <strong>I acknowledge the risks</strong>
                    This transaction has been flagged as ${analysis.severity} risk. Check this box to enable the Accept button.
                </label>
            </div>` : ''}
        </div>

        <div class="popup-footer">
            <button class="reject-btn" id="rejectBtn">Reject</button>
            <button class="accept-btn ${!isHighRisk ? 'active' : ''}" id="acceptBtn" ${isHighRisk ? 'disabled' : ''}>Accept</button>
        </div>
    </div>`;

    document.getElementById('root').innerHTML = html;
    setupListeners(analysis, isHighRisk);
}

function setupListeners(analysis, isHighRisk) {
    // Close — treat as reject
    document.getElementById('closeBtn').onclick = () => {
        sendDecision('reject');
    };

    // Copy buttons
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.onclick = (e) => { e.stopPropagation(); copyToClipboard(btn.dataset.copy, btn); };
    });

    // Warnings collapsible
    const header  = document.getElementById('warningsHeader');
    const content = document.getElementById('warningsContent');
    const icon    = document.getElementById('collapseIcon');
    if (header) {
        header.onclick = () => {
            content.classList.toggle('collapsed');
            icon.style.transform = content.classList.contains('collapsed') ? 'rotate(-90deg)' : '';
        };
    }

    // Risk checkbox
    const checkbox = document.getElementById('riskCheckbox');
    const acceptBtn = document.getElementById('acceptBtn');
    if (checkbox && acceptBtn) {
        checkbox.onchange = () => {
            acceptBtn.disabled = !checkbox.checked;
            acceptBtn.classList.toggle('active', checkbox.checked);
        };
    }

    // Reject
    document.getElementById('rejectBtn').onclick = () => {
        showConfirm('reject', () => sendDecision('reject'));
    };

    // Accept
    if (acceptBtn) {
        acceptBtn.onclick = () => {
            if (acceptBtn.disabled) return;
            showConfirm('accept', analysis, () => sendDecision('accept'));
        };
    }
}

function showConfirm(type, analysisOrCb, cb) {
    // Handle both showConfirm('reject', fn) and showConfirm('accept', analysis, fn)
    const onConfirm = typeof analysisOrCb === 'function' ? analysisOrCb : cb;
    const analysis  = typeof analysisOrCb === 'object'   ? analysisOrCb : null;

    const overlay = document.createElement('div');
    overlay.className = 'confirm-modal-overlay';

    if (type === 'reject') {
        overlay.innerHTML = `
            <div class="confirm-modal reject">
                <div class="confirm-icon">✕</div>
                <h3>Confirm Rejection</h3>
                <p>Are you sure you want to reject this transaction?</p>
                <div class="confirm-actions">
                    <button class="confirm-cancel">Cancel</button>
                    <button class="confirm-reject">Confirm Reject</button>
                </div>
            </div>`;
        overlay.querySelector('.confirm-cancel').onclick = () => overlay.remove();
        overlay.querySelector('.confirm-reject').onclick  = () => { overlay.remove(); onConfirm(); };
    } else {
        const riskColor = getRiskColor(analysis?.severity ?? 'LOW');
        overlay.innerHTML = `
            <div class="confirm-modal accept">
                <div class="confirm-icon">✓</div>
                <h3>Confirm Approval</h3>
                <p>You are about to approve a <span style="color:${riskColor};font-weight:bold">${analysis?.severity ?? 'LOW'}</span> risk transaction. Proceed?</p>
                <div class="confirm-actions">
                    <button class="confirm-cancel">Cancel</button>
                    <button class="confirm-accept">Confirm Accept</button>
                </div>
            </div>`;
        overlay.querySelector('.confirm-cancel').onclick  = () => overlay.remove();
        overlay.querySelector('.confirm-accept').onclick  = () => { overlay.remove(); onConfirm(); };
    }

    document.body.appendChild(overlay);
}

init();