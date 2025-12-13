# Networks_project
# 🛡️ Aegis Protocol: Reliable Datagram Telemetry Transport

## Project Overview

The **Aegis Protocol** is a high-performance, custom application-layer transport protocol built over UDP, designed for efficient and reliable telemetry data exchange in constrained environments. Developed in Python, this system demonstrates advanced concepts in network engineering, including Stop-and-Wait ARQ (Automatic Repeat Request), dynamic data batching, sequence numbering, and robust packet validation.

The core architectural goal was to maximize data throughput while adhering to a strict **200-byte maximum packet size constraint**.

------------------------------------------------------------------------------------------------------------------------------------------

## ✨ Key Technical Features

This project addresses the inherent unreliability of UDP by implementing a suite of crucial network functions:

* **Reliability (ARQ):** Implements a **Stop-and-Wait** mechanism with Retransmission Timeout (RTO) set at 0.5s to ensure guaranteed delivery of critical messages (`MSG_INIT`, `MSG_DATA`).
* **Efficiency (Batching):** Aggregates multiple sensor readings into a single packet to amortize the fixed 8-byte binary header overhead, significantly improving efficiency.
    * **Packet Size Constraint:** Strict enforcement of a maximum of **3 readings per packet** to ensure total packet size remains safely below the required **200-byte limit**.
* **Sequence Tracking & Deduplication:** The Server uses sequence numbers to identify and discard duplicate packets (to prevent data corruption) and detect sequence gaps (to monitor network health).
* **Binary Header:** Uses a highly compressed, fixed-size **8-byte** binary header (`<B B H L B`) for minimal overhead.
* **Network Simulation:** Includes server-side packet loss simulation and client-side duplicate transmission simulation for rigorous testing of the reliability mechanisms.

------------------------------------------------------------------------------------------------------------------------------------------

## ⚙️ Protocol Specification

### 1. Packet Size Constraint Enforcement

A primary design constraint is maintaining a packet size $\le 200$ bytes. The system enforces a maximum batch size of **3 readings**.

| Component | Size | Rationale |
| :--- | :--- | :--- |
| **Binary Header** | 8 bytes | Fixed size: `<B B H L B` |
| **Data Payload** | $3 \times 50 \text{ bytes}$ | Max 3 readings @ ~50 bytes each. |
| **JSON Overhead** | $\approx 10 \text{ bytes}$ | List structure (`[]`, commas, etc.). |
| **Total Packet Size** | **$\approx 168 \text{ bytes}$** | **Safely below the 200-byte limit.** |

### 2. Binary Header Structure (8 Bytes)

The header is packed using Python's `struct` module with the format string: **`<B B H L B`**.

| `struct` Format | Size (Bytes) | Protocol Field | Purpose |
| :--- | :--- | :--- | :--- |
| `B` | 1 | **VMT** | Packs 4-bit Protocol Version and 4-bit Message Type (Init, Data, Heartbeat, ACK). |
| `B` | 1 | **BatchCount** | Number of readings contained in the payload (0-255). |
| `H` | 2 | **SeqNum** | 16-bit Sequence Number for ARQ and Ordering. |
| `L` | 4 | **Timestamp** | 32-bit Unix timestamp of packet creation. |
| `B` | 1 | **Flags** | Reserved for future control flags. |

------------------------------------------------------------------------------------------------------------------------------------------

## 🚀 Getting Started

### Prerequisites

* Python 3.x
* The `argparse`, `socket`, `struct`, and `json` standard libraries (no external packages required).

### Execution

The server must be started first, followed by the client. Both applications log their performance and events to CSV files in the project root.

| Role | Script | Command |
| :--- | :--- | :--- |
| **Server** | `server_phase2.py` | `python server_phase2.py` |
| **Client** | `client_phase2.py` | `python client_phase2.py` |

------------------------------------------------------------------------------------------------------------------------------------------

## 📊 Automated Testing and Usage

The included PowerShell script, `run_test.ps1`, automates three scenarios to prove the protocol's stability and efficiency.

### 1. Running the Automated Tests

Execute the following command in PowerShell: (You just need the PowerShell dependency to be installed):

```powershell
.\run_test.ps1
```

### 2. Key Test Scenarios

Scenario	          |       Goal	                                                      |               Command Line Arguments
Baseline	          |     Test basic connectivity, RTT, and non-batched reliability.	  |                   --batch_size 1
Loss & Reliability  |	      Test packet loss recovery using the ARQ/RTO mechanism.	    |             server --simulate_loss 0.05
Stress Test	        |   Simultaneous random batching, packet loss, client duplication.  | --batch_size 3 --random_batch --simulate_dups 0.1

------------------------------------------------------------------------------------------------------------------------------------------

### 3. Performance Analysis

After testing, the following files are generated for analysis:

File Name               |          	            Data Logged	                       |                 Key Metric
client_measurements.csv	| Send time, ACK time, Sequence Number, Status, Batch Size |   	        Round Trip Time (RTT)
server_recv_log.csv	    |  Receive time, Sequence Number, Message Type, CPU Time	 | Duplicate Count, Packet Processing Latency

The data in these logs proves the system's ability to efficiently handle network anomalies and maintain data integrity.

------------------------------------------------------------------------------------------------------------------------------------------

## File Structure
```
.
├── client_phase2.py        # Telemetry Sensor Client (ARQ, Batching, RTO)
├── server_phase2.py        # Data Server (Deduplication, Gap Detection, ACK Logic)
├── run_test.ps1            # Automated test suite (PowerShell)
├── Helper.txt              # Manual test instructions and command list
├── .gitignore              # Ensures log files (*.csv) are ignored
└── README.md               # Project documentation (this file)
```
------------------------------------------------------------------------------------------------------------------------------------------

