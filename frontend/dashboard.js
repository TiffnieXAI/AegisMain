const modal = document.getElementById('walletModal');
const openBtn = document.getElementById('openModalBtn');
const closeBtn = document.getElementById('closeModalBtn');

openBtn.onclick = () => modal.style.display = 'flex';
closeBtn.onclick = () => modal.style.display = 'none';

window.onclick = (event) => {
    if (event.target == modal) modal.style.display = 'none';
}

async function connectWallet(walletName) {
    const statusText = document.getElementById('walletStatusText');
    const connectBtn = document.getElementById('openModalBtn');

    if (typeof window.ethereum == 'undefined') {
        modal.style.display = 'none';
        alert('No Ethereum wallet detected. Please install MetaMask or another wallet.');
        statusText.innerText = 'No Ethereum wallet detected. Please install MetaMask or another wallet.';
        return;
    }

    if (!window.ethereum.isMetaMask) {
        modal.style.display = 'none';
        alert('MetaMask is not detected. Please install MetaMask to connect.');
        statusText.innerText = 'MetaMask is not detected. Please install MetaMask to connect.';
        return;
    }

    
    statusText.innerText = `Connecting to ${walletName}...`;
    modal.style.display = 'none';

    
    try {

        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        const walletAddress = accounts[0];
        await checkforUserAccount(walletAddress);
        const nonce = await getNonce(walletAddress);
        const signature = await signMessage(walletAddress, nonce);
        const verificationResult = await verifySignature(walletAddress, signature);

        
        if (verificationResult.message != 'Authentication successful') {
            throw new Error('Signature verification failed');
        }
        console.log('Signature verified successfully.');
    
        statusText.innerHTML = `<span style="color: #39d98a;">● Connected to ${walletName}</span><br>Address: ${walletAddress}`;
        connectBtn.innerHTML = `<i class="ri-check-line"></i> Wallet Connected`;
        connectBtn.style.borderColor = "#39d98a";
        connectBtn.style.color = "#39d98a";

        console.log(`${walletName} connected successfully.`);

        fetchDashboardStats(walletAddress);
        fetchDashboardSummaries(walletAddress);
        await syncWallet(walletAddress);
        fetchRecentAlerts(walletAddress);

        startTransactionListener(walletAddress);
    } catch (error) {
        console.error('Error connecting to wallet:', error);
        statusText.innerText = `Failed to connect to ${walletName}. Please try again.`;
        return;
    }
}

let listenerInstalled = false;
 
function startTransactionListener(walletAddress) {
    if (listenerInstalled) return;
    listenerInstalled = true;
 
    const originalRequest = window.ethereum.request.bind(window.ethereum);
 
    window.ethereum.request = async function (args) {
        if (args.method === 'eth_sendTransaction') {
            const tx = args.params[0];
 
        
            const txData = {
                from:      tx.from      ?? null,  
                to:        tx.to        ?? null,   
                data:      tx.data      ?? '0x',   
                value:     tx.value     ?? '0x0',  
                gas:       tx.gas       ?? null,
                gasPrice:  tx.gasPrice  ?? null,
                maxFeePerGas:         tx.maxFeePerGas         ?? null,
                maxPriorityFeePerGas: tx.maxPriorityFeePerGas ?? null,
                nonce:     tx.nonce     ?? null,
            };
 
            console.log('[A.E.G.I.S.] Transaction intercepted:', txData);
 
            try {
                const analysis = await analyzeTransaction(walletAddress, txData);
 
             
                console.log('[A.E.G.I.S.] Analysis result:', analysis);
 
      
                // if (!analysis.safe) {
                //     showThreatAlert(analysis);
                //     fetchDashboardStats(walletAddress);
                //     fetchRecentAlerts(walletAddress);
                //     throw new Error(`[A.E.G.I.S.] Transaction blocked: ${analysis.reason}`);
                // }
 
                console.log('[A.E.G.I.S.] Forwarding to MetaMask.');
                return originalRequest(args);
 
            } catch (error) {
                if (error.message.startsWith('[A.E.G.I.S.]')) throw error;
 
                console.warn('[A.E.G.I.S.] Analysis failed — prompting user:', error);
                const proceed = confirm(
                    'A.E.G.I.S. could not analyze this transaction (server unreachable).\n\nProceed anyway?'
                );
                if (!proceed) throw new Error('User cancelled transaction after analysis failure.');
                return originalRequest(args);
            }
        }
 
       
        return originalRequest(args);
    };
 

    window.ethereum.on('accountsChanged', (accounts) => {
        if (accounts.length === 0) {
            console.log('[A.E.G.I.S.] Wallet disconnected.');
            listenerInstalled = false;
            return;
        }
        const newAddress = accounts[0];
        console.log('[A.E.G.I.S.] Account changed to:', newAddress);
      
        listenerInstalled = false;
        startTransactionListener(newAddress);
    });
 
    console.log('[A.E.G.I.S.] Transaction listener active for:', walletAddress);
}
 

