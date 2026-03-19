// Sample Transactions Array
        const sampleTransactions = [
            {
                id: "0x7a3f8b2e9d4c5e6f7a8b9c0d1e2f3a4b5c6d7e8f",
                title: "Swap 1,500 USDC to AEG on Uniswap V3",
                contract: "0xUniswapV3Router02",
                contractShort: "0xUni...uter02",
                from: "0x1a2b3c4d5e6f7g8h9i0j",
                fromShort: "0x1a2b...9i0j",
                riskScore: 78,
                riskLevel: "high",
                timestamp: new Date().toISOString(),
                gasUsed: "189,450",
                gasCost: "0.0032",
                trustScore: 82,
                scamSimilarity: 12,
                warnings: [
                    "High slippage tolerance detected (3%)",
                    "First interaction with this pool",
                    "Contract has only 2 months of activity"
                ],
                analysis: {
                    summary: "This swap involves a newly created liquidity pool with relatively low liquidity. The slippage setting is higher than recommended, which could lead to unfavorable execution."
                }
            },
            {
                id: "0x9b4c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c",
                title: "Mint 100 AEGIS Genesis NFT",
                contract: "0xAEGISGenesisNFT",
                contractShort: "0xAEG...NFT",
                from: "0x3c4d5e6f7g8h9i0j1k2l",
                fromShort: "0x3c4d...1k2l",
                riskScore: 24,
                riskLevel: "low",
                timestamp: new Date().toISOString(),
                gasUsed: "85,200",
                gasCost: "0.0015",
                trustScore: 94,
                scamSimilarity: 3,
                warnings: [],
                analysis: {
                    summary: "Legitimate NFT mint from verified contract. No suspicious patterns detected. Contract has been audited by Trail of Bits."
                }
            },
            {
                id: "0x2c5d6e7f8g9h0i1j2k3l4m5n6o7p8q9r0s1t2u3v",
                title: "Stake 500 AEG in Staking Pool",
                contract: "0xAEGISStaking",
                contractShort: "0xAEG...king",
                from: "0x5e6f7g8h9i0j1k2l3m4n",
                fromShort: "0x5e6f...3m4n",
                riskScore: 45,
                riskLevel: "medium",
                timestamp: new Date().toISOString(),
                gasUsed: "112,800",
                gasCost: "0.0021",
                trustScore: 76,
                scamSimilarity: 28,
                warnings: [
                    "First interaction with this staking contract",
                    "Lockup period: 14 days"
                ],
                analysis: {
                    summary: "Staking interaction with audited contract. Lockup period applies. No immediate red flags detected."
                }
            },
            {
                id: "0x8f7e6d5c4b3a2n1m9l8k7j6i5h4g3f2e1d0c9b8a7",
                title: "Transfer 2.5 ETH to unknown address",
                contract: "Native Transfer",
                contractShort: "Native Transfer",
                from: "0x9h8i7j6k5l4m3n2b1v0c",
                fromShort: "0x9h8i...b1v0c",
                riskScore: 92,
                riskLevel: "critical",
                timestamp: new Date().toISOString(),
                gasUsed: "21,000",
                gasCost: "0.0006",
                trustScore: 12,
                scamSimilarity: 94,
                warnings: [
                    "Recipient address associated with known phishing site",
                    "Large amount to a new address",
                    "Address has been flagged in 3 previous scams"
                ],
                analysis: {
                    summary: "HIGH RISK: Recipient address is blacklisted. This matches patterns of known phishing scams targeting large transfers."
                }
            }
        ];

        // Helper Functions
        function getRandomTransaction() {
            return sampleTransactions[Math.floor(Math.random() * sampleTransactions.length)];
        }

        function formatDateTime(timestamp) {
            const date = new Date(timestamp);
            return {
                date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
                time: date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
            };
        }

        function getRiskLevelColor(riskLevel) {
            const colors = {
                'safe': '#008a3e',
                'low': '#4da3ff',
                'medium': '#ffb347',
                'high': '#f97316',
                'critical': '#d32f2f'
            };
            return colors[riskLevel.toLowerCase()] || '#f97316';
        }

        function getTrustBadge(score) {
            if (score >= 80) return { text: 'High Trust', color: '#39d98a', bg: 'rgba(57, 217, 138, 0.1)' };
            if (score >= 60) return { text: 'Medium', color: '#ffb347', bg: 'rgba(255, 179, 71, 0.1)' };
            if (score >= 40) return { text: 'Low Trust', color: '#f97316', bg: 'rgba(249, 115, 22, 0.1)' };
            return { text: 'Untrusted', color: '#d32f2f', bg: 'rgba(211, 47, 47, 0.1)' };
        }

        function getSimilarityBadge(score) {
            if (score <= 20) return { text: 'Low Risk', color: '#4da3ff', bg: 'rgba(77, 163, 255, 0.1)' };
            if (score <= 50) return { text: 'Medium Risk', color: '#ffb347', bg: 'rgba(255, 179, 71, 0.1)' };
            if (score <= 80) return { text: 'High Risk', color: '#f97316', bg: 'rgba(249, 115, 22, 0.1)' };
            return { text: 'Critical', color: '#d32f2f', bg: 'rgba(211, 47, 47, 0.1)' };
        }

        // Confirmation Modals
        function showRejectionConfirmation(onConfirm) {
            const overlay = document.createElement('div');
            overlay.className = 'confirm-modal-overlay';
            overlay.innerHTML = `
                <div class="confirm-modal reject">
                    <div class="confirm-icon">✕</div>
                    <h3>Confirm Rejection</h3>
                    <p>Are you sure you want to reject this transaction? This action cannot be undone.</p>
                    <div class="confirm-actions">
                        <button class="confirm-cancel">Cancel</button>
                        <button class="confirm-reject">Confirm Reject</button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            overlay.querySelector('.confirm-cancel').onclick = () => overlay.remove();
            overlay.querySelector('.confirm-reject').onclick = () => {
                overlay.remove();
                onConfirm();
            };
        }

        function showApprovalConfirmation(rating, ratingColor, onConfirm) {
            const overlay = document.createElement('div');
            overlay.className = 'confirm-modal-overlay';
            overlay.innerHTML = `
                <div class="confirm-modal accept">
                    <div class="confirm-icon">✓</div>
                    <h3>Confirm Approval</h3>
                    <p>You are about to approve a <span style="color: ${ratingColor}; font-weight: bold;">${rating}</span> risk transaction. Proceed?</p>
                    <div class="confirm-actions">
                        <button class="confirm-cancel">Cancel</button>
                        <button class="confirm-accept">Confirm Approve</button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            overlay.querySelector('.confirm-cancel').onclick = () => overlay.remove();
            overlay.querySelector('.confirm-accept').onclick = () => {
                overlay.remove();
                onConfirm();
            };
        }

        // Create Popup HTML
        function createPopup(transaction) {
            const riskColor = getRiskLevelColor(transaction.riskLevel);
            const formatted = formatDateTime(transaction.timestamp);
            const trustBadge = getTrustBadge(transaction.trustScore);
            const similarityBadge = getSimilarityBadge(transaction.scamSimilarity);
            const isRiskWarningRequired = transaction.riskScore > 60;

            return `
                <div class="popup-card">
                    <!-- Header with Logo -->
                    <div class="popup-header">
                        <div class="logo-section">
                            <svg width="40" height="40" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
                                <defs><linearGradient id="g" x1="0" x2="1"><stop offset="0%" stop-color="#4f46e5"/><stop offset="100%" stop-color="#06b6d4"/></linearGradient></defs>
                                <path d="M32 4l18 6v10c0 15-11 27-18 30-7-3-18-15-18-30V10z" fill="url(#g)"/>
                                <circle cx="32" cy="26" r="6" fill="rgba(255,255,255,0.9)"/>
                            </svg>
                            <div class="logo-text">
                                <h2>A.E.G.I.S.</h2>
                                <p>Transaction Simulator</p>
                            </div>
                        </div>
                        <button class="close-btn" id="closePopupBtn">&times;</button>
                    </div>

                    <!-- Scrollable Content -->
                    <div class="popup-content">
                        <span class="tx-label">TRANSACTION</span>
                        <h3 class="tx-title">${transaction.title}</h3>

                        <!-- Contract Address -->
                        <div class="address-section">
                            <i class="ri-file-code-line contract-icon"></i>
                            <span class="address-label">Contract:</span>
                            <code class="address-value" style="color: #8b5cf6;">${transaction.contractShort}</code>
                            <button class="copy-btn" data-copy="${transaction.contract}">
                                <i class="ri-file-copy-line"></i>
                            </button>
                        </div>

                        <!-- From Address -->
                        <div class="address-section">
                            <i class="ri-user-line from-icon"></i>
                            <span class="address-label">From:</span>
                            <code class="address-value" style="color: #4da3ff;">${transaction.fromShort}</code>
                            <button class="copy-btn" data-copy="${transaction.from}">
                                <i class="ri-file-copy-line"></i>
                            </button>
                        </div>

                        <!-- Risk Section -->
                        <div class="risk-section">
                            <div>
                                <span style="color: #94a3b8; font-size: 10px; text-transform: uppercase;">RISK LEVEL</span><br>
                                <span class="risk-level-badge" style="background: ${riskColor}; color: ${transaction.riskLevel === 'medium' ? '#1e293b' : 'white'};">${transaction.riskLevel.toUpperCase()}</span>
                            </div>
                            <div style="text-align: right;">
                                <span style="color: #94a3b8; font-size: 10px; text-transform: uppercase;">RISK SCORE</span><br>
                                <span class="risk-score" style="color: ${riskColor};">${transaction.riskScore}<span class="risk-score-max">/100</span></span>
                            </div>
                        </div>

                        <!-- Date and Time -->
                        <div class="datetime-section">
                            <div class="datetime-item">
                                <i class="ri-calendar-line"></i>
                                <span>${formatted.date}</span>
                            </div>
                            <div class="datetime-item">
                                <i class="ri-time-line"></i>
                                <span>${formatted.time}</span>
                            </div>
                        </div>

                        <!-- Gas Section -->
                        <div class="gas-section">
                            <div class="gas-card">
                                <span class="gas-label">Gas Used</span>
                                <div class="gas-value">
                                    <span class="gas-number">${transaction.gasUsed}</span>
                                    <span class="gas-unit">units</span>
                                </div>
                            </div>
                            <div class="gas-card">
                                <span class="gas-label">Gas Cost</span>
                                <div class="gas-value">
                                    <span class="gas-number">${transaction.gasCost}</span>
                                    <span class="gas-unit">ETH</span>
                                </div>
                            </div>
                        </div>

                        <!-- Trust & Similarity -->
                        <div class="metrics-section">
                            <div class="metric-card">
                                <div class="metric-header">
                                    <i class="ri-shield-star-line" style="color: #8b5cf6;"></i>
                                    <span>Trust Score</span>
                                </div>
                                <div class="metric-main">
                                    <span class="metric-percentage">${transaction.trustScore}%</span>
                                    <span class="metric-badge" style="color: ${trustBadge.color}; background: ${trustBadge.bg};">${trustBadge.text}</span>
                                </div>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" style="width: ${transaction.trustScore}%; background: linear-gradient(90deg, #8b5cf6, #39d98a);"></div>
                                </div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-header">
                                    <i class="ri-alert-line" style="color: #f97316;"></i>
                                    <span>Scam Similarity</span>
                                </div>
                                <div class="metric-main">
                                    <span class="metric-percentage">${transaction.scamSimilarity}%</span>
                                    <span class="metric-badge" style="color: ${similarityBadge.color}; background: ${similarityBadge.bg};">${similarityBadge.text}</span>
                                </div>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" style="width: ${transaction.scamSimilarity}%; background: ${similarityBadge.color};"></div>
                                </div>
                            </div>
                        </div>

                        <!-- Analysis -->
                        <div class="analysis-section">
                            <div class="analysis-header">
                                <i class="ri-shield-check-line"></i>
                                <h4>Security Analysis</h4>
                            </div>
                            <p class="analysis-text">${transaction.analysis.summary}</p>
                        </div>

                        <!-- Warnings -->
                        ${transaction.warnings.length > 0 ? `
                        <div class="warnings-section">
                            <div class="warnings-header">
                                <i class="ri-alert-line"></i>
                                <h4>Security Warnings (${transaction.warnings.length})</h4>
                                <i class="ri-arrow-down-s-line collapse-icon"></i>
                            </div>
                            <div class="warnings-content">
                                <ul class="warnings-list">
                                    ${transaction.warnings.map(w => `<li>${w}</li>`).join('')}
                                </ul>
                            </div>
                        </div>
                        ` : ''}

                        <!-- Risk Acknowledgment -->
                        ${isRiskWarningRequired ? `
                        <div class="risk-acknowledgment">
                            <input type="checkbox" id="riskCheckbox">
                            <label for="riskCheckbox">
                                <strong>I acknowledge the risks</strong>
                                This transaction has been flagged as ${transaction.riskLevel.toUpperCase()} risk
                            </label>
                        </div>
                        ` : ''}

                    <!-- Footer -->
                    <div class="popup-footer">
                        <button class="reject-btn" id="rejectBtn">Reject</button>
                        <button class="accept-btn ${!isRiskWarningRequired ? 'active' : ''}" id="acceptBtn" ${isRiskWarningRequired ? 'disabled' : ''}>
                            Accept
                        </button>
                    </div>
                </div>
            `;
        }

        // Render Popup
        function renderPopup(transaction) {
            const container = document.getElementById('simulationContainer');
            container.innerHTML = createPopup(transaction);
            setupEventListeners(transaction);
        }

        // Setup Event Listeners
        function setupEventListeners(transaction) {
            const isRiskWarningRequired = transaction.riskScore > 60;

            // Close button
            document.getElementById('closePopupBtn').addEventListener('click', () => {
                window.close();
            });

            // Copy buttons
            document.querySelectorAll('.copy-btn').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const text = this.getAttribute('data-copy');
                    navigator.clipboard.writeText(text).then(() => {
                        const originalHtml = this.innerHTML;
                        this.innerHTML = '<i class="ri-check-line" style="color: #39d98a;"></i>';
                        setTimeout(() => {
                            this.innerHTML = originalHtml;
                        }, 1500);
                    });
                });
            });

            // Warnings collapsible
            const warningsHeader = document.querySelector('.warnings-header');
            const warningsContent = document.querySelector('.warnings-content');
            const collapseIcon = document.querySelector('.collapse-icon');

            if (warningsHeader && warningsContent && collapseIcon) {
                warningsHeader.addEventListener('click', () => {
                    warningsContent.classList.toggle('collapsed');
                    collapseIcon.style.transform = warningsContent.classList.contains('collapsed') ? 'rotate(-90deg)' : 'rotate(0deg)';
                });
            }

            // Checkbox handler
            const checkbox = document.getElementById('riskCheckbox');
            const acceptBtn = document.getElementById('acceptBtn');

            if (checkbox && acceptBtn) {
                checkbox.addEventListener('change', function() {
                    if (this.checked) {
                        acceptBtn.disabled = false;
                        acceptBtn.classList.add('active');
                    } else {
                        acceptBtn.disabled = true;
                        acceptBtn.classList.remove('active');
                    }
                });
            }

            // Reject button with confirmation
            document.getElementById('rejectBtn').addEventListener('click', () => {
                showRejectionConfirmation(() => {
                    window.close();
                });
            });

            // Accept button with confirmation
            if (acceptBtn) {
                acceptBtn.addEventListener('click', function() {
                    if (!this.disabled) {
                        showApprovalConfirmation(
                            transaction.riskLevel.toUpperCase(),
                            getRiskLevelColor(transaction.riskLevel),
                            () => {
                                alert('Transaction approved! (Simulation only)');
                                // Optionally close or stay
                            }
                        );
                    }
                });
            }

            // New simulation button
            document.getElementById('newSimBtn').addEventListener('click', () => {
                renderPopup(getRandomTransaction());
            });
        }

        // Initialize
        window.addEventListener('load', () => {
            renderPopup(getRandomTransaction());
        });