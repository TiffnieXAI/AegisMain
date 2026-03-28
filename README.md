# AEGIS

### Autonomous Evaluation & Guardian Intelligence System

> Stop signing blind transactions.
> AEGIS protects Web3 users *before* assets are lost.

---

## Core Areas

<table>
<tr>
<td align="center">
<img src="https://img.icons8.com/ios-filled/50/000000/blockchain-technology.png" width="40"/><br/>
<b>Web3</b>
</td>
<td align="center">
<img src="https://img.icons8.com/ios-filled/50/000000/artificial-intelligence.png" width="40"/><br/>
<b>Artificial Intelligence</b>
</td>
<td align="center">
<img src="https://img.icons8.com/ios-filled/50/000000/contract.png" width="40"/><br/>
<b>Smart Contracts</b>
</td>
<td align="center">
<img src="https://img.icons8.com/ios-filled/50/000000/network.png" width="40"/><br/>
<b>Parachains</b>
</td>
<td align="center">
<img src="https://img.icons8.com/ios-filled/50/000000/connected-people.png" width="40"/><br/>
<b>Polkadot</b>
</td>
</tr>
</table>

---

## Demo

Watch the demo:
[https://your-demo-link-here](https://your-demo-link-here)

![Demo](./assets/demo.gif)

---

## Why AEGIS?

### The Problem

Web3 transactions are **irreversible**, yet most users cannot understand what they are signing.

* Smart contract data is unreadable (hex)
* Users “blind sign” transactions
* One mistake leads to permanent loss of assets
* Attackers bypass traditional blocklists with new contracts

This creates a major barrier to **mass adoption**.

---

### The Solution

AEGIS introduces an **AI-powered security layer** between users and the blockchain.

It:

* Translates transactions into human-readable intent
* Simulates execution before approval
* Detects malicious patterns using AI
* Verifies trust using on-chain data

> Think: *Transaction simulation + AI analysis + on-chain verification*

---

## System Overview

![Architecture](./assets/architecture.png)

---

## Interface

### Transaction Analysis

![Analysis](./assets/analysis.png)

### Risk Warning

![Warning](./assets/warning.png)

### Dashboard

![Dashboard](./assets/dashboard.png)

---

## Features

### Live Interception

* Pre-execution simulation via Hardhat sandbox
* Human-readable intent extraction
* Real-time risk alerts

### Autonomous Intelligence (RAG Layer)

* Contract analysis using LLM + vector database
* Detection of zero-day threats via pattern recognition

### On-Chain Trust Registry

* Decentralized reputation system (Moonbase)
* Immutable verification of contract safety

### User Education

* Explains why transactions are flagged
* Helps users understand Web3 risks

---

## Architecture Diagram (PlantUML)

```plantuml
@startuml
actor User

User -> BrowserExtension : Initiate Transaction

BrowserExtension -> BackendAPI : Send Transaction Data

BackendAPI -> HardhatSimulator : Simulate Transaction
BackendAPI -> AIEngine : Analyze Intent (LLM + RAG)

AIEngine -> VectorDB : Retrieve Context
AIEngine -> BackendAPI : Risk Assessment

BackendAPI -> Blockchain : Query Trust Registry

BackendAPI -> BrowserExtension : Verdict + Warning

BrowserExtension -> User : Display Decision

@enduml
```

---

## Example Scenario

A user attempts to sign:

> Approve unlimited token spending

AEGIS:

* Simulates the transaction
* Detects abnormal permission scope
* Flags as high risk
* Explains the vulnerability

Result: the user avoids a potential wallet drain.

---

## Tech Stack

| Layer      | Technology           |
| ---------- | -------------------- |
| Backend    | FastAPI, Python      |
| AI Layer   | LLM, ChromaDB        |
| Blockchain | Solidity, Moonbase   |
| Database   | MySQL                |
| Frontend   | JavaScript, HTML/CSS |

---

## Installation

### Prerequisites

* Node.js >= v22.10.0
* Python = 3.11
* MySQL

> Tip: It is recommended to use a virtual environment to avoid dependency conflicts.

---

### Setup Python Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate
# or
.\venv\bin\activate
```

---

### Environment Variables

Create a `.env` file:

```env
DB_URL=mysql+pymysql://root:yourpassword@localhost/aegisdb
GEMINI_API_KEY=your_api_key_here
```

---

### Clone Repository

```bash
git clone https://github.com/TiffnieXAI/AegisMain.git
cd .\AegisMain\
bash setup.ps1
```

> You will be prompted to enter your MySQL password during database setup.

---

### Setup Hardhat

```powershell
cd .\AegisMain\backend\hardhat_sim
npm install
```

---

### Load Browser Extension

* Open your browser extensions
* Enable **Developer Mode**
* Click **Load Unpacked**
* Select the `aegis-extension` folder inside the backend directory

---

### Run the System

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

### Start Testing

Trigger transaction requests using smart contracts and observe how AEGIS:

* Simulates transactions
* Analyzes intent
* Flags risks
* Protects the user
