// Sample Transaction 
const sampleTransactions = [
    {
        id: "0x7a3f...8d2e",
        timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(), // 5 minutes ago
        status: "approved",
        riskLevel: "low",
        riskScore: 24,
        description: "Swap 150 USDC to AEG on Uniswap V3",
        from: "0x1a2b...3c4d",
        to: "0xUniswapV3Router02",
        gasUsed: "145,320",
        gasCost: "0.0023 ETH",
        warnings: [],
        recommendations: [
            "Slippage tolerance set to 0.5% — acceptable.",
            "Contract verified on Etherscan."
        ],
        technicalAnalysis: {
            summary: "Low-risk DeFi swap. No unusual call data. Contract is verified and widely used.",
            vulnerabilities: [],
            verification: "Passed",
            codeHash: "0x8a7d...f3b2",
            simulation: "Success"
        }
    },
    {
        id: "0x9b4c...1f7a",
        timestamp: new Date(Date.now() - 1000 * 60 * 32).toISOString(), // 32 minutes ago
        status: "rejected",
        riskLevel: "critical",
        riskScore: 92,
        description: "Mint 10,000 UNI to unverified minter contract",
        from: "0x3b4c...5d6e",
        to: "0xSuspiciousMinter",
        gasUsed: "210,000",
        gasCost: "0.0085 ETH",
        warnings: [
            "Contract not verified on Etherscan.",
            "Unlimited token approval detected.",
            "Recipient address has been flagged in 3 previous scams."
        ],
        recommendations: [
            "DO NOT PROCEED. This is a known scam pattern.",
            "Revoke any approvals immediately if already given."
        ],
        technicalAnalysis: {
            summary: "Malicious minter contract attempts to drain tokens. High-risk call data pattern matches 'approveAndCall' exploit.",
            vulnerabilities: ["Unverified contract", "Unlimited approval", "Honeypot pattern"],
            verification: "Failed",
            codeHash: "0xdead...beef",
            simulation: "Reverted (malicious)"
        }
    },
    {
        id: "0x2c5d...9e8f",
        timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(), // 2 hours ago
        status: "approved",
        riskLevel: "medium",
        riskScore: 58,
        description: "Stake 500 AEG in AEGIS staking pool",
        from: "0x5e6f...7g8h",
        to: "0xAEGISStaking",
        gasUsed: "98,450",
        gasCost: "0.0011 ETH",
        warnings: [
            "First interaction with this staking contract.",
            "Lockup period: 14 days."
        ],
        recommendations: [
            "Contract has been audited by Trail of Bits.",
            "Ensure you understand the unstaking period."
        ],
        technicalAnalysis: {
            summary: "Staking interaction. Contract audited, but lockup period applies.",
            vulnerabilities: ["Centralization risk (owner can pause)"],
            verification: "Passed",
            codeHash: "0xabcd...1234",
            simulation: "Success"
        }
    },
    {
        id: "0x8f7e...6d5c",
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), // 1 day ago
        status: "rejected",
        riskLevel: "high",
        riskScore: 81,
        description: "Transfer 2.5 ETH to address with phishing history",
        from: "0x9h8i...7j6k",
        to: "0xPhishyAddress",
        gasUsed: "21,000",
        gasCost: "0.0006 ETH",
        warnings: [
            "Recipient address associated with known phishing site 'eth-airdrop[.]scam'.",
            "Large amount to a new address."
        ],
        recommendations: [
            "Verify recipient address via trusted channels.",
            "Consider using a hardware wallet for large transfers."
        ],
        technicalAnalysis: {
            summary: "High-risk transfer to a known malicious address.",
            vulnerabilities: ["Address blacklisted", "No contract interaction"],
            verification: "Failed",
            codeHash: "N/A",
            simulation: "Warning (blacklist)"
        }
    },
    {
        id: "0x3e4f...2a1b",
        timestamp: new Date(Date.now() - 1000 * 60 * 10).toISOString(), // 10 minutes ago
        status: "approved",
        riskLevel: "safe",
        riskScore: 5,
        description: "Claim AEGIS staking rewards",
        from: "0x1a2b...3c4d",
        to: "0xAEGISStaking",
        gasUsed: "65,000",
        gasCost: "0.0009 ETH",
        warnings: [],
        recommendations: ["Rewards claimed successfully. No action needed."],
        technicalAnalysis: {
            summary: "Standard reward claim. No issues detected.",
            vulnerabilities: [],
            verification: "Passed",
            codeHash: "0xabcd...1234",
            simulation: "Success"
        }
    }
];