async function analyzeTransaction(walletAddress, txData) {
    console.log('[A.E.G.I.S.] Sending to /analyze-intent:', txData);
 
    const response = await fetch('http://127.0.0.1:8000/analyze-intent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            sender: txData.from,
            to:     txData.to,
            data:   txData.data,
            value:  txData.value,
        })
    });
 
    if (!response.ok) {
        const errText = await response.text();
        console.error('[A.E.G.I.S.] /analyze-intent error', response.status, errText);
        throw new Error(`Analysis endpoint returned ${response.status}`);
    }
 
    const raw = await response.json();
 
    
    console.log('[A.E.G.I.S.] Raw response:', raw);
   
    console.log('[A.E.G.I.S.] Full JSON:\n', JSON.stringify(raw, null, 2));
 
   
    return { safe: true, reason: 'DEBUG', severity: 'LOW', title: 'Debug mode', _raw: raw };
 
   
    // return normalizeAnalysisResponse(raw);
}

function normalizeAnalysisResponse(raw) {
    const analysis   = raw.analysis   ?? {};
    const simulation = raw.simulation ?? {};
    const preflight  = raw.preflight  ?? {};
    const registry   = raw.trust?.registry ?? {};

    const isSafe =
        analysis.safe          !== undefined ? Boolean(analysis.safe) :
        simulation.reverted    !== undefined ? !simulation.reverted   :
        preflight.passed       !== undefined ? Boolean(preflight.passed) :
        true;

    const reasons = [
        analysis.reason        ?? analysis.verdict ?? null,
        simulation.revert_reason                   ?? null,
        preflight.warning                          ?? null,
        registry.flagged ? `Contract flagged in trust registry: ${registry.label ?? 'unknown'}` : null,
    ].filter(Boolean);

    const severity =
        analysis.severity                     ??
        (registry.flagged   ? 'CRITICAL'   :
         !isSafe            ? 'HIGH'        : 'LOW');
 
    return {
        safe:     isSafe,
        reason:   reasons.join(' — ') || (isSafe ? 'No issues detected.' : 'Transaction flagged.'),
        severity: severity.toUpperCase(),
        title:    analysis.title ?? (isSafe ? 'Transaction Cleared' : 'Threat Detected'),
 
      
        _raw: raw,
    };
}

