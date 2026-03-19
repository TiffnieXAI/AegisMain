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
    }, 1200);
}

document.getElementById('simulate-btn').onclick = function() {
    // Sample transaction data (matching the standalone version)
    const sampleTransaction = {
        id: "0x7a3f8b2e9d4c5e6f7a8b9c0d1e2f3a4b5c6d7e8f",
        title: "Swap 1,500 USDC to AEG on Uniswap V3",
        contract: "0xUniswapV3Router02",
        contractShort: "0xUni...uter02",
        from: "0x1a2b3c4d5e6f7g8h9i0j",
        fromShort: "0x1a2b...9i0j",
        riskScore: 99,
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
    };

    // Format date and time
    const now = new Date();
    const formattedDate = now.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric' 
    });
    const formattedTime = now.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });

    // Determine rating and color based on risk score
    let rating, ratingColor;
    if (sampleTransaction.riskScore < 0) {
        rating = "UNKNOWN";
        ratingColor = "#8100D1";
    } else if (sampleTransaction.riskScore <= 20) {
        rating = "SAFE";
        ratingColor = "#008a3e";
    } else if (sampleTransaction.riskScore <= 40) {
        rating = "LOW";
        ratingColor = "#4da3ff";
    } else if (sampleTransaction.riskScore <= 60) {
        rating = "MEDIUM";
        ratingColor = "#ffb347";
    } else if (sampleTransaction.riskScore <= 80) {
        rating = "HIGH";
        ratingColor = "#f97316";
    } else if (sampleTransaction.riskScore <= 100) {
        rating = "CRITICAL";
        ratingColor = "#d32f2f";
    } else {
        rating = "UNKNOWN";
        ratingColor = "#8100D1";
    }

    // Get trust badge
    const getTrustBadge = (score) => {
        if (score >= 80) return { text: 'High Trust', color: '#39d98a', bg: 'rgba(57, 217, 138, 0.1)' };
        if (score >= 60) return { text: 'Medium', color: '#ffb347', bg: 'rgba(255, 179, 71, 0.1)' };
        if (score >= 40) return { text: 'Low Trust', color: '#f97316', bg: 'rgba(249, 115, 22, 0.1)' };
        return { text: 'Untrusted', color: '#d32f2f', bg: 'rgba(211, 47, 47, 0.1)' };
    };

    const getSimilarityBadge = (score) => {
        if (score <= 20) return { text: 'Low Risk', color: '#4da3ff', bg: 'rgba(77, 163, 255, 0.1)' };
        if (score <= 50) return { text: 'Medium Risk', color: '#ffb347', bg: 'rgba(255, 179, 71, 0.1)' };
        if (score <= 80) return { text: 'High Risk', color: '#f97316', bg: 'rgba(249, 115, 22, 0.1)' };
        return { text: 'Critical', color: '#d32f2f', bg: 'rgba(211, 47, 47, 0.1)' };
    };

    const trustBadge = getTrustBadge(sampleTransaction.trustScore);
    const similarityBadge = getSimilarityBadge(sampleTransaction.scamSimilarity);
    const isRiskWarningRequired = sampleTransaction.riskScore > 60;

    // Create overlay
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed; inset: 0; background: rgba(10, 15, 30, 0.7); 
        z-index: 2147483647; display: flex; align-items: center; 
        justify-content: center; backdrop-filter: blur(6px); font-family: 'Inter', sans-serif;
    `;

    overlay.innerHTML = `
        <div style="background: #1e293b; width: 480px; border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); border: 1px solid rgba(139, 92, 246, 0.3); display: flex; flex-direction: column; max-height: 85vh; animation: fadeInScale 0.3s ease-out;">
            <style>
                @keyframes fadeInScale {
                    from { opacity: 0; transform: scale(0.95); }
                    to { opacity: 1; transform: scale(1); }
                }
            </style>
            
            <!-- Header (without logo) -->
            <div style="padding: 18px 20px; display: flex; justify-content: space-between; align-items: center; background: #0f172a; border-bottom: 1px solid #334155; flex-shrink: 0;">
                <div style="font-weight: 800; color: #ffffff; font-size: 16px;">Transaction Simulation</div>
                <button class="close-dash-sim" style="background: transparent; border: none; color: #64748b; font-size: 24px; cursor: pointer; padding: 0 4px;">&times;</button>
            </div>

            <!-- Scrollable Content -->
            <div style="padding: 20px; overflow-y: auto; flex: 1;">
                <!-- Transaction Title -->
                <div style="margin-bottom: 16px;">
                    <span style="color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;">TRANSACTION</span>
                    <h3 style="margin: 4px 0 0 0; color: #ffffff; font-size: 18px; font-weight: 600; line-height: 1.4;">${sampleTransaction.title}</h3>
                </div>

                <!-- Contract Address -->
                <div style="background: #0f172a; padding: 12px 14px; border-radius: 12px; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; border: 1px solid #334155;">
                    <i class="ri-file-code-line" style="color: #8b5cf6; font-size: 16px;"></i>
                    <span style="color: #94a3b8; font-size: 12px;">Contract:</span>
                    <code style="color: #8b5cf6; font-size: 12px; font-family: monospace; background: rgba(139, 92, 246, 0.1); padding: 3px 6px; border-radius: 4px;">${sampleTransaction.contractShort}</code>
                    <button class="copy-contract-dash" style="margin-left: auto; background: transparent; border: none; color: #64748b; cursor: pointer; padding: 4px;">
                        <i class="ri-file-copy-line"></i>
                    </button>
                </div>

                <!-- From Address -->
                <div style="background: #0f172a; padding: 12px 14px; border-radius: 12px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; border: 1px solid #334155;">
                    <i class="ri-user-line" style="color: #4da3ff; font-size: 16px;"></i>
                    <span style="color: #94a3b8; font-size: 12px;">From:</span>
                    <code style="color: #4da3ff; font-size: 12px; font-family: monospace; background: rgba(77, 163, 255, 0.1); padding: 3px 6px; border-radius: 4px;">${sampleTransaction.fromShort}</code>
                    <button class="copy-from-dash" style="margin-left: auto; background: transparent; border: none; color: #64748b; cursor: pointer; padding: 4px;">
                        <i class="ri-file-copy-line"></i>
                    </button>
                </div>

                <!-- Risk Score and Level -->
                <div style="display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 14px; border-radius: 12px; margin-bottom: 16px;">
                    <div>
                        <span style="color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;">RISK LEVEL</span><br>
                        <span style="background: ${ratingColor}; color: ${rating === 'MEDIUM' ? '#1e293b' : 'white'}; padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 12px; display: inline-block; margin-top: 4px; text-transform: uppercase;">${rating}</span>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;">RISK SCORE</span><br>
                        <span style="font-size: 32px; font-weight: 800; color: ${ratingColor};">${sampleTransaction.riskScore}<span style="font-size: 12px; color: #64748b;">/100</span></span>
                    </div>
                </div>

                <!-- Date and Time -->
                <div style="display: flex; gap: 16px; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 5px;">
                        <i class="ri-calendar-line" style="color: #64748b; font-size: 14px;"></i>
                        <span style="color: #cbd5e1; font-size: 12px;">${formattedDate}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 5px;">
                        <i class="ri-time-line" style="color: #64748b; font-size: 14px;"></i>
                        <span style="color: #cbd5e1; font-size: 12px;">${formattedTime}</span>
                    </div>
                </div>

                <!-- Gas Information -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
                    <div style="background: #0f172a; padding: 10px; border-radius: 10px; border: 1px solid #334155;">
                        <span style="color: #94a3b8; font-size: 9px; text-transform: uppercase;">Gas Used</span>
                        <div style="display: flex; align-items: baseline; gap: 3px; margin-top: 4px;">
                            <span style="color: #ffffff; font-size: 16px; font-weight: 600;">${sampleTransaction.gasUsed}</span>
                            <span style="color: #64748b; font-size: 9px;">units</span>
                        </div>
                    </div>
                    <div style="background: #0f172a; padding: 10px; border-radius: 10px; border: 1px solid #334155;">
                        <span style="color: #94a3b8; font-size: 9px; text-transform: uppercase;">Gas Cost</span>
                        <div style="display: flex; align-items: baseline; gap: 3px; margin-top: 4px;">
                            <span style="color: #ffffff; font-size: 16px; font-weight: 600;">${sampleTransaction.gasCost}</span>
                            <span style="color: #64748b; font-size: 9px;">ETH</span>
                        </div>
                    </div>
                </div>

                <!-- Trust & Similarity Metrics -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
                    <!-- Trust Score -->
                    <div style="background: #0f172a; padding: 12px; border-radius: 10px; border: 1px solid #334155;">
                        <div style="display: flex; align-items: center; gap: 4px; margin-bottom: 6px;">
                            <i class="ri-shield-star-line" style="color: #8b5cf6; font-size: 12px;"></i>
                            <span style="color: #94a3b8; font-size: 9px; text-transform: uppercase;">Trust Score</span>
                        </div>
                        <div style="display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 6px;">
                            <span style="color: #ffffff; font-size: 18px; font-weight: 700;">${sampleTransaction.trustScore}%</span>
                            <span style="color: ${trustBadge.color}; background: ${trustBadge.bg}; font-size: 8px; padding: 2px 6px; border-radius: 10px;">${trustBadge.text}</span>
                        </div>
                        <div style="height: 4px; background: #1e293b; border-radius: 2px; overflow: hidden;">
                            <div style="width: ${sampleTransaction.trustScore}%; height: 100%; background: linear-gradient(90deg, #8b5cf6, #39d98a); border-radius: 2px;"></div>
                        </div>
                    </div>

                    <!-- Similarity to Scams -->
                    <div style="background: #0f172a; padding: 12px; border-radius: 10px; border: 1px solid #334155;">
                        <div style="display: flex; align-items: center; gap: 4px; margin-bottom: 6px;">
                            <i class="ri-alert-line" style="color: #f97316; font-size: 12px;"></i>
                            <span style="color: #94a3b8; font-size: 9px; text-transform: uppercase;">Scam Similarity</span>
                        </div>
                        <div style="display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 6px;">
                            <span style="color: #ffffff; font-size: 18px; font-weight: 700;">${sampleTransaction.scamSimilarity}%</span>
                            <span style="color: ${similarityBadge.color}; background: ${similarityBadge.bg}; font-size: 8px; padding: 2px 6px; border-radius: 10px;">${similarityBadge.text}</span>
                        </div>
                        <div style="height: 4px; background: #1e293b; border-radius: 2px; overflow: hidden;">
                            <div style="width: ${sampleTransaction.scamSimilarity}%; height: 100%; background: ${similarityBadge.color}; border-radius: 2px;"></div>
                        </div>
                    </div>
                </div>

                <!-- Security Analysis -->
                <div style="margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                        <i class="ri-shield-check-line" style="color: #8b5cf6; font-size: 14px;"></i>
                        <h4 style="color: #ffffff; font-size: 13px; margin: 0;">Security Analysis</h4>
                    </div>
                    <p style="color: #cbd5e1; font-size: 12px; line-height: 1.5; margin: 0; background: #0f172a; padding: 10px; border-radius: 8px;">
                        ${sampleTransaction.analysis.summary}
                    </p>
                </div>

                <!-- Warnings (Collapsible) -->
                ${sampleTransaction.warnings.length > 0 ? `
                <div style="background: rgba(249, 115, 22, 0.1); border-left: 3px solid #f97316; border-radius: 6px; margin-bottom: 16px; overflow: hidden;">
                    <div class="warnings-header-dash" style="padding: 12px; display: flex; align-items: center; gap: 6px; cursor: pointer;">
                        <i class="ri-alert-line" style="color: #f97316; font-size: 14px;"></i>
                        <h4 style="color: #f97316; font-size: 12px; margin: 0; text-transform: uppercase; letter-spacing: 0.5px; flex: 1;">Security Warnings (${sampleTransaction.warnings.length})</h4>
                        <i class="ri-arrow-down-s-line" style="color: #f97316; font-size: 14px; transition: transform 0.2s;"></i>
                    </div>
                    <div class="warnings-content-dash" style="padding: 0 12px 12px 32px;">
                        <ul style="margin: 0; padding-left: 16px; color: #ffb347; font-size: 11px; line-height: 1.6;">
                            ${sampleTransaction.warnings.map(warning => `<li style="margin-bottom: 4px;">${warning}</li>`).join('')}
                        </ul>
                    </div>
                </div>
                ` : ''}

                <!-- Risk Acknowledgment -->
                ${isRiskWarningRequired ? `
                <div style="background: #0f172a; border: 1.5px solid #f97316; padding: 12px; border-radius: 8px; margin-bottom: 16px; display: flex; gap: 10px; align-items: flex-start;">
                    <input type="checkbox" id="risk-checkbox-dash" style="width: 16px; height: 16px; cursor: pointer; margin-top: 2px; accent-color: #f97316;">
                    <label for="risk-checkbox-dash" style="font-size: 12px; color: #ffb347; line-height: 1.4; cursor: pointer;">
                        <strong style="color: #f97316; display: block; margin-bottom: 2px;">I acknowledge the risks</strong>
                        This transaction has been flagged as ${rating} risk
                    </label>
                </div>
                ` : ''}
            </div>

            <!-- Footer with Action Buttons -->
            <div style="padding: 16px 20px; display: flex; gap: 10px; background: #0f172a; border-top: 1px solid #334155; flex-shrink: 0;">
                <button id="btn-reject-dash" style="flex: 1; padding: 12px; background: #d32f2f; color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 700; font-size: 13px;">
                    Reject
                </button>
                <button id="btn-accept-dash" ${isRiskWarningRequired ? 'disabled' : ''} style="flex: 1; padding: 12px; background: ${isRiskWarningRequired ? '#334155' : '#008a3e'}; color: white; border: none; border-radius: 10px; cursor: ${isRiskWarningRequired ? 'not-allowed' : 'pointer'}; font-weight: 600; font-size: 13px;">
                    Accept
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Event Listeners
    const closeBtn = overlay.querySelector('.close-dash-sim');
    const checkbox = document.getElementById('risk-checkbox-dash');
    const acceptBtn = document.getElementById('btn-accept-dash');
    const rejectBtn = document.getElementById('btn-reject-dash');

    // Close button
    closeBtn.onclick = () => overlay.remove();

    // Copy contract address
    const copyContractBtn = overlay.querySelector('.copy-contract-dash');
    copyContractBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        navigator.clipboard.writeText(sampleTransaction.contract).then(() => {
            const originalHtml = this.innerHTML;
            this.innerHTML = '<i class="ri-check-line" style="color: #39d98a;"></i>';
            setTimeout(() => {
                this.innerHTML = originalHtml;
            }, 1500);
        });
    });

    // Copy from address
    const copyFromBtn = overlay.querySelector('.copy-from-dash');
    copyFromBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        navigator.clipboard.writeText(sampleTransaction.from).then(() => {
            const originalHtml = this.innerHTML;
            this.innerHTML = '<i class="ri-check-line" style="color: #39d98a;"></i>';
            setTimeout(() => {
                this.innerHTML = originalHtml;
            }, 1500);
        });
    });

    // Warnings collapsible
    const warningsHeader = overlay.querySelector('.warnings-header-dash');
    const warningsContent = overlay.querySelector('.warnings-content-dash');
    const collapseIcon = warningsHeader?.querySelector('i:last-child');

    if (warningsHeader && warningsContent && collapseIcon) {
        warningsHeader.addEventListener('click', () => {
            if (warningsContent.style.display === 'none') {
                warningsContent.style.display = 'block';
                collapseIcon.style.transform = 'rotate(0deg)';
            } else {
                warningsContent.style.display = 'none';
                collapseIcon.style.transform = 'rotate(-90deg)';
            }
        });
    }

    // Checkbox handler
    if (checkbox) {
        checkbox.onchange = function() {
            if (this.checked) {
                acceptBtn.disabled = false;
                acceptBtn.style.background = "#008a3e";
                acceptBtn.style.cursor = "pointer";
            } else {
                acceptBtn.disabled = true;
                acceptBtn.style.background = "#334155";
                acceptBtn.style.cursor = "not-allowed";
            }
        };
    }

    // Reject button - Modified to keep popup open until confirmed
    rejectBtn.onclick = () => {
        // Create rejection confirmation modal
        const confirmOverlay = document.createElement('div');
        confirmOverlay.style.cssText = `
            position: fixed; inset: 0; background: rgba(0,0,0,0.5); 
            z-index: 2147483647; display: flex; align-items: center; 
            justify-content: center; backdrop-filter: blur(2px);
        `;
        
        confirmOverlay.innerHTML = `
            <div style="background: #1e293b; width: 380px; padding: 24px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); border: 1px solid rgba(139, 92, 246, 0.3);">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                    <h3 style="margin: 0; font-size: 18px; color: #ffffff;">Confirm Rejection</h3>
                </div>
                <p style="color: #cbd5e1; font-size: 14px; line-height: 1.5; margin-bottom: 24px;">
                    Are you sure you want to reject this transaction? This action cannot be undone.
                </p>
                <div style="display: flex; gap: 12px;">
                    <button id="reject-cancel" style="flex: 1; padding: 12px; border: 1px solid #334155; background: transparent; border-radius: 10px; cursor: pointer; font-weight: 600; color: #ffffff;">Cancel</button>
                    <button id="reject-confirm" style="flex: 1; padding: 12px; background: #d32f2f; color: white; border: none; border-radius: 10px; font-weight: 700; cursor: pointer;">Confirm Reject</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(confirmOverlay);
        
        // Cancel button - just remove confirmation modal
        confirmOverlay.querySelector('#reject-cancel').onclick = () => confirmOverlay.remove();
        
        // Confirm button - remove both modals
        confirmOverlay.querySelector('#reject-confirm').onclick = () => {
            confirmOverlay.remove();
            overlay.remove(); // Close simulation popup only after confirmation
        };
        
        // Close on outside click
        confirmOverlay.addEventListener('click', (e) => {
            if (e.target === confirmOverlay) confirmOverlay.remove();
        });
    };

    // Accept button - Modified to keep popup open until confirmed
    acceptBtn.onclick = () => { 
        if (!acceptBtn.disabled) {
            // Create approval confirmation modal
            const confirmOverlay = document.createElement('div');
            confirmOverlay.style.cssText = `
                position: fixed; inset: 0; background: rgba(0,0,0,0.5); 
                z-index: 2147483647; display: flex; align-items: center; 
                justify-content: center; backdrop-filter: blur(2px);
            `;
            
            confirmOverlay.innerHTML = `
                <div style="background: #1e293b; width: 400px; padding: 24px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); border: 1px solid rgba(139, 92, 246, 0.3);">
                    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                        <h3 style="margin: 0; font-size: 18px; color: #ffffff;">Confirm Approval</h3>
                    </div>
                    <p style="color: #cbd5e1; font-size: 14px; margin-bottom: 16px;">You are about to approve the following transaction:</p>
                    <div style="background: #0f172a; padding: 16px; border-radius: 12px; font-size: 13px; line-height: 1.8; border: 1px solid #334155; margin-bottom: 20px;">
                        <span style="color: #64748b;">Function:</span> <strong style="color: #ffffff;">${sampleTransaction.title}</strong><br>
                        <span style="color: #64748b;">Risk Level:</span> <span style="background: ${ratingColor}; color: ${rating === 'MEDIUM' ? '#1e293b' : 'white'}; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">${rating}</span><br>
                        <span style="color: #64748b;">Contract:</span> <code style="font-size: 11px; color: #94a3b8;">${sampleTransaction.contractShort}</code>
                    </div>
                    <div style="display: flex; gap: 12px;">
                        <button id="approve-cancel" style="flex: 1; padding: 12px; border: 1px solid #334155; background: transparent; border-radius: 10px; cursor: pointer; font-weight: 600; color: #ffffff;">Cancel</button>
                        <button id="approve-confirm" style="flex: 1; padding: 12px; background: #008a3e; color: white; border: none; border-radius: 10px; font-weight: 700; cursor: pointer;">Confirm Approve</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(confirmOverlay);
            
            // Cancel button - just remove confirmation modal
            confirmOverlay.querySelector('#approve-cancel').onclick = () => confirmOverlay.remove();
            
            // Confirm button - remove both modals
            confirmOverlay.querySelector('#approve-confirm').onclick = () => {
                confirmOverlay.remove();
                overlay.remove(); // Close simulation popup only after confirmation
            };
            
            // Close on outside click
            confirmOverlay.addEventListener('click', (e) => {
                if (e.target === confirmOverlay) confirmOverlay.remove();
            });
        }
    };

    // Close on outside click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.remove();
    });
}

