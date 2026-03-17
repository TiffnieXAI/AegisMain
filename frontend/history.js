document.getElementById("btn_go_to_dashboard").addEventListener("click", function() {
    window.location.href = "dashboard.html";
});


// script.js — Dynamic A.E.G.I.S. functionality with database integration

(function() {
    "use strict";

    // API Configuration
    const API_BASE_URL = 'https://your-api-endpoint.com/api'; // Replace with your actual API
    const WS_URL = 'wss://your-websocket-endpoint.com'; // For real-time updates

    // State management
    let transactions = [];
    let currentTransaction = null;
    let filters = {
        status: 'all',
        risk: 'all'
    };
    let webSocket = null;

    // DOM Elements
    const transactionList = document.getElementById('transactionList');
    const modal = document.getElementById('transactionModal');
    const technicalModal = document.getElementById('technicalModal');
    const noTransactionsMsg = document.getElementById('noTransactionsMsg');
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');

    // Initialize
    async function initialize() {
        await fetchTransactions();
        setupEventListeners();
        setupWebSocket();
        setupRealTimeUpdates();
    }

    // Fetch transactions from database
    async function fetchTransactions() {
        try {
            showLoading();
            
            const queryParams = new URLSearchParams({
                status: filters.status,
                risk: filters.risk,
                limit: 100,
                sort: '-date'
            });

            const response = await fetch(`${API_BASE_URL}/transactions?${queryParams}`, {
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Failed to fetch transactions');

            const data = await response.json();
            transactions = data.transactions;
            
            renderTransactions(transactions);
            updateFilterCounts();
            hideLoading();
        } catch (error) {
            console.error('Error fetching transactions:', error);
            showError('Failed to load transactions');
        }
    }

    // Setup WebSocket for real-time updates
    function setupWebSocket() {
        webSocket = new WebSocket(WS_URL);
        
        webSocket.onmessage = (event) => {
            const update = JSON.parse(event.data);
            handleRealTimeUpdate(update);
        };

        webSocket.onclose = () => {
            // Attempt to reconnect after 5 seconds
            setTimeout(setupWebSocket, 5000);
        };
    }

    // Handle real-time updates
    function handleRealTimeUpdate(update) {
        switch(update.type) {
            case 'NEW_TRANSACTION':
                transactions.unshift(update.data);
                if (shouldShowTransaction(update.data)) {
                    renderTransactions(transactions);
                }
                updateFilterCounts();
                showNotification('New transaction detected', 'info');
                break;
                
            case 'TRANSACTION_UPDATED':
                const index = transactions.findIndex(t => t.id === update.data.id);
                if (index !== -1) {
                    transactions[index] = update.data;
                    if (shouldShowTransaction(update.data)) {
                        renderTransactions(transactions);
                    }
                }
                break;
                
            case 'RISK_SCORE_UPDATE':
                updateRiskScore(update.data.transactionId, update.data.newScore);
                break;
        }
    }

    // Render transactions dynamically
    function renderTransactions(transactionsToRender) {
        if (!transactionList) return;

        transactionList.innerHTML = '';
        
        if (transactionsToRender.length === 0) {
            noTransactionsMsg.style.display = 'block';
            transactionList.style.display = 'none';
        } else {
            noTransactionsMsg.style.display = 'none';
            transactionList.style.display = 'block';
            
            transactionsToRender.forEach(tx => {
                const txElement = createTransactionElement(tx);
                transactionList.appendChild(txElement);
            });
        }
    }

    // Create transaction element with dynamic data
    function createTransactionElement(tx) {
        const div = document.createElement('div');
        div.className = 'transaction-item';
        div.setAttribute('data-transaction-id', tx.id);
        div.setAttribute('data-risk', tx.risk);
        div.setAttribute('data-status', tx.status);
        
        div.innerHTML = `
            <div class="transaction-header">
                <div class="transaction-title">
                    <h3>${escapeHtml(tx.type)}</h3>
                    <span class="risk-badge ${tx.risk}">${tx.risk}</span>
                    <span class="status-badge ${tx.status}">${tx.status}</span>
                </div>
                <span class="risk-score">Risk Score: ${tx.riskScore}</span>
            </div>
            <p class="transaction-description">${escapeHtml(truncateText(tx.description, 100))}</p>
            <div class="transaction-meta">
                <span>${formatDate(tx.date)}</span>
                <span class="tx-address">${formatAddress(tx.address)}</span>
                <button class="see-more-btn" onclick="window.openTransactionModal('${tx.id}')">See More →</button>
            </div>
        `;

        return div;
    }

    // Open transaction modal with dynamic data
    window.openTransactionModal = async function(transactionId) {
        try {
            showLoading();
            
            const response = await fetch(`${API_BASE_URL}/transactions/${transactionId}`, {
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Failed to fetch transaction details');

            const tx = await response.json();
            currentTransaction = tx;
            
            populateModalWithData(tx);
            
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
            
            hideLoading();
        } catch (error) {
            console.error('Error fetching transaction details:', error);
            showError('Failed to load transaction details');
        }
    };

    // Populate modal with dynamic data
    function populateModalWithData(tx) {
        // Basic info
        document.getElementById('modalTransactionTitle').textContent = tx.type;
        document.getElementById('modalTxId').textContent = tx.id;
        document.getElementById('modalDate').textContent = formatDate(tx.date, 'full');
        document.getElementById('modalRiskScore').textContent = tx.riskScore;
        
        // Severity badge
        const severityEl = document.getElementById('modalSeverity');
        severityEl.textContent = tx.risk;
        severityEl.className = `severity-badge ${tx.risk}`;
        
        // Status badge
        const statusEl = document.getElementById('modalStatus');
        statusEl.textContent = tx.status;
        statusEl.className = `status-badge ${tx.status}`;
        
        // Contract address
        document.getElementById('modalContractAddress').textContent = tx.address;
        
        // Description
        document.getElementById('modalDescription').textContent = tx.description;
        
        // Warnings
        const warningsList = document.getElementById('modalWarnings');
        warningsList.innerHTML = '';
        if (tx.warnings && tx.warnings.length > 0) {
            tx.warnings.forEach(warning => {
                const li = document.createElement('li');
                li.textContent = warning;
                warningsList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.textContent = 'No warnings detected';
            li.style.color = '#39d98a';
            warningsList.appendChild(li);
        }

        // Recommendations
        const recommendationsList = document.getElementById('modalRecommendations');
        recommendationsList.innerHTML = '';
        if (tx.recommendations && tx.recommendations.length > 0) {
            tx.recommendations.forEach(rec => {
                const li = document.createElement('li');
                li.textContent = rec;
                recommendationsList.appendChild(li);
            });
        }

        // Metrics
        document.getElementById('modalTrustScore').textContent = tx.trustScore || 'N/A';
        document.getElementById('modalGasEstimate').textContent = tx.gasEstimate || 'N/A';
        document.getElementById('modalGasCost').textContent = tx.gasCost ? `(${tx.gasCost})` : '';
        document.getElementById('modalSimilarContracts').textContent = tx.similarContracts?.toLocaleString() || '0';
        document.getElementById('modalConfidence').textContent = tx.confidence ? tx.confidence + '%' : 'N/A';
        
        // Vulnerabilities
        const vulnElement = document.getElementById('modalVulnerabilities');
        if (tx.vulnerabilityPatterns) {
            vulnElement.textContent = tx.vulnerabilityPatterns;
            vulnElement.style.color = tx.risk === 'safe' || tx.risk === 'low' ? '#39d98a' : '#ffb347';
        } else {
            vulnElement.textContent = 'No known vulnerabilities';
            vulnElement.style.color = '#39d98a';
        }

        // Store transaction ID for technical analysis
        localStorage.setItem('currentTransactionId', tx.id);
    }

    // Open technical modal with real-time analysis
    window.openTechnicalModal = async function() {
        if (!currentTransaction) return;
        
        try {
            showLoading();
            
            // Fetch detailed technical analysis
            const response = await fetch(`${API_BASE_URL}/transactions/${currentTransaction.id}/analysis`, {
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Failed to fetch technical analysis');

            const analysis = await response.json();
            populateTechnicalModal(analysis);
            
            technicalModal.classList.add('active');
            hideLoading();
        } catch (error) {
            console.error('Error fetching technical analysis:', error);
            showError('Failed to load technical analysis');
        }
    };

    // Populate technical modal with dynamic analysis
    function populateTechnicalModal(analysis) {
        // RAG Analysis
        const ragEl = document.getElementById('ragAnalysis');
        if (ragEl) {
            ragEl.innerHTML = `
                <div style="margin-bottom: 0.5rem;"><strong>Contract:</strong> ${escapeHtml(analysis.contract?.name || 'Unknown')}</div>
                <div><strong>Status:</strong> ${analysis.contract?.verified ? '✅ Whitelisted' : '⚠️ Unverified'}</div>
                <div><strong>Risk Level:</strong> <span style="color: ${getRiskColor(analysis.risk)}">${analysis.risk || 'Unknown'}</span></div>
                <div style="margin-top: 0.5rem; font-size: 0.8rem; color: #94a3b8;">
                    ${analysis.contract?.verificationDetails || 'No verification details available'}
                </div>
            `;
        }
        
        // Action Listener
        const actionEl = document.getElementById('actionListener');
        if (actionEl) {
            const functions = analysis.monitoredFunctions || [];
            const funcList = functions.map(f => f.name).join(', ') || 'No functions monitored';
            
            actionEl.innerHTML = `
                <div><strong>Monitored Functions:</strong></div>
                <div style="margin-top: 0.3rem; color: #8b5cf6;">${escapeHtml(funcList)}</div>
                <div style="margin-top: 0.5rem; font-size: 0.8rem;">
                    <span style="color: ${analysis.monitoringActive ? '#39d98a' : '#ff4c4c'};">● ${analysis.monitoringActive ? 'Active' : 'Inactive'}</span>
                    Real-time execution monitoring
                </div>
            `;
        }
        
        // Trust Registry
        const trustStatus = document.getElementById('trustRegistryStatus');
        const trustBadge = document.getElementById('trustRegistryBadge');
        if (trustStatus && trustBadge) {
            const isSafe = analysis.trustScore > 70;
            trustStatus.textContent = isSafe ? 'SAFE' : 'CAUTION';
            trustStatus.style.color = isSafe ? '#39d98a' : '#ffb347';
            
            trustBadge.textContent = analysis.contract?.verified ? 'Verified' : 'Unverified';
            trustBadge.style.background = analysis.contract?.verified ? 
                'rgba(57, 217, 138, 0.15)' : 'rgba(255, 179, 71, 0.15)';
            trustBadge.style.color = analysis.contract?.verified ? '#39d98a' : '#ffb347';
        }
        
        // Function Signature
        const funcSig = document.getElementById('functionSignature');
        if (funcSig) {
            funcSig.innerHTML = `
                <div><strong>${escapeHtml(analysis.function?.name || 'Unknown')}</strong> 
                <span style="color: #64748b;">${analysis.function?.signature || ''}</span></div>
                <div style="margin-top: 0.3rem; font-size: 0.8rem; color: #94a3b8;">
                    ${analysis.function?.analysis || 'No analysis available'}
                </div>
            `;
        }
        
        // Simulation Result
        const simResult = document.getElementById('simulationResult');
        if (simResult) {
            simResult.innerHTML = `
                <div style="margin-bottom: 0.5rem;">
                    <span style="color: ${analysis.simulation?.success ? '#39d98a' : '#ff4c4c'};">${analysis.simulation?.success ? '✓' : '⚠'} Simulation ${analysis.simulation?.success ? 'Successful' : 'Failed'}</span>
                    <span style="color: #94a3b8; margin-left: 1rem;">Gas used: ${analysis.simulation?.gasUsed?.toLocaleString() || 'N/A'}</span>
                </div>
                <div style="color: #cbd5e1; line-height: 1.6;">
                    ${analysis.simulation?.description || 'No simulation data available'}
                </div>
            `;
        }
        
        // State Changes
        const stateList = document.getElementById('stateChanges');
        if (stateList && analysis.stateChanges) {
            stateList.innerHTML = '';
            
            analysis.stateChanges.forEach(change => {
                const li = document.createElement('li');
                li.style.cssText = 'color: #cbd5e1; padding: 0.5rem 0; border-bottom: 1px solid rgba(139, 92, 246, 0.1);';
                
                if (change.type === 'out') {
                    li.innerHTML = `<span style="color: #ff4c4c;">-${escapeHtml(change.amount)}</span> <span style="color: #94a3b8;">${escapeHtml(change.description)}</span>`;
                } else if (change.type === 'in') {
                    li.innerHTML = `<span style="color: #39d98a;">+${escapeHtml(change.amount)}</span> <span style="color: #94a3b8;">${escapeHtml(change.description)}</span>`;
                } else {
                    li.innerHTML = `<span style="color: #8b5cf6;">${escapeHtml(change.amount)}</span> <span style="color: #94a3b8;">${escapeHtml(change.description)}</span>`;
                }
                
                stateList.appendChild(li);
            });
        }
        
        // Raw Call Data
        const rawData = document.getElementById('rawCallData');
        if (rawData && analysis.rawData) {
            const functionSelector = analysis.rawData.substring(0, 10);
            
            rawData.innerHTML = `
                <div style="margin-bottom: 0.5rem;">
                    <span style="color: #8b5cf6;">Function Selector:</span> ${functionSelector}
                </div>
                <div style="font-size: 0.7rem; word-break: break-all; color: #a5b4fc;">
                    ${analysis.rawData}
                </div>
            `;
        }
        
        // Community Reports
        const communityReports = document.getElementById('communityReports');
        const lastAudit = document.getElementById('lastAudit');
        const communityMsg = document.getElementById('communityMessage');
        
        if (communityReports) {
            communityReports.textContent = analysis.communityReports || '0';
            communityReports.style.color = analysis.communityReports > 0 ? '#ffb347' : '#39d98a';
        }
        
        if (lastAudit) {
            lastAudit.textContent = analysis.lastAudit || 'Never';
        }
        
        if (communityMsg) {
            if (analysis.contract?.verified && analysis.trustScore > 70) {
                communityMsg.innerHTML = `
                    <i class="ri-checkbox-circle-line" style="color: #39d98a;"></i>
                    This contract has been verified and whitelisted by the community
                `;
            } else if (!analysis.contract?.verified) {
                communityMsg.innerHTML = `
                    <i class="ri-error-warning-line" style="color: #ffb347;"></i>
                    This contract is not verified - exercise extreme caution
                `;
            } else {
                communityMsg.innerHTML = `
                    <i class="ri-alert-line" style="color: #ffb347;"></i>
                    This transaction has mixed risk factors - review carefully
                `;
            }
        }
    }

    // Update filter counts from database
    async function updateFilterCounts() {
        try {
            const response = await fetch(`${API_BASE_URL}/transactions/counts`, {
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Failed to fetch counts');

            const counts = await response.json();

            document.getElementById('statusAll').textContent = counts.total || 0;
            document.getElementById('statusApproved').textContent = counts.approved || 0;
            document.getElementById('statusRejected').textContent = counts.rejected || 0;
            document.getElementById('riskAll').textContent = counts.total || 0;
            document.getElementById('riskCritical').textContent = counts.critical || 0;
            document.getElementById('riskHigh').textContent = counts.high || 0;
            document.getElementById('riskMedium').textContent = counts.medium || 0;
            document.getElementById('riskLow').textContent = counts.low || 0;
            document.getElementById('riskSafe').textContent = counts.safe || 0;
        } catch (error) {
            console.error('Error updating filter counts:', error);
        }
    }

    // Filter transactions with database query
    async function filterTransactions() {
        const activeStatus = document.querySelector('[data-status].active');
        const activeRisk = document.querySelector('[data-risk].active');
        
        filters.status = activeStatus ? activeStatus.dataset.status : 'all';
        filters.risk = activeRisk ? activeRisk.dataset.risk : 'all';
        
        await fetchTransactions();
    }

    // Clear filters and reset view
    async function clearFilters() {
        document.querySelectorAll('[data-status]').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll('[data-risk]').forEach(btn => {
            btn.classList.remove('active');
        });
        
        document.querySelector('[data-status="all"]').classList.add('active');
        document.querySelector('[data-risk="all"]').classList.add('active');
        
        filters.status = 'all';
        filters.risk = 'all';
        
        await fetchTransactions();
    }

    // Setup real-time updates polling (fallback for WebSocket)
    function setupRealTimeUpdates() {
        setInterval(async () => {
            if (!webSocket || webSocket.readyState !== WebSocket.OPEN) {
                await checkForUpdates();
            }
        }, 30000); // Check every 30 seconds
    }

    // Check for updates via REST API
    async function checkForUpdates() {
        try {
            const lastUpdate = localStorage.getItem('lastUpdateTimestamp');
            const response = await fetch(`${API_BASE_URL}/transactions/updates?since=${lastUpdate || 0}`, {
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Failed to check updates');

            const updates = await response.json();
            
            if (updates.length > 0) {
                await fetchTransactions(); // Refresh the list
                localStorage.setItem('lastUpdateTimestamp', Date.now());
            }
        } catch (error) {
            console.error('Error checking for updates:', error);
        }
    }

    // Helper Functions
    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function truncateText(text, length) {
        if (!text) return '';
        return text.length > length ? text.substring(0, length) + '...' : text;
    }

    function formatAddress(address) {
        if (!address) return '';
        return address.substring(0, 10) + '...' + address.substring(address.length - 8);
    }

    function formatDate(date, format = 'short') {
        if (!date) return '';
        const d = new Date(date);
        if (format === 'short') {
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        } else {
            return d.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }

    function getRiskColor(risk) {
        const colors = {
            'critical': '#ff4c4c',
            'high': '#ffb347',
            'medium': '#ffd966',
            'low': '#4da3ff',
            'safe': '#39d98a'
        };
        return colors[risk] || '#94a3b8';
    }

    function getAuthToken() {
        return localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
    }

    function showLoading() {
        // Implement loading indicator
        const loader = document.createElement('div');
        loader.className = 'loading-spinner';
        loader.id = 'global-loader';
        if (!document.getElementById('global-loader')) {
            document.body.appendChild(loader);
        }
    }

    function hideLoading() {
        const loader = document.getElementById('global-loader');
        if (loader) loader.remove();
    }

    function showError(message) {
        // Implement error notification
        console.error(message);
        // You could add a toast notification here
    }

    function showNotification(message, type) {
        // Implement notification system
        console.log(`[${type}] ${message}`);
    }

    function shouldShowTransaction(transaction) {
        const statusMatch = filters.status === 'all' || transaction.status === filters.status;
        const riskMatch = filters.risk === 'all' || transaction.risk === filters.risk;
        return statusMatch && riskMatch;
    }

    function updateRiskScore(transactionId, newScore) {
        const transaction = transactions.find(t => t.id === transactionId);
        if (transaction) {
            transaction.riskScore = newScore;
            if (shouldShowTransaction(transaction)) {
                renderTransactions(transactions);
            }
        }
    }

    // Setup event listeners
    function setupEventListeners() {
        // Close modal buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', closeModals);
        });

        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModals();
        });

        technicalModal.addEventListener('click', (e) => {
            if (e.target === technicalModal) closeModals();
        });

        // View technical analysis
        const viewTechnicalBtn = document.getElementById('viewTechnicalBtn');
        if (viewTechnicalBtn) {
            viewTechnicalBtn.addEventListener('click', () => window.openTechnicalModal());
        }

        // Close technical modal
        const closeTechnicalBtn = document.querySelector('.btn-close-technical');
        if (closeTechnicalBtn) {
            closeTechnicalBtn.addEventListener('click', closeModals);
        }

        const technicalCloseBtn = document.querySelector('.technical-close');
        if (technicalCloseBtn) {
            technicalCloseBtn.addEventListener('click', closeModals);
        }

        // Approve button
        const approveBtn = document.getElementById('approveBtn');
        if (approveBtn) {
            approveBtn.addEventListener('click', async () => {
                if (currentTransaction) {
                    await updateTransactionStatus(currentTransaction.id, 'approved');
                }
                closeModals();
            });
        }

        // Copy address function
        window.copyToClipboard = async (text) => {
            try {
                await navigator.clipboard.writeText(text);
                showNotification('Address copied to clipboard!', 'success');
            } catch (err) {
                console.error('Failed to copy:', err);
            }
        };

        // Status filter buttons
        document.querySelectorAll('[data-status]').forEach(btn => {
            btn.addEventListener('click', async () => {
                document.querySelectorAll('[data-status]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                await filterTransactions();
            });
        });

        // Risk filter buttons
        document.querySelectorAll('[data-risk]').forEach(btn => {
            btn.addEventListener('click', async () => {
                document.querySelectorAll('[data-risk]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                await filterTransactions();
            });
        });

        // Clear filters button
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', clearFilters);
        }

        // Keyboard escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeModals();
            }
        });
    }

    // Update transaction status
    async function updateTransactionStatus(transactionId, status) {
        try {
            const response = await fetch(`${API_BASE_URL}/transactions/${transactionId}/status`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status })
            });

            if (!response.ok) throw new Error('Failed to update status');

            showNotification('Transaction status updated', 'success');
            await fetchTransactions(); // Refresh the list
        } catch (error) {
            console.error('Error updating status:', error);
            showError('Failed to update transaction status');
        }
    }

    // Close all modals
    function closeModals() {
        modal.classList.remove('active');
        technicalModal.classList.remove('active');
        document.body.style.overflow = '';
        currentTransaction = null;
    }

    // Initialize the application
    initialize();
})();