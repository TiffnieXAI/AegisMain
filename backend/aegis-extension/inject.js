
(function () {
    if (window.__aegisInstalled) return;
    window.__aegisInstalled = true;

    const realDefineProperty = Object.defineProperty.bind(Object);
    Object.defineProperty = function (obj, prop, descriptor) {
        realDefineProperty(obj, prop, descriptor);
        if ((obj === window || obj === globalThis) && prop === 'ethereum') {
            const eth = descriptor.value ?? descriptor.get?.();
            if (eth && typeof eth.request === 'function') wrapRequest(eth);
        }
        return obj;
    };

    function tryWrapExisting() {
        if (window.ethereum && typeof window.ethereum.request === 'function') {
            wrapRequest(window.ethereum);
            return;
        }
        let attempts = 0;
        const interval = setInterval(() => {
            if (window.ethereum && typeof window.ethereum.request === 'function') {
                wrapRequest(window.ethereum);
                clearInterval(interval);
            }
            if (++attempts > 60) {
                clearInterval(interval);
                console.warn('[A.E.G.I.S.] window.ethereum not found after 3s.');
            }
        }, 50);
    }
    tryWrapExisting();

    function wrapRequest(eth) {
        if (eth.__aegisWrapped) return;
        eth.__aegisWrapped = true;

        const originalRequest = eth.request.bind(eth);

        eth.request = async function (args) {
            if (args.method !== 'eth_sendTransaction') {
                return originalRequest(args);
            }

            const tx = args.params[0];
            const txData = {
                sender: tx.from  ?? null,
                to:     tx.to    ?? null,
                data:   tx.data  ?? '0x',
                value:  tx.value ?? '0x0',
            };

            console.log('[A.E.G.I.S.] Intercepted tx:', txData);

            return new Promise((resolve, reject) => {
                const requestId = crypto.randomUUID();
                let settled = false;

                function settle(fn) {
                    if (settled) return;
                    settled = true;
                    clearTimeout(timeoutId);
                    window.removeEventListener('message', onReply);
                    fn();
                }

                // ── Only accept genuine replies from content.js ──────────────
                // A real reply has: aegis:true, matching requestId,
                // and either an analysis object OR an error string.
                // It does NOT have direction:'page-to-bg' (that's our outgoing msg).
                function onReply(event) {
                    if (event.source !== window)          return;
                    if (!event.data?.aegis)               return;
                    if (event.data.requestId !== requestId) return;
                    if (event.data.direction === 'page-to-bg') return; // ignore echo
                    // Must have analysis or error — ignore anything else
                    if (!('analysis' in event.data) && !('error' in event.data)) return;

                    const result = event.data;
                    console.log('[A.E.G.I.S.] Reply received:', result);

                    if (result.error) {
                        settle(() => {
                            const proceed = confirm(
                                'A.E.G.I.S. could not reach the backend.\n\nProceed anyway?'
                            );
                            if (proceed) resolve(originalRequest(args));
                            else reject(new Error('User cancelled after analysis failure.'));
                        });
                        return;
                    }

                    if (!result.analysis) {
                        console.error('[A.E.G.I.S.] Empty analysis in reply — failing open.');
                        settle(() => resolve(originalRequest(args)));
                        return;
                    }

                    console.log('[A.E.G.I.S.] Analysis result:', result.analysis);

                    if (!result.analysis.safe) {
                        settle(() => {
                            showThreatBanner(result.analysis);
                            reject(new Error('[A.E.G.I.S.] Blocked: ' + result.analysis.reason));
                        });
                        return;
                    }

                    console.log('[A.E.G.I.S.] Safe — forwarding to MetaMask.');
                    settle(() => resolve(originalRequest(args)));
                }

                window.addEventListener('message', onReply);

                // Hard timeout — fail open after 20s so the user is never stuck
                const timeoutId = setTimeout(() => {
                    console.warn('[A.E.G.I.S.] Timed out waiting for backend — failing open.');
                    settle(() => resolve(originalRequest(args)));
                }, 20000);

                window.postMessage({
                    aegis:     true,
                    direction: 'page-to-bg',
                    requestId,
                    txData,
                }, '*');
            });
        };

        console.log('[A.E.G.I.S.] window.ethereum.request wrapped successfully.');
    }

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
        banner.style.cssText = [
            'all:initial',
            'position:fixed',
            'top:20px',
            'right:20px',
            'z-index:2147483647',
            'background:#1a1a2e',
            'border:1.5px solid ' + severityColor,
            'border-radius:12px',
            'padding:18px 22px',
            'max-width:360px',
            'font-family:system-ui,sans-serif',
            'font-size:13px',
            'color:#ccc',
        ].join(';');

        banner.innerHTML =
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">' +
                '<span style="font-size:20px;all:initial;font-size:20px;">&#x1F6E1;&#xFE0F;</span>' +
                '<strong style="color:' + severityColor + ';font-size:14px;">' +
                    (analysis.title ?? 'Transaction Blocked') +
                '</strong>' +
                '<span style="margin-left:auto;background:' + severityColor + '22;color:' + severityColor + ';' +
                    'font-size:10px;padding:2px 8px;border-radius:20px;border:1px solid ' + severityColor + '55;' +
                    'text-transform:uppercase;letter-spacing:.5px;">' +
                    (analysis.severity ?? 'HIGH') +
                '</span>' +
            '</div>' +
            '<p style="margin:0 0 12px;line-height:1.5;color:#bbb;">' +
                (analysis.reason ?? 'This transaction was flagged as potentially malicious.') +
            '</p>' +
            '<div style="display:flex;justify-content:flex-end;">' +
                '<button id="__aegis_dismiss" style="background:transparent;border:1px solid #555;' +
                    'color:#aaa;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px;">' +
                    'Dismiss' +
                '</button>' +
            '</div>';

        document.body.appendChild(banner);
        document.getElementById('__aegis_dismiss').onclick = () => banner.remove();
        setTimeout(() => { if (banner.parentNode) banner.remove(); }, 12000);
    }

    console.log('[A.E.G.I.S.] Proxy trap installed — waiting for window.ethereum.');
})();