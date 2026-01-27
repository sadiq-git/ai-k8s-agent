# 🛡️ Agentic AI SRE: Autonomous Kubernetes DevSecOps

An Autonomous AI Agent that defends Kubernetes clusters by detecting, scanning, and patching vulnerable deployments in real-time.

## 📖 Overview

This Proof of Concept (PoC) demonstrates the future of Self-Healing Infrastructure. Instead of waiting for a human engineer to wake up at 3 AM to fix a broken deployment or a security vulnerability, this system uses Agentic AI to:

* Audit the cluster state autonomously.
* Scan container images for CVEs (Common Vulnerabilities and Exposures).
* Reason about the best course of action (e.g., "Patch immediately" vs "Report only").
* Execute remediation commands via `kubectl`.
* Verify the fix resulted in a healthy state.

## 🏗️ Architecture

The system integrates a Local Kubernetes Cluster with Cloud AI via a Self-Hosted GitHub Action Runner.

```mermaid
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