// Add this temporary debugging code
console.log('History.js loaded');

// Debug function to check modal when "See More" is clicked
const originalOpenModal = openTransactionModal;
openTransactionModal = function(txId) {
    console.log('Opening modal for transaction:', txId);
    const transaction = sampleTransactions.find(tx => tx.id === txId);
    console.log('Found transaction:', transaction);
    
    if (!transaction) {
        console.error('Transaction not found!');
        return;
    }
    
    // Check if modal elements exist
    console.log('Main modal element:', mainModal);
    console.log('Modal elements:');
    console.log('- modalTxId:', document.getElementById('modalTxId'));
    console.log('- modalRiskScore:', document.getElementById('modalRiskScore'));
    console.log('- modalSeverity:', document.getElementById('modalSeverity'));
    
    // Call the original function
    originalOpenModal(txId);
    
    // Check if active class was added
    setTimeout(() => {
        console.log('Modal active class after opening:', mainModal.classList.contains('active'));
        console.log('Modal display style:', window.getComputedStyle(mainModal).display);
    }, 100);
}

// Global variables for current filter state
let currentStatusFilter = 'all';
let currentRiskFilter = 'all';

// DOM elements
const transactionListEl = document.getElementById('transactionList');
const noTransactionsMsg = document.getElementById('noTransactionsMsg');
const clearFiltersBtn = document.getElementById('clearFiltersBtn');

// Status filter buttons
const statusFilterBtns = document.querySelectorAll('#statusFilters .filter-btn');
const riskFilterBtns = document.querySelectorAll('#riskFilters .filter-btn');

// Count spans
const statusAllSpan = document.getElementById('statusAll');
const statusApprovedSpan = document.getElementById('statusApproved');
const statusRejectedSpan = document.getElementById('statusRejected');
const riskAllSpan = document.getElementById('riskAll');
const riskCriticalSpan = document.getElementById('riskCritical');
const riskHighSpan = document.getElementById('riskHigh');
const riskMediumSpan = document.getElementById('riskMedium');
const riskLowSpan = document.getElementById('riskLow');
const riskSafeSpan = document.getElementById('riskSafe');

// Modals
const mainModal = document.getElementById('transactionModal');
const technicalModal = document.getElementById('technicalModal');