function showThreatAlert(analysis) {
    const existing = document.getElementById('aegis-threat-popup');
    if (existing) existing.remove();
 
    const raw        = analysis._raw        ?? {};
    const simulation = raw.simulation       ?? {};
    const preflight  = raw.preflight        ?? {};
    const registry   = raw.trust?.registry  ?? {};
    const history    = raw.history          ?? {};
 
    
    const detailRows = [
        simulation.reverted
            ? detailRow('Simulation', simulation.revert_reason ?? 'Transaction reverted', '#e74c3c')
            : null,
        preflight.warning
            ? detailRow('Preflight',  preflight.warning, '#f39c12')
            : null,
        registry.flagged
            ? detailRow('Registry',   `${registry.label ?? 'Flagged contract'} · ${registry.category ?? ''}`, '#e74c3c')
            : null,
        history.suspicious_interactions > 0
            ? detailRow('History',    `${history.suspicious_interactions} suspicious past interactions`, '#f39c12')
            : null,
    ].filter(Boolean).join('');
 
    const severityColor = {
        CRITICAL: '#e74c3c',
        HIGH:     '#e74c3c',
        MEDIUM:   '#f39c12',
        LOW:      '#39d98a',
    }[analysis.severity] ?? '#e74c3c';
 
    const popup = document.createElement('div');
    popup.id = 'aegis-threat-popup';
    popup.style.cssText = `
        position: fixed; bottom: 24px; right: 24px; z-index: 9999;
        background: #1a1a2e; border: 1px solid ${severityColor};
        border-radius: 12px; padding: 20px 24px; max-width: 380px;
        box-shadow: 0 8px 32px ${severityColor}44;
        animation: aegis-slide-in 0.3s ease;
    `;
 
    popup.innerHTML = `
        <style>
            @keyframes aegis-slide-in {
                from { transform: translateY(20px); opacity: 0; }
                to   { transform: translateY(0);    opacity: 1; }
            }
        </style>
 
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
            <span style="font-size:22px;">🛡️</span>
            <div style="flex:1;">
                <strong style="color:${severityColor}; font-size:15px; display:block;">
                    ${analysis.title ?? 'Threat Detected'}
                </strong>
                <span style="color:#888; font-size:11px;">A.E.G.I.S. Transaction Guard</span>
            </div>
            <span style="
                background:${severityColor}22; color:${severityColor};
                font-size:10px; padding:2px 8px; border-radius:20px;
                border:1px solid ${severityColor}55; text-transform:uppercase; letter-spacing:.5px;
                white-space:nowrap;
            ">${analysis.severity ?? 'HIGH'}</span>
        </div>
 
        <p style="color:#ccc; font-size:13px; margin:0 0 12px; line-height:1.5;">
            ${analysis.reason ?? 'This transaction was flagged as potentially malicious.'}
        </p>
 
        ${detailRows ? `
        <div style="border-top:1px solid #ffffff15; padding-top:10px; margin-bottom:12px; display:flex; flex-direction:column; gap:6px;">
            ${detailRows}
        </div>` : ''}
 
        <div style="display:flex; justify-content:flex-end;">
            <button onclick="document.getElementById('aegis-threat-popup').remove()" style="
                background:transparent; border:1px solid #555; color:#aaa;
                padding:5px 14px; border-radius:6px; cursor:pointer; font-size:12px;
            ">Dismiss</button>
        </div>
    `;
 
    document.body.appendChild(popup);
    setTimeout(() => popup?.remove(), 12000);
}
 
function detailRow(label, text, color) {
    return `
        <div style="display:flex; gap:8px; align-items:flex-start; font-size:12px;">
            <span style="color:${color}; min-width:64px; font-weight:500; padding-top:1px;">${label}</span>
            <span style="color:#bbb; line-height:1.4;">${text}</span>
        </div>
    `;
}
// lanz to -- adding dynamic data fetching for dashboard stats
// so far: total scanned, threats blocked, approved, pending, protection rate
async function checkforUserAccount(walletAddress) {
    try {
        const response = await fetch(`http://127.0.0.1:8000/wallets/${walletAddress}`);

        if (response.status === 404) {
            console.log("Wallet not found. Creating...");
            await createNewUser(walletAddress);
            return;
        }

        if (!response.ok) {
            throw new Error("Failed to fetch wallet");
        }

        const data = await response.json();
        console.log("Wallet exists:", data);

    } catch (error) {
        console.error('Error checking wallet:', error);
    }
}

