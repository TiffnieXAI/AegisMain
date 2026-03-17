// Modal Logic
const modal = document.getElementById('walletModal');
const openBtn = document.getElementById('openModalBtn');
const closeBtn = document.getElementById('closeModalBtn');

openBtn.onclick = () => modal.style.display = 'flex';
closeBtn.onclick = () => modal.style.display = 'none';

// Close modal if user clicks outside of it
window.onclick = (event) => {
    if (event.target == modal) modal.style.display = 'none';
}

// Wallet Connection Simulation
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

    // Simulate Loading
    statusText.innerText = `Connecting to ${walletName}...`;
    modal.style.display = 'none';

    try {
        // requesting a wallet connection here
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        const walletAddress = accounts[0];

        const nonce = await getNonce(walletAddress);
        const signature = await signMessage(walletAddress, nonce);
        const verificationResult = await verifySignature(walletAddress, signature);

        // successfull connection proceeds
        statusText.innerHTML = `<span style="color: #39d98a;">● Connected to ${walletName}</span><br>Address: ${walletAddress}`;
        connectBtn.innerHTML = `<i class="ri-check-line"></i> Wallet Connected`;
        connectBtn.style.borderColor = "#39d98a";
        connectBtn.style.color = "#39d98a";

        console.log(`${walletName} connected successfully.`);

        fetchDashboardStats("0xA12F91AA001"); // Change this please kapag may wallet na

        await syncWallet(walletAddress);
    } catch (error) {
        console.error('Error connecting to wallet:', error);
        statusText.innerText = `Failed to connect to ${walletName}. Please try again.`;
        return;
    }
}

// lanz to -- adding dynamic data fetching for dashboard stats
// so far: total scanned, threats blocked, approved, pending, protection rate
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
        return data.nonce;
        }
    catch (error) {
        console.error('Error fetching nonce:', error);
        throw new Error('Failed to fetch nonce');
    }
}

async function signMessage(walletAddres, nonce) {
    const message = `Login to AEGIS:\nNonce: ${nonce}`;
    const signature = await window.ethereum.request({
        method: "personal_sign",
        params: [message, walletAddress]
    });
    return signature;
}

async function verifySignature(walletAddress, signature) {
    const response = await fetch(`hhtp://127.0.0.1:8000/auth/verify`, {
        method: 'POST',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            wallet_address: walletAddress,
            signature: signature
        })
    });

    return await response.json();
}