// Technical Analysis Modal for simulation (add this AFTER the main function)
function showTechnicalAnalysisModal(transaction, mainOverlay) {
    const modal = document.createElement('div');
    modal.style.cssText = `position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 2147483647; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px);`;

    modal.innerHTML = `
        <div style="background: #1e293b; width: 550px; max-width: 90vw; border-radius: 20px; overflow: hidden; box-shadow: 0 25px 50px rgba(0,0,0,0.5); border: 1px solid rgba(139, 92, 246, 0.3); display: flex; flex-direction: column; max-height: 80vh;">
            <div style="padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; background: #0f172a; border-bottom: 1px solid #334155; flex-shrink: 0;">
                <h3 style="color: white; margin: 0; font-size: 15px; display: flex; align-items: center; gap: 6px;">
                    <i class="ri-code-box-line" style="color: #8b5cf6;"></i>
                    Technical Analysis
                </h3>
                <button class="close-tech-modal" style="background: transparent; border: none; color: #64748b; cursor: pointer; font-size: 20px;">&times;</button>
            </div>
            <div style="padding: 20px; overflow-y: auto; flex: 1;">
                <pre style="background: #0f172a; padding: 14px; border-radius: 8px; color: #a5b4fc; font-family: monospace; font-size: 11px; line-height: 1.5; white-space: pre-wrap; word-wrap: break-word; margin: 0;">${JSON.stringify(transaction.analysis, null, 2)}</pre>
                
                <div style="margin-top: 16px; background: #0f172a; padding: 14px; border-radius: 8px;">
                    <h4 style="color: #ffffff; font-size: 12px; margin: 0 0 10px 0;">Transaction Details</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <div>
                            <span style="color: #64748b; font-size: 10px;">Transaction ID</span>
                            <p style="color: #8b5cf6; font-size: 10px; margin: 3px 0 0 0; word-break: break-all;">${transaction.id.substring(0, 20)}...</p>
                        </div>
                        <div>
                            <span style="color: #64748b; font-size: 10px;">Verification</span>
                            <p style="color: ${transaction.analysis.verification === 'Passed' ? '#39d98a' : '#f97316'}; font-size: 11px; margin: 3px 0 0 0;">${transaction.analysis.verification}</p>
                        </div>
                    </div>
                </div>
            </div>
            <div style="padding: 16px 20px; background: #0f172a; border-top: 1px solid #334155; text-align: right; flex-shrink: 0;">
                <button class="close-tech-modal" style="background: #8b5cf6; color: white; border: none; padding: 7px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 12px;">Close</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Close modal handlers
    modal.querySelectorAll('.close-tech-modal').forEach(btn => {
        btn.addEventListener('click', () => modal.remove());
    });

    // Close on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

// Technical Analysis Modal for simulation (add this AFTER the main function)
function showTechnicalAnalysisModal(transaction, mainOverlay) {
    const modal = document.createElement('div');
    modal.style.cssText = `position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 2147483647; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px);`;

    modal.innerHTML = `
        <div style="background: #1e293b; width: 600px; max-width: 90vw; border-radius: 20px; overflow: hidden; box-shadow: 0 25px 50px rgba(0,0,0,0.5); border: 1px solid rgba(139, 92, 246, 0.3);">
            <div style="padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; background: #0f172a; border-bottom: 1px solid #334155;">
                <h3 style="color: white; margin: 0; font-size: 16px; display: flex; align-items: center; gap: 8px;">
                    <i class="ri-code-box-line" style="color: #8b5cf6;"></i>
                    Technical Analysis
                </h3>
                <button class="close-tech-modal" style="background: transparent; border: none; color: #64748b; cursor: pointer; font-size: 20px;">&times;</button>
            </div>
            <div style="padding: 24px; max-height: 60vh; overflow-y: auto;">
                <pre style="background: #0f172a; padding: 16px; border-radius: 8px; color: #a5b4fc; font-family: monospace; font-size: 12px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; margin: 0;">${JSON.stringify(transaction.analysis, null, 2)}</pre>
                
                <div style="margin-top: 20px; background: #0f172a; padding: 16px; border-radius: 8px;">
                    <h4 style="color: #ffffff; font-size: 13px; margin: 0 0 12px 0;">Transaction Details</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <span style="color: #64748b; font-size: 11px;">Transaction ID</span>
                            <p style="color: #8b5cf6; font-size: 11px; margin: 4px 0 0 0; word-break: break-all;">${transaction.id}</p>
                        </div>
                        <div>
                            <span style="color: #64748b; font-size: 11px;">Contract Verification</span>
                            <p style="color: ${transaction.analysis.verification === 'Passed' ? '#39d98a' : '#f97316'}; font-size: 11px; margin: 4px 0 0 0;">${transaction.analysis.verification}</p>
                        </div>
                    </div>
                </div>
            </div>
            <div style="padding: 18px 24px; background: #0f172a; border-top: 1px solid #334155; text-align: right;">
                <button class="close-tech-modal" style="background: #8b5cf6; color: white; border: none; padding: 8px 24px; border-radius: 8px; cursor: pointer; font-weight: 600;">Close</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Close modal handlers
    modal.querySelectorAll('.close-tech-modal').forEach(btn => {
        btn.addEventListener('click', () => modal.remove());
    });

    // Close on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

