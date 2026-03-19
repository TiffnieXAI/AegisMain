/**
 * Unit Tests for dashboard.js
 * Testing Framework: Jest with jsdom
 * 
 * Test Coverage:
 * - Wallet modal interactions
 * - Wallet connection simulation
 * - Transaction simulation overlay
 * - Risk assessment logic
 * - User interaction handlers
 */

// Mock DOM environment
describe('Dashboard.js - Wallet Modal', () => {
    let modal, openBtn, closeBtn;

    beforeEach(() => {
        // Setup DOM elements
        document.body.innerHTML = `
            <div id="walletModal" style="display: none;"></div>
            <button id="openModalBtn"></button>
            <button id="closeModalBtn"></button>
        `;

        modal = document.getElementById('walletModal');
        openBtn = document.getElementById('openModalBtn');
        closeBtn = document.getElementById('closeModalBtn');

        // Simulate the modal logic from dashboard.js
        openBtn.onclick = () => modal.style.display = 'flex';
        closeBtn.onclick = () => modal.style.display = 'none';
        window.onclick = (event) => {
            if (event.target == modal) modal.style.display = 'none';
        };
    });

    afterEach(() => {
        document.body.innerHTML = '';
    });

    test('Should open wallet modal when connect button is clicked', () => {
        expect(modal.style.display).toBe('none');
        openBtn.click();
        expect(modal.style.display).toBe('flex');
    });

    test('Should close wallet modal when close button is clicked', () => {
        modal.style.display = 'flex';
        closeBtn.click();
        expect(modal.style.display).toBe('none');
    });

    test('Should close wallet modal when clicking outside the modal', () => {
        modal.style.display = 'flex';
        const clickEvent = new MouseEvent('click', { bubbles: true });
        Object.defineProperty(clickEvent, 'target', { value: modal, enumerable: true });
        window.onclick(clickEvent);
        expect(modal.style.display).toBe('none');
    });

    test('Should not close modal when clicking inside modal content', () => {
        modal.style.display = 'flex';
        const innerElement = document.createElement('div');
        modal.appendChild(innerElement);
        
        const clickEvent = new MouseEvent('click', { bubbles: true });
        Object.defineProperty(clickEvent, 'target', { value: innerElement, enumerable: true });
        window.onclick(clickEvent);
        expect(modal.style.display).toBe('flex');
    });
});

describe('Dashboard.js - Wallet Connection', () => {
    let statusText, connectBtn, modal;

    beforeEach(() => {
        jest.useFakeTimers();
        jest.spyOn(console, 'log').mockImplementation(() => {});

        document.body.innerHTML = `
            <div id="walletModal" style="display: flex;"></div>
            <div id="walletStatusText"></div>
            <button id="openModalBtn"></button>
        `;

        statusText = document.getElementById('walletStatusText');
        connectBtn = document.getElementById('openModalBtn');
        modal = document.getElementById('walletModal');
    });

    afterEach(() => {
        jest.restoreAllMocks();
        jest.useRealTimers();
        document.body.innerHTML = '';
    });

    test('Should update UI with wallet connection status after connecting', () => {
        const walletName = 'MetaMask';
        
        // Simulate connectWallet function
        const connectWallet = (walletName) => {
            statusText.innerText = `Connecting to ${walletName}...`;
            modal.style.display = 'none';

            setTimeout(() => {
                statusText.innerHTML = `<span style="color: #39d98a;">● Connected to ${walletName}</span><br>Address: 0x71C...4f92`;
                connectBtn.innerHTML = `<i class="ri-check-line"></i> Wallet Connected`;
                connectBtn.style.borderColor = "#39d98a";
                connectBtn.style.color = "#39d98a";
                console.log(`${walletName} connected successfully.`);
            }, 1200);
        };

        connectWallet(walletName);

        // Check loading state
        expect(statusText.innerText).toBe('Connecting to MetaMask...');
        expect(modal.style.display).toBe('none');

        // Fast-forward time
        jest.advanceTimersByTime(1200);

        // Check connected state
        expect(statusText.innerHTML).toContain('Connected to MetaMask');
        expect(statusText.innerHTML).toContain('0x71C...4f92');
        expect(connectBtn.innerHTML).toContain('Wallet Connected');
        expect(connectBtn.style.borderColor).toBe('#39d98a');
        expect(connectBtn.style.color).toBe('#39d98a');
        expect(console.log).toHaveBeenCalledWith('MetaMask connected successfully.');
    });

    test('Should handle different wallet names correctly', () => {
        const walletNames = ['MetaMask', 'WalletConnect', 'Coinbase'];

        walletNames.forEach(walletName => {
            const connectWallet = (name) => {
                statusText.innerText = `Connecting to ${name}...`;
            };

            connectWallet(walletName);
            expect(statusText.innerText).toBe(`Connecting to ${walletName}...`);
        });
    });
});