// ---------- Utility Functions ----------
function formatTimeAgo(timestamp) {
    const now = new Date();
    const date = new Date(timestamp);
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return `${seconds} seconds ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    const days = Math.floor(hours / 24);
    return `${days} day${days > 1 ? 's' : ''} ago`;
}

function formatFullDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
    });
}

function shortenAddress(address) {
    if (!address) return '';
    if (address.length < 10) return address;
    return address.slice(0, 6) + '...' + address.slice(-4);
}

// ---------- Filter Update and Counts ----------
function updateFilterCounts() {
    const total = sampleTransactions.length;
    const approved = sampleTransactions.filter(tx => tx.status === 'approved').length;
    const rejected = sampleTransactions.filter(tx => tx.status === 'rejected').length;
    
    statusAllSpan.textContent = total;
    statusApprovedSpan.textContent = approved;
    statusRejectedSpan.textContent = rejected;
    
    const critical = sampleTransactions.filter(tx => tx.riskLevel === 'critical').length;
    const high = sampleTransactions.filter(tx => tx.riskLevel === 'high').length;
    const medium = sampleTransactions.filter(tx => tx.riskLevel === 'medium').length;
    const low = sampleTransactions.filter(tx => tx.riskLevel === 'low').length;
    const safe = sampleTransactions.filter(tx => tx.riskLevel === 'safe').length;
    
    riskAllSpan.textContent = total;
    riskCriticalSpan.textContent = critical;
    riskHighSpan.textContent = high;
    riskMediumSpan.textContent = medium;
    riskLowSpan.textContent = low;
    riskSafeSpan.textContent = safe;
}

// Apply filters and render
function filterAndRenderTransactions() {
    let filtered = sampleTransactions;
    
    // Filter by status
    if (currentStatusFilter !== 'all') {
        filtered = filtered.filter(tx => tx.status === currentStatusFilter);
    }
    
    // Filter by risk
    if (currentRiskFilter !== 'all') {
        filtered = filtered.filter(tx => tx.riskLevel === currentRiskFilter);
    }
    
    renderTransactionList(filtered);
    
    // Show/hide no transactions message
    if (filtered.length === 0) {
        noTransactionsMsg.style.display = 'block';
    } else {
        noTransactionsMsg.style.display = 'none';
    }
}

// ---------- Render Transaction List (stacked cards) ----------
function renderTransactionList(transactions) {
    if (!transactionListEl) return;
    
    if (transactions.length === 0) {
        transactionListEl.innerHTML = ''; // clear, message shown separately
        return;
    }
    
    let html = '';
    transactions.forEach(tx => {
        const timeAgo = formatTimeAgo(tx.timestamp);
        const shortFrom = shortenAddress(tx.from);
        const shortTo = shortenAddress(tx.to);
        const riskClass = tx.riskLevel.toLowerCase();
        const statusClass = tx.status.toLowerCase();
        
        html += `
            <div class="transaction-item" data-tx-id="${tx.id}">
                <div class="transaction-header">
                    <div class="transaction-title">
                        <h3>${tx.description}</h3>
                        <span class="risk-badge ${riskClass}">${tx.riskLevel.toUpperCase()}</span>
                        <span class="status-badge ${statusClass}">${tx.status.toUpperCase()}</span>
                    </div>
                    <span class="risk-score">Risk Score: ${tx.riskScore}</span>
                </div>
                <div class="transaction-meta">
                    <span><i class="ri-user-line"></i> From: ${shortFrom}</span>
                    <span><i class="ri-arrow-right-line"></i> To: ${shortTo}</span>
                    <span><i class="ri-time-line"></i> ${timeAgo}</span>
                    <button class="see-more-btn" data-tx-id="${tx.id}">See More <i class="ri-arrow-right-s-line"></i></button>
                </div>
            </div>
        `;
    });
    
    transactionListEl.innerHTML = html;
    
    // Attach click listeners to "See More" buttons
    document.querySelectorAll('.see-more-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const txId = btn.getAttribute('data-tx-id');
            openTransactionModal(txId);
        });
    });
}

// ---------- Modal Functions ----------
function openTransactionModal(txId) {
    const transaction = sampleTransactions.find(tx => tx.id === txId);
    if (!transaction) return;
    
    // Populate main modal - with null checks to prevent errors
    const modalTxId = document.getElementById('modalTxId');
    if (modalTxId) modalTxId.textContent = transaction.id;
    
    const modalTxDate = document.getElementById('modalTxDate');
    if (modalTxDate) modalTxDate.textContent = formatFullDate(transaction.timestamp);
    
    const modalRiskScore = document.getElementById('modalRiskScore');
    if (modalRiskScore) modalRiskScore.textContent = transaction.riskScore;
    
    const modalSeverity = document.getElementById('modalSeverity');
    if (modalSeverity) {
        modalSeverity.textContent = transaction.riskLevel.toUpperCase();
        // Set the class properly - keep the existing classes and add risk level
        modalSeverity.className = `severity-badge risk-${transaction.riskLevel}`;
    }
    
    const modalStatus = document.getElementById('modalStatus');
    if (modalStatus) {
        modalStatus.textContent = transaction.status.toUpperCase();
        modalStatus.className = `status-badge ${transaction.status}`;
    }
    
    const modalContractAddress = document.getElementById('modalContractAddress');
    if (modalContractAddress) {
        const codeElement = modalContractAddress.querySelector('code');
        if (codeElement) codeElement.textContent = transaction.to;
    }
    
    const modalAnalysisSummary = document.getElementById('modalAnalysisSummary');
    if (modalAnalysisSummary) modalAnalysisSummary.textContent = transaction.technicalAnalysis.summary;
    
    // Warnings
    const warningsList = document.getElementById('modalWarningsList');
    const securityWarnings = document.querySelector('.security-warnings');
    
    if (warningsList && securityWarnings) {
        if (transaction.warnings && transaction.warnings.length > 0) {
            warningsList.innerHTML = transaction.warnings.map(w => `<li>${w}</li>`).join('');
            securityWarnings.style.display = 'block';
        } else {
            securityWarnings.style.display = 'none';
        }
    }
    
    // Recommendations
    const recommendationsList = document.getElementById('modalRecommendationsList');
    if (recommendationsList) {
        recommendationsList.innerHTML = transaction.recommendations.map(r => `<li>${r}</li>`).join('');
    }
    
    // Gas metrics
    const modalGasUsed = document.getElementById('modalGasUsed');
    if (modalGasUsed) modalGasUsed.textContent = transaction.gasUsed;
    
    const modalGasCost = document.getElementById('modalGasCost');
    if (modalGasCost) modalGasCost.textContent = transaction.gasCost;
    
    // Store current transaction for technical view
    if (mainModal) {
        mainModal.setAttribute('data-current-tx', txId);
        
        // Show modal
        mainModal.classList.add('active');
        console.log('Modal should now be visible');
    } else {
        console.error('Main modal element not found!');
    }
}

function closeMainModal() {
    mainModal.classList.remove('active');
}

function openTechnicalModal() {
    const txId = mainModal.getAttribute('data-current-tx');
    const transaction = sampleTransactions.find(tx => tx.id === txId);
    if (!transaction) return;
    
    // Populate technical modal
    const techBody = document.getElementById('technicalModalBody');
    techBody.innerHTML = `<pre class="technical-pre">${JSON.stringify(transaction.technicalAnalysis, null, 2)}</pre>`;
    
    technicalModal.classList.add('active');
}

function closeTechnicalModal() {
    technicalModal.classList.remove('active');
}

// ---------- Event Listeners ----------
// Status filter buttons
statusFilterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // Update active class
        statusFilterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Update filter
        currentStatusFilter = btn.getAttribute('data-status');
        filterAndRenderTransactions();
    });
});

// Risk filter buttons
riskFilterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        riskFilterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        currentRiskFilter = btn.getAttribute('data-risk');
        filterAndRenderTransactions();
    });
});

// Clear filters button
if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener('click', () => {
        // Reset buttons to 'all'
        statusFilterBtns.forEach(b => {
            if (b.getAttribute('data-status') === 'all') {
                b.classList.add('active');
            } else {
                b.classList.remove('active');
            }
        });
        riskFilterBtns.forEach(b => {
            if (b.getAttribute('data-risk') === 'all') {
                b.classList.add('active');
            } else {
                b.classList.remove('active');
            }
        });
        
        currentStatusFilter = 'all';
        currentRiskFilter = 'all';
        filterAndRenderTransactions();
    });
}

// Modal close buttons
document.querySelectorAll('.modal-close, .modal .close-modal').forEach(btn => {
    btn.addEventListener('click', closeMainModal);
});

// Add click handlers for technical modal close buttons
const closeTechnicalBtn = document.getElementById('closeTechnicalBtn');
if (closeTechnicalBtn) {
    closeTechnicalBtn.addEventListener('click', closeTechnicalModal);
}

const closeTechnicalModalBtn = document.getElementById('closeTechnicalModalBtn');
if (closeTechnicalModalBtn) {
    closeTechnicalModalBtn.addEventListener('click', closeTechnicalModal);
}

// View technical analysis button
const viewTechnicalBtn = document.getElementById('viewTechnicalBtn');
if (viewTechnicalBtn) {
    viewTechnicalBtn.addEventListener('click', openTechnicalModal);
}

// Close modals when clicking outside content
window.addEventListener('click', (e) => {
    if (e.target === mainModal) {
        closeMainModal();
    }
    if (e.target === technicalModal) {
        closeTechnicalModal();
    }
});

// Copy address button
const copyBtn = document.querySelector('.copy-btn');
if (copyBtn) {
    copyBtn.addEventListener('click', () => {
        const address = document.getElementById('modalContractAddress').querySelector('code').textContent;
        navigator.clipboard.writeText(address).then(() => {
            alert('Address copied to clipboard');
        }).catch(() => {
            // fallback
            prompt('Copy manually:', address);
        });
    });
}

// ---------- Initialization ----------
document.addEventListener('DOMContentLoaded', () => {
    updateFilterCounts();
    filterAndRenderTransactions();
    
    // Ensure modals are hidden initially
    if (mainModal) mainModal.classList.remove('active');
    if (technicalModal) technicalModal.classList.remove('active');
});