async function createNewUser(walletAddress){
    try {
        const response = await fetch(`http://127.0.0.1:8000/wallets/`, { 
            method: 'POST',
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ wallet_address: walletAddress })
        });

        if (!response.ok) {
            const err = await response.json();
            console.warn("Wallet creation issue:", err.detail);
            return;
        }

        const data = await response.json();
        console.log("Wallet created:", data);

        return;
    } catch (error){
        console.error("Error creating wallet", error);
    }
}
async function fetchDashboardStats(walletAddress) {
    try {
        const response = await fetch(`http://127.0.0.1:8000/stats/${walletAddress}`);
        const data = await response.json();

        document.getElementById('totalScanned').innerText = data.total_scanned;
        document.getElementById('threatsBlocked').innerText = data.threats_blocked;
        document.getElementById('approved').innerText = data.safe_transactions;
        document.getElementById('pending').innerText = data.pending;
        document.getElementById('rate').innerText = data.protection_rate + '%';
    } catch (error) {
        console.error('Error fetching dashboard stats:', error);
    }
}

async function fetchDashboardSummaries(walletAddress){
    try {
        const response = await fetch(`http://127.0.0.1:8000/stats/L7D/${walletAddress}`);
        const data = await response.json();
        console.log(data);
        document.getElementById('threatsBlockedL7D').innerText = data.threats_blocked;
        document.getElementById('approvedL7D').innerText = data.transactions_approved;
        document.getElementById('summaryrate').innerText = data.protection_rate + '%';
    } catch (error){
        console.error('Error fetching dashboard summaries', error);
    }
}

async function syncWallet(walletAddress) {
    try{
        await fetch(`http://127.0.0.1:8000/sync/${walletAddress}`, { 
            method: 'POST',
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ wallet_address: walletAddress })
        });

        console.log('Wallet synced successfully.');
    } catch(error) {
        console.error('Error syncing wallet:', error);
    }
}

async function getNonce(walletAddress) {
    try {
        const response = await fetch(`http://127.0.0.1:8000/auth/nonce/${walletAddress}`);
        const data = await response.json();
        console.log('Verification Proceeding.');
        return data.nonce;
        }
    catch (error) {
        console.error('Error fetching nonce:', error);
        throw new Error('Failed to fetch nonce');
    }
}

async function signMessage(walletAddress, nonce) {
    const message = `Login to AEGIS:\nNonce: ${nonce}`;
    const signature = await window.ethereum.request({
        method: "personal_sign",
        params: [walletAddress, message]
    });
    return signature;
}

async function verifySignature(walletAddress, signature) {
    const response = await fetch(`http://127.0.0.1:8000/auth/verify/`, {
        method: 'POST',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            wallet_address: walletAddress,
            signature: signature
        })
    });
    const data = await response.json();
    // adding this para may persistence sa data
    localStorage.setItem('walletAddress', data.wallet_address);
    localStorage.setItem('authToken', signature);
    return await data;
}

async function fetchRecentAlerts(walletAddress) {
    const alertListDiv = document.querySelector('.alert-list-dash');
    try {
        const response = await fetch(`http://127.0.0.1:8000/alerts/recent/${walletAddress}?limit=3`);
        let data = await response.json();
        console.log(data);
       
        if (!Array.isArray(data)) data = [];

      
        alertListDiv.innerHTML = '';

        if (data.length === 0) {
            alertListDiv.innerHTML = `
                <div class="alert-item info">
                    <div class="alert-info">
                        <strong>No recent alerts</strong>
                        <span>You're safe!</span>
                    </div>
                    <span class="badge info">INFO</span>
                </div>
            `;
            return;
        }

        data.forEach(alert => {
            alertListDiv.innerHTML += `
                <div class="alert-item ${alert.severity.toLowerCase()}">
                    <div class="alert-info">
                        <strong>${alert.title}</strong>
                        <span>${alert.timeAgo}</span>
                    </div>
                    <span class="badge ${alert.severity.toLowerCase()}">${alert.severity}</span>
                </div>
            `;
        });

    } catch (error) {
        console.error('Error fetching recent alerts:', error);
        alertListDiv.innerHTML = `
            <div class="alert-item info">
                <div class="alert-info">
                    <strong>Failed to fetch alerts</strong>
                    <span>Please try again later</span>
                </div>
                <span class="badge info">INFO</span>
            </div>
        `;
    }
}