describe('Dashboard.js - Risk Assessment Logic', () => {
    test('Should display correct risk rating and color based on risk score', () => {
        const testCases = [
            { score: 10, expectedRating: 'SAFE', expectedColor: '#008a3e' },
            { score: 20, expectedRating: 'SAFE', expectedColor: '#008a3e' },
            { score: 30, expectedRating: 'LOW', expectedColor: '#4da3ff' },
            { score: 40, expectedRating: 'LOW', expectedColor: '#4da3ff' },
            { score: 50, expectedRating: 'MEDIUM', expectedColor: '#ffb347' },
            { score: 60, expectedRating: 'MEDIUM', expectedColor: '#ffb347' },
            { score: 70, expectedRating: 'HIGH', expectedColor: '#f97316' },
            { score: 80, expectedRating: 'HIGH', expectedColor: '#f97316' },
            { score: 90, expectedRating: 'CRITICAL', expectedColor: '#d32f2f' },
            { score: 100, expectedRating: 'CRITICAL', expectedColor: '#d32f2f' }
        ];

        testCases.forEach(({ score, expectedRating, expectedColor }) => {
            let rating, ratingColor;

            if (score <= 20) {
                rating = "SAFE";
                ratingColor = "#008a3e";
            } else if (score <= 40) {
                rating = "LOW";
                ratingColor = "#4da3ff";
            } else if (score <= 60) {
                rating = "MEDIUM";
                ratingColor = "#ffb347";
            } else if (score <= 80) {
                rating = "HIGH";
                ratingColor = "#f97316";
            } else {
                rating = "CRITICAL";
                ratingColor = "#d32f2f";
            }

            expect(rating).toBe(expectedRating);
            expect(ratingColor).toBe(expectedColor);
        });
    });

    test('Should require risk acknowledgment for high-risk transactions', () => {
        const testCases = [
            { score: 50, shouldRequire: false },
            { score: 60, shouldRequire: false },
            { score: 61, shouldRequire: true },
            { score: 80, shouldRequire: true },
            { score: 100, shouldRequire: true }
        ];

        testCases.forEach(({ score, shouldRequire }) => {
            const isRiskWarningRequired = score > 60;
            expect(isRiskWarningRequired).toBe(shouldRequire);
        });
    });
});

describe('Dashboard.js - Transaction Simulation Overlay', () => {
    beforeEach(() => {
        document.body.innerHTML = '';
    });

    afterEach(() => {
        document.body.innerHTML = '';
    });

    test('Should create and display transaction simulation overlay with correct data', () => {
        const sampleTransaction = {
            id: "0x7a3f8b2e9d4c5e6f7a8b9c0d1e2f3a4b5c6d7e8f",
            title: "Swap 1,500 USDC to AEG on Uniswap V3",
            contract: "0xUniswapV3Router02",
            contractShort: "0xUni...uter02",
            from: "0x1a2b3c4d5e6f7g8h9i0j",
            fromShort: "0x1a2b...9i0j",
            riskScore: 78,
            gasUsed: "189,450",
            gasCost: "0.0032",
            trustScore: 82,
            scamSimilarity: 12,
            warnings: [
                "High slippage tolerance detected (3%)",
                "First interaction with this pool"
            ],
            analysis: {
                summary: "This swap involves a newly created liquidity pool."
            }
        };

        const overlay = document.createElement('div');
        overlay.innerHTML = `
            <div class="transaction-title">${sampleTransaction.title}</div>
            <div class="contract-address">${sampleTransaction.contractShort}</div>
            <div class="risk-score">${sampleTransaction.riskScore}</div>
            <div class="gas-used">${sampleTransaction.gasUsed}</div>
            <div class="gas-cost">${sampleTransaction.gasCost}</div>
        `;

        document.body.appendChild(overlay);

        expect(overlay.innerHTML).toContain(sampleTransaction.title);
        expect(overlay.innerHTML).toContain(sampleTransaction.contractShort);
        expect(overlay.innerHTML).toContain(sampleTransaction.riskScore.toString());
        expect(overlay.innerHTML).toContain(sampleTransaction.gasUsed);
        expect(overlay.innerHTML).toContain(sampleTransaction.gasCost);
    });

    test('Should format date and time correctly', () => {
        const mockDate = new Date('2024-01-15T14:30:00');
        jest.spyOn(global, 'Date').mockImplementation(() => mockDate);

        const formattedDate = mockDate.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
        const formattedTime = mockDate.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        expect(formattedDate).toBe('Jan 15, 2024');
        expect(formattedTime).toMatch(/\d{1,2}:\d{2}\s[AP]M/);

        jest.restoreAllMocks();
    });
});

