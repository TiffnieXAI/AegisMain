// inject.js
// Injected directly into the page's JS context (same scope as window.ethereum).
// This is the ONLY place that can wrap window.ethereum.request.
// It cannot call chrome APIs — it communicates via window.postMessage.

(function () {
    if (window.__aegisInstalled) return;
    window.__aegisInstalled = true;

    const originalRequest = window.ethereum.request.bind(window.ethereum);

    window.ethereum.request = async function (args) {
        if (args.method !== 'eth_sendTransaction') {
            return originalRequest(args);
        }

        const tx = args.params[0];

        const txData = {
            sender: tx.from   ?? null,
            to:     tx.to     ?? null,
            data:   tx.data   ?? '0x',
            value:  tx.value  ?? '0x0',
        };

        console.log('[A.E.G.I.S.] Intercepted tx:', txData);

        // Ask the background service worker to call the backend.
        // We use postMessage because inject.js has no chrome.* access.
        return new Promise((resolve, reject) => {
            const requestId = crypto.randomUUID();

            // Listen for the background's verdict (relayed via content.js)
            function onMessage(event) {
                if (
                    event.source !== window ||
                    !event.data?.aegis ||
                    event.data.requestId !== requestId
                ) return;

                window.removeEventListener('message', onMessage);

                const result = event.data;

                if (result.error) {
                    // Backend unreachable — ask user if they want to proceed
                    const proceed = confirm(
                        'A.E.G.I.S. could not analyze this transaction (server unreachable).\n\nProceed anyway?'
                    );
                    if (proceed) resolve(originalRequest(args));
                    else reject(new Error('User cancelled after analysis failure.'));
                    return;
                }

                console.log('[A.E.G.I.S.] Analysis result:', result.analysis);

                if (!result.analysis.safe) {
                    // Show a visible warning on the page
                    showThreatBanner(result.analysis);
                    reject(new Error(`[A.E.G.I.S.] Blocked: ${result.analysis.reason}`));
                    return;
                }

                console.log('[A.E.G.I.S.] Safe — forwarding to MetaMask.');
                resolve(originalRequest(args));
            }

            window.addEventListener('message', onMessage);

            // Send the tx data to content.js → background.js
            window.postMessage({
                aegis: true,
                direction: 'page-to-bg',
                requestId,
                txData,
            }, '*');
        });
    };

    // ── In-page threat banner ──────────────────────────────────────────────────
    function showThreatBanner(analysis) {
        const existing = document.getElementById('__aegis_banner');
        if (existing) existing.remove();

        const severityColor = {
            CRITICAL: '#e74c3c',
            HIGH:     '#e74c3c',
            MEDIUM:   '#f39c12',
            LOW:      '#39d98a',
        }[analysis.severity] ?? '#e74c3c';

        const banner = document.createElement('div');
        banner.id = '__aegis_banner';
        banner.style.cssText = `
            all: initial;
            position: fixed; top: 20px; right: 20px; z-index: 2147483647;
            background: #1a1a2e; border: 1.5px solid ${severityColor};
            border-radius: 12px; padding: 18px 22px; max-width: 340px;
            font-family: system-ui, sans-serif; font-size: 13px; color: #ccc;
            box-shadow: 0 8px 32px ${severityColor}44;
            animation: aegis-in .25s ease;
        `;

        banner.innerHTML = `
            <style>
                @keyframes aegis-in {
                    from { transform: translateY(-12px); opacity: 0; }
                    to   { transform: translateY(0);     opacity: 1; }
                }
            </style>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
                <span style="font-size:20px;">🛡️</span>
                <strong style="color:${severityColor};font-size:14px;">
                    ${analysis.title ?? 'Transaction Blocked'}
                </strong>
                <span style="
                    margin-left:auto; background:${severityColor}22; color:${severityColor};
                    font-size:10px; padding:2px 8px; border-radius:20px;
                    border:1px solid ${severityColor}55; text-transform:uppercase; letter-spacing:.5px;
                ">${analysis.severity ?? 'HIGH'}</span>
            </div>
            <p style="margin:0 0 12px;line-height:1.5;color:#bbb;">
                ${analysis.reason ?? 'This transaction was flagged as potentially malicious.'}
            </p>
            <div style="display:flex;justify-content:flex-end;">
                <button id="__aegis_dismiss" style="
                    background:transparent; border:1px solid #555; color:#aaa;
                    padding:5px 14px; border-radius:6px; cursor:pointer; font-size:12px;
                ">Dismiss</button>
            </div>
        `;

        document.body.appendChild(banner);
        document.getElementById('__aegis_dismiss').onclick = () => banner.remove();
        setTimeout(() => banner?.remove(), 12000);
    }

    console.log('[A.E.G.I.S.] Transaction guard active on this page.');
})();