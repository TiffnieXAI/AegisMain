# 🛡️ AEGIS

### Autonomous Evaluation & Guardian Intelligence System

> ⚠️ Stop signing blind transactions.
> AEGIS protects Web3 users *before* assets are lost.

🚀 AI-Powered Security Layer for Web3
🔐 Built with Blockchain + AI + Simulation

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Solidity](https://img.shields.io/badge/Solidity-smartcontracts-black)
![Status](https://img.shields.io/badge/Status-Hackathon-green)

---

## 🎥 Demo

👉 Watch the demo here:
https://your-demo-link-here

<!-- Optional: Add GIF preview -->

![Demo](./assets/demo.gif)

---

## ⚡ Why AEGIS?

### 🚨 The Problem

Web3 is **dangerous for non-technical users**.

* Users sign transactions they don’t understand
* Smart contract data appears as unreadable hex
* One mistake = **permanent loss of funds**
* Attackers bypass blocklists using fresh malicious contracts

👉 Result: Web3 remains unsafe and inaccessible for mass adoption

---

### 💡 The Solution

AEGIS acts as a **real-time AI guardian** between users and the blockchain.

* 🧠 Translates complex transactions into human-readable intent
* 🔍 Simulates outcomes before execution
* ⚠️ Warns users of hidden risks
* 🔗 Verifies trust using on-chain data

> 💬 *Think: “Google Translate + Antivirus for Web3 transactions”*

---

## 🖥️ Interface Overview

### 🔍 Transaction Analysis

![Analysis](./assets/analysis.png)

### ⚠️ Risk Warning

![Warning](./assets/warning.png)

### 📊 Dashboard

![Dashboard](./assets/dashboard.png)

> Designed to simplify complex blockchain interactions into clear insights

---

## 🧩 Features

### 🛡️ Live Interception

* Pre-execution transaction simulation (Hardhat sandbox)
* Human-readable intent extraction
* Real-time risk warnings

---

### 🧠 Autonomous Intelligence (RAG Layer)

* Contextual contract analysis using LLM + Vector DB
* Detects zero-day threats via pattern recognition

---

### 🔗 On-Chain Trust Registry

* Community-vetted contract reputation system
* Immutable verification using Moonbase Parachain

---

### 🎓 Real-Time Education

* Explains *why* a transaction is risky
* Turns every alert into a learning experience

---

## 🧪 Example Scenario

User attempts to sign a transaction:

> “Approve unlimited USDT spending”

AEGIS detects:
⚠️ Potential wallet drain exploit

✅ Blocks transaction
🧠 Explains the risk

👉 User avoids losing funds

---

## 🛠️ Tech Stack

| Layer      | Technology           |
| ---------- | -------------------- |
| Backend    | FastAPI, Python      |
| AI Layer   | LLM, ChromaDB        |
| Blockchain | Solidity, Moonbase   |
| Database   | MySQL                |
| Frontend   | JavaScript, HTML/CSS |

---

## ⚙️ Installation

### ✅ Prerequisites

* Node.js >= v22.10.0
* Python = 3.11
* MySQL

💡 Recommended: Use a virtual environment

---

### 🐍 Setup Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate
# or
.\venv\bin\activate
```

---

### 🔐 Environment Variables

Create `.env` file:

```env
DB_URL=mysql+pymysql://root:yourpassword@localhost/aegisdb
GEMINI_API_KEY=your_api_key_here
```

---

### 📦 Clone Repository

```bash
git clone https://github.com/TiffnieXAI/AegisMain.git
cd .\AegisMain\
bash setup.ps1
```

---

### ⚒️ Setup Hardhat

```powershell
cd .\AegisMain\backend\hardhat_sim
npm install
```

---

### 🌐 Load Browser Extension

* Enable Developer Mode in browser
* Click “Load Unpacked”
* Select `aegis-extension` folder

---

### ▶️ Run the System

```powershell
cd .\AegisMain\backend\
uvicorn aegis:app --port 8000 --reload
```

```powershell
# In another terminal
cd .\AegisMain\ai\rag-semantic-layer\
uvicorn api:app --port 8001 --reload
```

---

## 🚀 Start Testing

Trigger smart contract transactions and let AEGIS:

✔ Simulate
✔ Analyze
✔ Warn
✔ Protect

---

## 🔮 Future Work

* Wallet integrations (MetaMask, Talisman)
* Mobile app version
* DAO-powered trust registry

---

## 📌 Final Note

AEGIS is not just a tool — it’s a **guardian layer for Web3 users**.

🔐 Safer
🧠 Smarter
🌍 More Accessible

> **Don’t trust. Verify. Understand.**
