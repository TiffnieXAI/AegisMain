// Global variables for current filter state
let currentStatusFilter = 'all';
let currentRiskFilter = 'all';
let transactions = [];

// // Mappings for DB Integers to Frontend Strings
const STATUS_MAP = {
    0: "rejected",
    1: "approved",
};
const RISK_MAP = {
    0: "safe",
    1: "low",
    2: "medium",
    3: "high",
    4: "critical",
    5: "unknown"
};


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
const riskUnknownSpan = document.getElementById('riskUnknown');

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
    const total = transactions.length;
    const approved = transactions.filter(tx => tx.status === 1).length;
    const rejected = transactions.filter(tx => tx.status === 2).length;
    
    statusAllSpan.textContent = total;
    statusApprovedSpan.textContent = approved;
    statusRejectedSpan.textContent = rejected;
    
    const critical = transactions.filter(tx => tx.risk_level === 4).length;
    const high = transactions.filter(tx => tx.risk_level === 3).length;
    const medium = transactions.filter(tx => tx.risk_level === 2).length;
    const low = transactions.filter(tx => tx.risk_level === 1).length;
    const safe = transactions.filter(tx => tx.risk_level === 0).length;
    const unknown = transactions.filter(tx => tx.risk_level === 5).length;
    
    riskAllSpan.textContent = total;
    riskCriticalSpan.textContent = critical;
    riskHighSpan.textContent = high;
    riskMediumSpan.textContent = medium;
    riskLowSpan.textContent = low;
    riskSafeSpan.textContent = safe;
    riskUnknownSpan.textContent = unknown;
}

// Apply filters and render
async function filterAndRenderTransactions() {

    const walletAddress = localStorage.getItem('walletAddress');

    const statusMapping = {
        'all': -1,
        'approved': 1,
        'rejected': 0
    };

    const riskMapping = {
        'all': -1,
        'safe': 0,
        'low': 1,
        'medium': 2,
        'high': 3,
        'critical': 4,
        'unknown': 5
    };

    const currentStatusFilter = statusMapping[currentStatusFilter] ?? -1;
    const currentRiskFilter = riskMapping[currentRiskFilter] ?? -1;

    if (!walletAddress) {
        console.warn("No wallet address found. Please connect wallet.");
        transactionListEl.innerHTML = '';
        noTransactionsMsg.style.display = 'block';
        return;
    }

    try {
        const params = new URLSearchParams({
            wallet_address: walletAddress,
            status_filter: currentStatusFilter,
            risk_filter: currentRiskFilter
        });
        const response = await fetch(`http://127.0.0.1:8000/transactions/filter?${params}`);
        
        if (!response.ok) {
            throw new Error("Failed to fetch transactions: ");
        }

        const data = await response.json();
        renderTransactionList(data);
        updateFilterCounts(data);

        noTransactionsMsg.style.display = data.total === 0 ? 'block' : 'none';

    } catch (error) {
        console.error('Error fetching transactions:', error);        
    }}
    // let filtered = sampleTransactions; //make function     await fetch('Enpoint')
    // // Filter by status
    // await fetch('URL/transactions/');
    // if (currentStatusFilter !== 'all') {
    //     filtered = filtered.filter(tx => tx.status === currentStatusFilter); //mga filter kahit wala na kasi pwede naifilter sa endpoint
    // } 
    
    // // Filter by risk
    // if (currentRiskFilter !== 'all') {
    //     filtered = filtered.filter(tx => tx.riskLevel === currentRiskFilter);
    // }
    
    // renderTransactionList(filtered);
    
    // //Show/hide no transactions message
    // if (filtered.length === 0) {
    //     noTransactionsMsg.style.display = 'block';
    // } else {
    //     noTransactionsMsg.style.display = 'none';
    // }
// }

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
        const shortFrom = shortenAddress(tx.wallet_address);
        const shortTo = shortenAddress(tx.address_destination);
        const riskClass = RISK_MAP[tx.risk_level];
        const statusClass = STATUS_MAP[tx.status];
        
        html += `
            <div class="transaction-item" data-tx-id="${tx.transaction_hash}">
                <div class="transaction-header">
                    <div class="transaction-title">
                        <h3>${tx.method_called}</h3>
                        <span class="risk-badge ${riskClass}">${tx.risk_level.toUpperCase()}</span>
                        <span class="status-badge ${statusClass}">${tx.status.toUpperCase()}</span>
                    </div>
                        <span class="risk-score">Risk Level: ${tx.risk_level.toUpperCase()}</span>
                    </div>
                <div class="transaction-meta">
                    <span><i class="ri-user-line"></i> From: ${shortFrom}</span>
                    <span><i class="ri-arrow-right-line"></i> To: ${shortTo}</span>
                    <span><i class="ri-time-line"></i> ${timeAgo}</span>
                    <button class="see-more-btn" data-tx-id="${tx.transaction_hash}">See More <i class="ri-arrow-right-s-line"></i></button>
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
    const transaction = sampleTransactions.find(tx => tx.transaction_hash === txId);
    if (!transaction) return;
    
    // Populate main modal - with null checks to prevent errors
    const modalTxId = document.getElementById('modalTxId');
    if (modalTxId) modalTxId.textContent = transaction.transaction_hash;
    
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

    console.log("Current status:", currentStatusFilter);
    updateFilterCounts([]);
    filterAndRenderTransactions();
    
    // Ensure modals are hidden initially
    if (mainModal) mainModal.classList.remove('active');
    if (technicalModal) technicalModal.classList.remove('active');
});
