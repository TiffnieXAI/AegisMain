// content.js
// Runs in the "content script" context — has access to chrome.runtime
// but NOT to the page's window.ethereum.
// Its only job: inject inject.js into the page, then relay messages.

// ── 1. Inject inject.js into the real page context ────────────────────────────
const script = document.createElement('script');
script.src = chrome.runtime.getURL('inject.js');
script.onload = () => script.remove();
(document.head || document.documentElement).appendChild(script);

// ── 2. Relay: page → background ───────────────────────────────────────────────
window.addEventListener('message', (event) => {
    if (
        event.source !== window ||
        !event.data?.aegis ||
        event.data.direction !== 'page-to-bg'
    ) return;

    chrome.runtime.sendMessage(
        { aegis: true, ...event.data },
        (response) => {
            // Relay the background's response back to the page
            window.postMessage({
                aegis:     true,
                requestId: event.data.requestId,
                ...response,
            }, '*');
        }
    );
});