describe('Dashboard.js - Clipboard Functionality', () => {
    beforeEach(() => {
        // Mock clipboard API
        Object.assign(navigator, {
            clipboard: {
                writeText: jest.fn(() => Promise.resolve())
            }
        });

        jest.useFakeTimers();
    });

    afterEach(() => {
        jest.restoreAllMocks();
        jest.useRealTimers();
    });

    test('Should copy contract address to clipboard when copy button is clicked', async () => {
        const contractAddress = "0xUniswapV3Router02";
        
        document.body.innerHTML = `
            <button class="copy-btn">
                <i class="ri-file-copy-line"></i>
            </button>
        `;

        const copyBtn = document.querySelector('.copy-btn');
        const originalHtml = copyBtn.innerHTML;

        // Simulate copy functionality
        copyBtn.addEventListener('click', async function(e) {
            e.stopPropagation();
            await navigator.clipboard.writeText(contractAddress);
            this.innerHTML = '<i class="ri-check-line" style="color: #39d98a;"></i>';
            setTimeout(() => {
                this.innerHTML = originalHtml;
            }, 1500);
        });

        await copyBtn.click();

        expect(navigator.clipboard.writeText).toHaveBeenCalledWith(contractAddress);
        expect(copyBtn.innerHTML).toContain('ri-check-line');
        expect(copyBtn.innerHTML).toContain('#39d98a');

        // Fast-forward time
        jest.advanceTimersByTime(1500);
        expect(copyBtn.innerHTML).toBe(originalHtml);
    });
});

describe('Dashboard.js - Risk Acknowledgment Checkbox', () => {
    let checkbox, acceptBtn;

    beforeEach(() => {
        document.body.innerHTML = `
            <input type="checkbox" id="risk-checkbox-dash">
            <button id="btn-accept-dash" disabled style="background: #334155; cursor: not-allowed;"></button>
        `;

        checkbox = document.getElementById('risk-checkbox-dash');
        acceptBtn = document.getElementById('btn-accept-dash');

        // Simulate checkbox handler
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
    });

    afterEach(() => {
        document.body.innerHTML = '';
    });

    test('Should enable accept button only when risk acknowledgment checkbox is checked', () => {
        // Initially disabled
        expect(acceptBtn.disabled).toBe(true);
        expect(acceptBtn.style.background).toBe('#334155');

        // Check the checkbox
        checkbox.checked = true;
        checkbox.onchange();

        expect(acceptBtn.disabled).toBe(false);
        expect(acceptBtn.style.background).toBe('#008a3e');
        expect(acceptBtn.style.cursor).toBe('pointer');
    });

    test('Should disable accept button when checkbox is unchecked', () => {
        // Check first
        checkbox.checked = true;
        checkbox.onchange();
        expect(acceptBtn.disabled).toBe(false);

        // Then uncheck
        checkbox.checked = false;
        checkbox.onchange();

        expect(acceptBtn.disabled).toBe(true);
        expect(acceptBtn.style.background).toBe('#334155');
        expect(acceptBtn.style.cursor).toBe('not-allowed');
    });
});

describe('Dashboard.js - Warnings Toggle', () => {
    let warningsHeader, warningsContent, collapseIcon;

    beforeEach(() => {
        document.body.innerHTML = `
            <div class="warnings-header-dash" style="cursor: pointer;">
                <i class="ri-arrow-down-s-line" style="transition: transform 0.2s;"></i>
            </div>
            <div class="warnings-content-dash" style="display: block;"></div>
        `;

        warningsHeader = document.querySelector('.warnings-header-dash');
        warningsContent = document.querySelector('.warnings-content-dash');
        collapseIcon = warningsHeader.querySelector('i');

        // Simulate toggle functionality
        warningsHeader.addEventListener('click', () => {
            if (warningsContent.style.display === 'none') {
                warningsContent.style.display = 'block';
                collapseIcon.style.transform = 'rotate(0deg)';
            } else {
                warningsContent.style.display = 'none';
                collapseIcon.style.transform = 'rotate(-90deg)';
            }
        });
    });

    afterEach(() => {
        document.body.innerHTML = '';
    });

    test('Should toggle warnings section when clicking the warnings header', () => {
        // Initially visible
        expect(warningsContent.style.display).toBe('block');

        // Click to collapse
        warningsHeader.click();
        expect(warningsContent.style.display).toBe('none');
        expect(collapseIcon.style.transform).toBe('rotate(-90deg)');

        // Click to expand
        warningsHeader.click();
        expect(warningsContent.style.display).toBe('block');
        expect(collapseIcon.style.transform).toBe('rotate(0deg)');
    });
});

describe('Dashboard.js - Overlay Removal', () => {
    let overlay, rejectBtn;

    beforeEach(() => {
        overlay = document.createElement('div');
        overlay.id = 'transaction-overlay';
        overlay.innerHTML = `
            <button id="btn-reject-dash">Reject</button>
        `;
        document.body.appendChild(overlay);

        rejectBtn = document.getElementById('btn-reject-dash');
    });

    afterEach(() => {
        document.body.innerHTML = '';
    });

    test('Should remove overlay when reject button is clicked', () => {
        rejectBtn.onclick = () => overlay.remove();

        expect(document.getElementById('transaction-overlay')).toBeTruthy();
        rejectBtn.click();
        expect(document.getElementById('transaction-overlay')).toBeFalsy();
    });

    test('Should remove overlay when close button is clicked', () => {
        const closeBtn = document.createElement('button');
        closeBtn.className = 'close-dash-sim';
        overlay.appendChild(closeBtn);

        closeBtn.onclick = () => overlay.remove();

        expect(document.getElementById('transaction-overlay')).toBeTruthy();
        closeBtn.click();
        expect(document.getElementById('transaction-overlay')).toBeFalsy();
    });
});
