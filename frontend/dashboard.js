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
    const riskScore = 78; // Example score trigger for HIGH risk
    const isHighRisk = riskScore >= 75;

    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed; inset: 0; background: rgba(10, 15, 30, 0.7); 
        z-index: 2147483647; display: flex; align-items: center; 
        justify-content: center; backdrop-filter: blur(6px); font-family: 'Inter', sans-serif;
    `;

    overlay.innerHTML = `
        <div style="background: #1e293b; width: 440px; border-radius: 20px; overflow: hidden; box-shadow: 0 25px 50px rgba(0,0,0,0.5);">
            <div style="padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; background: #1e293b; border-bottom: 1px solid #fee2e2;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="background: #6200ea; color: white; padding: 8px; border-radius: 10px;">🛡️</div>
                    <div>
                        <div style="font-weight: 800; color: #6200ea; font-size: 15px;">A.E.G.I.S. Security</div>
                        <div style="font-size: 11px; color: #697386;">Transaction Approval</div>
                    </div>
                </div>
                <div style="background: #1e293b; color: #f57c00; font-size: 11px; padding: 4px 12px; border-radius: 20px; border: 1px solid #ffe0b2; font-weight: 600;">🕒 Pending</div>
            </div>

            <div style="padding: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                    <div>
                        <small style="color: #697386; font-size: 11px; font-weight: 600;">Danger Rating</small><br>
                        <span style="background: #f97316; color: white; padding: 5px 12px; border-radius: 6px; font-weight: 700; font-size: 12px; display: inline-block; margin-top: 4px;">HIGH</span>
                    </div>
                    <div style="text-align: right;">
                        <small style="color: #697386; font-size: 11px; font-weight: 600;">Risk Score</small><br>
                        <span style="font-size: 32px; font-weight: 800; color: #f97316;">${riskScore}<small style="font-size: 14px; color: #a3acb9;">/100</small></span>
                    </div>
                </div>

                <div id="risk-acknowledgment" style="background: #fff7ed; border: 1.5px solid #f97316; padding: 16px; border-radius: 12px; margin-bottom: 20px; display: flex; gap: 12px; align-items: flex-start;">
                    <input type="checkbox" id="risk-checkbox" style="width: 18px; height: 18px; cursor: pointer; margin-top: 3px;">
                    <label for="risk-checkbox" style="font-size: 13px; color: #9a3412; line-height: 1.5; cursor: pointer;">
                        <strong>I understand the risks</strong><br>
                        I acknowledge that this transaction has been flagged as HIGH risk and understand I could lose all my funds. I accept full responsibility for proceeding.
                    </label>
                </div>
            </div>

            <div style="padding: 20px 24px; display: flex; gap: 12px; background: #1e293b; border-top: 1px solid #f0f2f5;">
                <button id="btn-reject" style="flex: 1; padding: 14px; background: #d32f2f; color: #1e293b; border: none; border-radius: 12px; cursor: pointer; font-weight: 700;">
                    Reject
                </button>
                <button id="btn-accept" disabled style="flex: 1; padding: 14px; background: #a7f3d0; color: #1e293b; border: none; border-radius: 12px; cursor: not-allowed; font-weight: 600; transition: all 0.2s;">
                    Accept
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    const checkbox = document.getElementById('risk-checkbox');
    const acceptBtn = document.getElementById('btn-accept');
    const rejectBtn = document.getElementById('btn-reject');

    // Checkbox handles the 'Accept' button state
    checkbox.onchange = function() {
        if (this.checked) {
            acceptBtn.disabled = false;
            acceptBtn.style.background = "#008a3e";
            acceptBtn.style.cursor = "pointer";
            acceptBtn.style.fontWeight = "700";
        } else {
            acceptBtn.disabled = true;
            acceptBtn.style.background = "#a7f3d0";
            acceptBtn.style.cursor = "not-allowed";
            acceptBtn.style.fontWeight = "600";
        }
    };

    rejectBtn.onclick = () => {
        showRejectionModal(overlay);
    };

    acceptBtn.onclick = () => {
        if (!acceptBtn.disabled) {
            showApprovalModal(overlay);
        }
    };
};

// 3. Rejection Modal Logic
function showRejectionModal(mainOverlay) {
    const modal = document.createElement('div');
    modal.style.cssText = `position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 2147483647; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px);`;

    modal.innerHTML = `
        <div style="background: #1e293b; width: 400px; padding: 24px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); font-family: 'Inter', sans-serif;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                <div style="color: #d32f2f; font-size: 24px; background: #fee2e2; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">✕</div>
                <h3 style="margin: 0; font-size: 18px; color: #111827;">Confirm Transaction Rejection</h3>
            </div>
            <p style="color: #4b5563; font-size: 14px; line-height: 1.5; margin-bottom: 24px;">
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
function showApprovalModal(mainOverlay) {
    const modal = document.createElement('div');
    modal.style.cssText = `position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 2147483647; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px);`;

    modal.innerHTML = `
        <div style="background: #1e293b; width: 400px; padding: 24px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); font-family: 'Inter', sans-serif;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                <div style="color: #008a3e; font-size: 24px; background: #f0fdf4; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">✔</div>
                <h3 style="margin: 0; font-size: 18px; color: #111827;">Confirm Transaction Approval</h3>
            </div>
            <p style="color: #4b5563; font-size: 14px; margin-bottom: 16px;">You are about to approve the following transaction:</p>
            <div style="background: #1e293b; padding: 16px; border-radius: 12px; font-size: 13px; line-height: 1.8; border: 1px solid #eef1f5;">
                <span style="color: #6b7280;">Function:</span> <strong style="color: #111827;">transfer</strong><br>
                <span style="color: #6b7280;">Risk Level:</span> <span style="background: #008a3e; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">SAFE</span><br>
                <span style="color: #6b7280;">Contract:</span> <code style="font-size: 11px; color: #374151;">0x9876...5432</code>
            </div>
            <p style="margin-top: 20px; font-size: 14px; color: #374151; font-weight: 500;">Are you sure you want to proceed?</p>
            <div style="display: flex; gap: 12px; margin-top: 20px;">
                <button id="approve-cancel" style="flex: 1; padding: 12px; border: 1px solid #d1d5db; background: white; border-radius: 10px; cursor: pointer; font-weight: 600; color: #374151;">Cancel</button>
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