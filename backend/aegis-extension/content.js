// content.js

const script = document.createElement('script');
script.src = chrome.runtime.getURL('inject.js');
script.onload = () => script.remove();
(document.head || document.documentElement).appendChild(script);

window.addEventListener('message', (event) => {
    if (
        event.source !== window ||
        !event.data?.aegis ||
        event.data.direction !== 'page-to-bg'
    ) return;

    const requestId = event.data.requestId;
    console.log('[A.E.G.I.S. content] Relaying to background:', requestId);

    // Retry sendMessage up to 3 times — service worker may be waking from suspension
    // which causes the first sendMessage to return undefined
    function trySend(attemptsLeft) {
        chrome.runtime.sendMessage(event.data, (response) => {
            if (chrome.runtime.lastError) {
                console.error('[A.E.G.I.S. content] sendMessage error:', chrome.runtime.lastError.message);
                if (attemptsLeft > 0) {
                    console.log('[A.E.G.I.S. content] Retrying... (' + attemptsLeft + ' left)');
                    setTimeout(() => trySend(attemptsLeft - 1), 500);
                } else {
                    window.postMessage({ aegis: true, requestId, analysis: null, error: chrome.runtime.lastError.message }, '*');
                }
                return;
            }

            if (!response) {
                // Service worker returned undefined — still waking up, retry
                console.warn('[A.E.G.I.S. content] Empty response from background — worker waking, retrying...');
                if (attemptsLeft > 0) {
                    setTimeout(() => trySend(attemptsLeft - 1), 800);
                } else {
                    window.postMessage({ aegis: true, requestId, analysis: null, error: 'Background returned no response' }, '*');
                }
                return;
            }

            console.log('[A.E.G.I.S. content] Got background response:', response);
            window.postMessage({
                aegis:    true,
                requestId,
                analysis: response.analysis ?? null,
                error:    response.error    ?? null,
            }, '*');
        });
    }

    trySend(3);  // up to 3 retries
});