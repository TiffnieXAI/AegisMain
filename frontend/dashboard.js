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
function connectWallet(walletName) {
    const statusText = document.getElementById('walletStatusText');
    const connectBtn = document.getElementById('openModalBtn');

    // Simulate Loading
    statusText.innerText = `Connecting to ${walletName}...`;
    modal.style.display = 'none';

    setTimeout(() => {
        // Update UI to show connected state
        statusText.innerHTML = `<span style="color: #39d98a;">● Connected to ${walletName}</span><br>Address: 0x71C...4f92`;
        connectBtn.innerHTML = `<i class="ri-check-line"></i> Wallet Connected`;
        connectBtn.style.borderColor = "#39d98a";
        connectBtn.style.color = "#39d98a";

        console.log(`${walletName} connected successfully.`);

         fetchDashboardStats("0xA12F91AA001"); // Change this please kapag may wallet na
    }, 1200);
}

// lanz to -- adding dynamic data fetching for dashboard stats
// so far: total scanned, threats blocked, approved, pending, protection rate
async function fetchDashboardStats(walletAddress) {
    try {
        const response = await fetch(`http://127.0.0.1:8000/stats/${walletAddress}`);
        const data = await response.json();

        document.getElementById('totalScanned').innerText = data.total_scanned;
        document.getElementById('threatsBlocked').innerText = data.threats_blocked_today;
        document.getElementById('approved').innerText = data.approved;
        document.getElementById('pending').innerText = data.pending;
        document.getElementById('rate').innerText = data.protection_rate + '%';
    } catch (error) {
        console.error('Error fetching dashboard stats:', error);
    }
}