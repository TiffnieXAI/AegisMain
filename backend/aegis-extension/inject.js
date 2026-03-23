// inject.js
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

            // ── Show loading banner immediately ───────────────────────────────
            showLoadingBanner();

            return new Promise((resolve, reject) => {
                const requestId = crypto.randomUUID();
                let settled = false;

                function settle(fn) {
                    if (settled) return;
                    settled = true;
                    clearTimeout(timeoutId);
                    window.removeEventListener('message', onReply);
                    removeLoadingBanner();
                    fn();
                }

                function onReply(event) {
                    if (event.source !== window)               return;
                    if (!event.data?.aegis)                    return;
                    if (event.data.requestId !== requestId)    return;
                    if (event.data.direction === 'page-to-bg') return;
                    if (!('decision' in event.data) && !('error' in event.data)) return;

                    console.log('[A.E.G.I.S.] Decision received:', event.data);

                    if (event.data.error) {
                        settle(() => {
                            const proceed = confirm(
                                'A.E.G.I.S. could not reach the backend.\n\nProceed anyway?'
                            );
                            if (proceed) resolve(originalRequest(args));
                            else reject(new Error('User cancelled after analysis failure.'));
                        });
                        return;
                    }

                    if (event.data.decision === 'accept') {
                        console.log('[A.E.G.I.S.] User accepted — forwarding to MetaMask.');
                        settle(() => resolve(originalRequest(args)));
                    } else {
                        console.log('[A.E.G.I.S.] User rejected — transaction blocked.');
                        settle(() => reject(new Error('[A.E.G.I.S.] Transaction rejected by user.')));
                    }
                }

                window.addEventListener('message', onReply);

                // Hard timeout — 5 minutes (user may be reading the popup)
                const timeoutId = setTimeout(() => {
                    console.warn('[A.E.G.I.S.] Popup timed out after 5min — blocking tx.');
                    settle(() => reject(new Error('[A.E.G.I.S.] Timed out waiting for user decision.')));
                }, 300000);

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

    // ── Loading banner ─────────────────────────────────────────────────────────
    function showLoadingBanner() {
        const existing = document.getElementById('__aegis_loading');
        if (existing) return;

        const banner = document.createElement('div');
        banner.id = '__aegis_loading';
        banner.style.cssText = [
            'all:initial',
            'position:fixed',
            'bottom:24px',
            'right:24px',
            'z-index:2147483647',
            'background:#1a1a2e',
            'border:1.5px solid #4f46e5',
            'border-radius:12px',
            'padding:14px 18px',
            'font-family:system-ui,sans-serif',
            'font-size:13px',
            'color:#a5b4fc',
            'display:flex',
            'align-items:center',
            'gap:12px',
            'box-shadow:0 8px 32px rgba(79,70,229,0.3)',
            'animation:aegis-in .2s ease',
        ].join(';');

        banner.innerHTML =
            '<style>' +
                '@keyframes aegis-in{from{transform:translateY(10px);opacity:0}to{transform:translateY(0);opacity:1}}' +
                '@keyframes aegis-spin{to{transform:rotate(360deg)}}' +
            '</style>' +
            '<div style="all:initial;width:18px;height:18px;border:2px solid rgba(79,70,229,0.3);border-top-color:#4f46e5;border-radius:50%;animation:aegis-spin .7s linear infinite;flex-shrink:0"></div>' +
            '<div style="all:initial;font-family:system-ui,sans-serif;">' +
                '<div style="font-size:13px;font-weight:600;color:#a5b4fc;">A.E.G.I.S. Analyzing...</div>' +
                '<div style="font-size:11px;color:#6366f1;margin-top:2px;">Simulating transaction on-chain</div>' +
            '</div>';

        document.body.appendChild(banner);
    }



    function removeLoadingBanner() {
        const banner = document.getElementById('__aegis_loading');
        if (banner) {
            banner.style.opacity = '0';
            banner.style.transform = 'translateY(10px)';
            banner.style.transition = 'opacity .2s, transform .2s';
            setTimeout(() => banner?.remove(), 200);
        }
    }

    console.log('[A.E.G.I.S.] Proxy trap installed — waiting for window.ethereum.');
})();