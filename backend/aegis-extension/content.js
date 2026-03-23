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

  
    chrome.runtime.sendMessage(event.data, (response) => {
        if (chrome.runtime.lastError) {
            console.error('[A.E.G.I.S. content] sendMessage error:', chrome.runtime.lastError.message);
            window.postMessage({ aegis: true, requestId, decision: null, error: chrome.runtime.lastError.message }, '*');
            return;
        }

        if (!response) {
            console.warn('[A.E.G.I.S. content] Empty response — retrying...');
            window.postMessage({ aegis: true, requestId, decision: null, error: 'Background returned no response' }, '*');
            return;
        }

        console.log('[A.E.G.I.S. content] Got background response:', response);

        // Relay decision (or error) back to inject.js
        // background.js calls sendResponse ONLY after popup decision —
        // so this message only fires when user clicks Accept or Reject
        window.postMessage({
            aegis:    true,
            requestId,
            decision: response.decision ?? null,
            error:    response.error    ?? null,
        }, '*');
    });
    }

  
);