🛡️ Agentic AI SRE: Autonomous Kubernetes DevSecOps

An Autonomous AI Agent that defends Kubernetes clusters by detecting, scanning, and patching vulnerable deployments in real-time.

📖 Overview

This Proof of Concept (PoC) demonstrates the future of Self-Healing Infrastructure. Instead of waiting for a human engineer to wake up at 3 AM to fix a broken deployment or a security vulnerability, this system uses Agentic AI to:

Audit the cluster state autonomously.

Scan container images for CVEs (Common Vulnerabilities and Exposures).

Reason about the best course of action (e.g., "Patch immediately" vs "Report only").

Execute remediation commands via kubectl.

Verify the fix resulted in a healthy state.

🏗️ Architecture

The system integrates a Local Kubernetes Cluster with Cloud AI via a Self-Hosted GitHub Action Runner.

flowchart TD
    User["Developer"] -->|"Push Code"| GH["GitHub Actions"]
    
    subgraph LocalMachine ["Your Local Machine (Self-Hosted Runner)"]
        direction TB
        GH -->|"Trigger"| Agent["🐍 Python AI Agent"]
        
        Agent -->|"1. List Pods"| K8s["Docker Desktop K8s"]
        Agent -->|"2. Scan Image"| Trivy["🛡️ Trivy Scanner"]
        
        Trivy -->|"Report CVEs"| Agent
        
        Agent -->|"3. Reasoning"| Groq["🧠 Groq Cloud API"]
        Groq -->|"Llama 3.3"| Agent
        
        Agent -->|"4. Auto-Patch"| K8s
        K8s -->|"5. Verify"| Agent
    end


🛠️ Tech Stack

Intelligence: Groq API running Llama 3.3 70B (Low latency, High reasoning).

Orchestration: LangChain (Tool calling and reasoning loop).

Infrastructure: Kubernetes (Docker Desktop).

Security: Trivy (Container Image Scanner).

Automation: GitHub Actions (Self-Hosted Windows Runner).

🚀 How to Run this Demo

Prerequisites

Windows Machine with Docker Desktop installed.

Kubernetes enabled in Docker Settings.

Python 3.10+ installed.

Groq API Key (Free tier).

Step 1: Clone & Configure

Fork/Clone this repository.

Create a .github/workflows/ai-sre.yml file (provided in repo).

Add your Groq API Key to GitHub Secrets:

Settings -> Secrets and variables -> Actions -> New Repository Secret

Name: GROQ_API_KEY

Value: gsk_...

Step 2: Setup Self-Hosted Runner

Since the K8s cluster is local, GitHub needs a bridge to reach it.

Go to Repo Settings -> Actions -> Runners -> New Self-Hosted Runner.

Select Windows.

Run the provided PowerShell commands on your machine.

Start the runner:

.\run.cmd


Step 3: Trigger the Attack & Defense

Go to the Actions tab in GitHub.

Run the "AI DevSecOps Pipeline".

Watch the Magic:

Attack: The pipeline deploys a vulnerable app (alpine:3.10).

Detection: The AI Agent sees the new pod.

Scan: It runs a security scan and finds critical CVEs.

Defense: The AI decides to patch it to alpine:3.20.

Success: The cluster heals itself without human intervention.

📝 Sample Logs (Actual Execution)

🤖 Starting AI Audit...
✅ DevSecOps Agent Online (Model: llama-3.3-70b-versatile)
   Monitoring Cluster for Security Compliance...

🛠️  k8s_get_all_pods args={'namespace': 'default'}
   -> Pod: ci-cd-vulnerable-5d64... | Status: Running | Image: alpine:3.10

🛡️  SECURITY: Scanning 'alpine:3.10' (this may take 10-20s)...
   -> ❌ VULNERABLE: Found 1 CRITICAL issues: CVE-2021-36159 (apk-tools)...

⚡ ACTION: Patching 'ci-cd-vulnerable' -> 'alpine:3.20'
   -> deployment.apps/ci-cd-vulnerable image updated...

📝 FINAL REPORT: Audit complete. 'alpine:3.10' was found, scanned, and patched to 'alpine:3.20'.


🔮 Future Roadmap

[ ] Slack Integration: Ask the human for permission before patching Production.

[ ] Vector Database: Remember past incidents to avoid repeating analysis.

[ ] Multi-Cluster: Manage AWS EKS and Azure AKS from one agent.

🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Author: Sadiq | License: MIT