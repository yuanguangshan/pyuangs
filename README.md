# Trusted AI Agent Governance Engine (TAAGE) 🛡️

TAAGE is a governance engine designed for AI agents, featuring **sovereignty awareness** and **self-evolution** capabilities. It provides a solid defense boundary for AI behavior through physical decoupling of rule hot-loading, Ed25519 signature verification, and credit score game mechanisms.

## 🌟 Core Philosophy

1. **Sovereignty Over Intelligence**: Only the human with the private key is the commander-in-chief of the project. AI rule modifications must be signed by the sovereign.
2. **Trust, but Verify**: Every line of Diff passes through a multi-layer perception engine (anomaly detection, entropy analysis, risk matching) for decoupled review.
3. **Self-Audit**: The system automatically monitors governance health, identifying performance drift and permission creep.

---

## 🚀 Quick Start (Python)

### 1. Installation

```bash
pip install trusted-agent-engine
```

### 2. Initialize Sovereignty Keys

Generate your governance identity:

```bash
trusted-engine init
```

- `.ai/sovereign.key`: Your private key (**NEVER commit to Git**).
- `.ai/sovereign.pub`: Your public key.

### 3. Configure and Sign Policy

Create `agent.policy.yaml` and sign it with your private key:

```bash
# 1. Create policy
cat > agent.policy.yaml <<EOF
meta:
  mode: strict
  privileges: ["high-risk-decision"]
scopes:
  - id: "src"
    allow: ["src/**"]
rules:
  - id: "scope-enforcement"
    check: {"!": {"var": "engine.isScoped"}}
    action: "block"
    description: "Unauthorized file access detected"
EOF

# 2. Sign it
trusted-engine sign agent.policy.yaml
```

---

## 🛠 Integration Guide

### Option A: One-click Wrapper (Python)

```python
import asyncio
from trusted_agent_engine import TrustedGuard, Proposal

async def main():
    proposal = Proposal(
        id='p-001',
        author='ai-agent',
        reasoning='Update user login logic',
        files=['src/auth.py'],
        diff='... standard git diff ...'
    )

    # Evaluate: auto-load policy, verify signature, audit and log
    decision = await TrustedGuard.evaluate("./", proposal)

    if not decision.allowed:
        print(f"🚫 Blocked: {decision.audit_log}")
        return

    print(f"✅ Allowed, Value Score: {decision.valueScore}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Option B: CLI Interception

Run before your AI Agent executes tasks:

```bash
trusted-engine check --author=ai
```

---

## 🌐 API Service Mode

Start a standalone governance gateway:

```bash
trusted-engine serve
```

Default: `http://localhost:3000`.

---

## 📊 Governance Insights

The engine automatically discovers:

- **Trusted Patterns**: Suggests promoting frequently successful paths to trusted scopes.
- **Frequent Violations**: Suggests hardening rules that are frequently triggered.

Stored in `.ai/governance_assets.json`.

---

## ⚖️ License

MIT License.
# pyuangs