// 3. Rejection Modal Logic
function showRejectionModal(mainOverlay) {
    const modal = document.createElement('div');
    modal.style.cssText = `position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 2147483647; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px);`;

    modal.innerHTML = `
        <div style="background: #1e293b; width: 400px; padding: 24px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); font-family: 'Inter', sans-serif;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                <h3 style="margin: 0; font-size: 18px; color: #e2e8f0;">Confirm Transaction Rejection</h3>
            </div>
            <p style="color: #9CA3AF; font-size: 14px; line-height: 1.5; margin-bottom: 24px;">
                Are you sure you want to reject this transaction? This action cannot be undone and the request will be cancelled.
            </p>
            <div style="display: flex; gap: 12px;">
                <button id="reject-cancel" style="flex: 1; padding: 12px; border: 1px solid #d1d5db; background: white; border-radius: 10px; cursor: pointer; font-weight: 600; color: #374151;">Cancel</button>
                <button id="reject-confirm" style="flex: 1; padding: 12px; background: #d32f2f; color: white; border: none; border-radius: 10px; font-weight: 700; cursor: pointer;">Confirm & Reject</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    document.getElementById('reject-cancel').onclick = () => modal.remove();
    document.getElementById('reject-confirm').onclick = () => {
        modal.remove();
        mainOverlay.remove();
    };
}

// 4. Approval Modal Logic (Existing)
function showApprovalModal(mainOverlay, rating, ratingColor) {
    const modal = document.createElement('div');
    modal.style.cssText = `position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 2147483647; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px);`;

    modal.innerHTML = `
        <div style="background: #1e293b; width: 400px; padding: 24px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); font-family: 'Inter', sans-serif;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                <h3 style="margin: 0; font-size: 18px; color: #e2e8f0;">Final Confirmation</h3>
            </div>
            <p style="color: #9CA3AF; font-size: 14px; margin-bottom: 16px;">You are about to approve the following transaction:</p>
            <div style="background: #0f172a; padding: 16px; border-radius: 12px; font-size: 13px; line-height: 1.8; border: 1px solid #334155;">
                <span style="color: #64748b;">Function:</span> <strong style="color: #ffffff;">transfer</strong><br>
                <span style="color: #64748b;">Risk Level:</span> <span style="background: ${ratingColor}; color: ${rating === 'MEDIUM' ? '#1e293b' : 'white'}; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">${rating}</span><br>
                <span style="color: #64748b;">Contract:</span> <code style="font-size: 11px; color: #94a3b8;">0x9876...5432</code>
            </div>
            <p style="margin-top: 20px; font-size: 14px; color: #ffffff; font-weight: 500;">Proceed with this action?</p>
            <div style="display: flex; gap: 12px; margin-top: 20px;">
                <button id="approve-cancel" style="flex: 1; padding: 12px; border: 1px solid #334155; background: transparent; border-radius: 10px; cursor: pointer; font-weight: 600; color: #ffffff;">Cancel</button>
                <button id="approve-confirm" style="flex: 1; padding: 12px; background: #008a3e; color: white; border: none; border-radius: 10px; font-weight: 700; cursor: pointer;">Confirm & Approve</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    document.getElementById('approve-cancel').onclick = () => modal.remove();
    document.getElementById('approve-confirm').onclick = () => {
        modal.remove();
        mainOverlay.remove();
    };
}