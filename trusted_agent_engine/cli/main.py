import os
import sys
import subprocess
import time
import json
import yaml
import asyncio
import argparse
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..engine.evaluator import PolicyEngine
from ..engine.diff_parser import parse_unified_diff
from ..engine.policy_loader import load_policy
from ..engine.types import Proposal, DecisionTrace, PolicyConfig, ValueManifesto
from ..engine.context_bank import ContextBank
from ..engine.asset_manager import AssetManager
from ..engine.self_audit import SelfAuditor
from ..engine.sovereign import SovereignManager
from ..api.server import main as run_server

console = Console()

def get_git_diff() -> str:
    try:
        # Try staged changes first
        diff = subprocess.check_output(['git', 'diff', '--cached'], stderr=subprocess.STDOUT).decode('utf-8')
        if not diff:
            # Fallback to unstaged changes
            diff = subprocess.check_output(['git', 'diff'], stderr=subprocess.STDOUT).decode('utf-8')
        return diff
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error running git diff:[/bold red] {e.output.decode('utf-8') if e.output else 'Unknown error'}")
        return ""
    except FileNotFoundError:
        console.print("[bold red]Error:[/bold red] git command not found.")
        return ""

async def check_command(args):
    cwd = os.getcwd()
    policy_path = os.path.join(cwd, args.policy)
    pub_key_path = os.path.join(cwd, '.ai', 'sovereign.pub')
    
    public_key = None
    if os.path.exists(pub_key_path):
        with open(pub_key_path, 'r', encoding='utf-8') as f:
            public_key = f.read()
            
    try:
        config = load_policy(policy_path, public_key=public_key)
    except Exception as e:
        console.print(f"[bold red]Error loading policy:[/bold red] {e}")
        sys.exit(1)

    manifesto_path = os.path.join(cwd, 'value_manifesto.yaml')
    manifesto = None
    if os.path.exists(manifesto_path):
        try:
            with open(manifesto_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                manifesto = ValueManifesto.model_validate(data)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load value_manifesto.yaml: {e}[/yellow]")

    engine = PolicyEngine(config, manifesto, cwd)
    bank = ContextBank(cwd)

    diff = get_git_diff()
    if not diff:
        console.print("[yellow]No changes detected.[/yellow]")
        sys.exit(0)

    analysis = parse_unified_diff(diff)
    author = 'ai-agent' if args.author == 'ai' else 'human'
    
    proposal = Proposal(
        id=f"cli-{int(time.time())}",
        timestamp=time.time(),
        author=author,
        reasoning="Changes from local environment.",
        files=analysis.filesTouched,
        diff=diff
    )

    decision = engine.evaluate(proposal)

    trace = DecisionTrace(
        **decision.model_dump(),
        proposal=proposal,
        outcome='applied' if decision.allowed else 'rejected'
    )
    
    await bank.record(trace)
    
    history = await bank.get_history()
    asset_manager = AssetManager()
    assets = asset_manager.mine(history)
    if assets:
        console.print("\n[bold cyan]--- Governance Insights ---[/bold cyan]")
        for asset in assets[:3]:
            console.print(f"💡 [bold]{asset.type.upper()}[/bold] {asset.description}")
        
    self_auditor = SelfAuditor()
    report = self_auditor.audit(history)
    if report.findings:
        console.print(f"\n[bold cyan]--- System Self-Audit (Health: {report.healthScore}/100) ---[/bold cyan]")

    result_text = "✅ ALLOWED" if decision.allowed else "❌ BLOCKED"
    result_color = "green" if decision.allowed else "red"
    
    console.print(Panel(
        f"[bold {result_color}]Result: {result_text}[/bold {result_color}]\n"
        f"Risk Level: {decision.riskLevel.upper()}\n"
        f"Value Score: {decision.valueScore:.2f if decision.valueScore is not None else 'N/A'}",
        title="Trusted Agent Policy Report",
        expand=False
    ))

    if not decision.allowed:
        sys.exit(1)

def init_command(args):
    ai_dir = os.path.join(os.getcwd(), '.ai')
    if not os.path.exists(ai_dir):
        os.makedirs(ai_dir)
        
    priv_key_path = os.path.join(ai_dir, 'sovereign.key')
    pub_key_path = os.path.join(ai_dir, 'sovereign.pub')
    
    if os.path.exists(priv_key_path) and not args.force:
        console.print("[yellow]Sovereign keys already exist. Use --force to overwrite.[/yellow]")
        return

    private_key, public_key = SovereignManager.generate_key_pair()
    with open(priv_key_path, 'w', encoding='utf-8') as f:
        f.write(private_key)
    with open(pub_key_path, 'w', encoding='utf-8') as f:
        f.write(public_key)
        
    console.print(f"[green]Sovereign keys generated in .ai/[/green]")
    console.print(f"Private Key: {priv_key_path} (KEEP IT SECRET!)")
    console.print(f"Public Key: {pub_key_path}")

def sign_command(args):
    ai_dir = os.path.join(os.getcwd(), '.ai')
    priv_key_path = os.path.join(ai_dir, 'sovereign.key')
    
    if not os.path.exists(priv_key_path):
        console.print("[bold red]Error: Private key not found. Run 'init' first.[/bold red]")
        sys.exit(1)
        
    policy_path = args.policy
    if not os.path.exists(policy_path):
        console.print(f"[bold red]Error: Policy file not found: {policy_path}[/bold red]")
        sys.exit(1)
        
    with open(priv_key_path, 'r', encoding='utf-8') as f:
        private_key = f.read()
    with open(policy_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    signature = SovereignManager.sign_policy(content, private_key)
    sig_path = f"{policy_path}.sig"
    with open(sig_path, 'w', encoding='utf-8') as f:
        f.write(signature)
        
    console.print(f"[green]Signed {policy_path}. Signature saved to {sig_path}[/green]")

def main():
    parser = argparse.ArgumentParser(description="Trusted Agent Engine CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Check
    check_parser = subparsers.add_parser("check", help="Evaluate current changes")
    check_parser.add_argument("--policy", default="agent.policy.yaml", help="Path to policy file")
    check_parser.add_argument("--author", choices=["human", "ai"], default="human", help="Author of changes")

    # Init
    init_parser = subparsers.add_parser("init", help="Initialize sovereign keys")
    init_parser.add_argument("--force", action="store_true", help="Force overwrite existing keys")

    # Sign
    sign_parser = subparsers.add_parser("sign", help="Sign a policy file")
    sign_parser.add_argument("policy", nargs="?", default="agent.policy.yaml", help="Path to policy file")

    # Serve
    serve_parser = subparsers.add_parser("serve", help="Start governance API server")
    
    args = parser.parse_args()

    if args.command == "check":
        asyncio.run(check_command(args))
    elif args.command == "init":
        init_command(args)
    elif args.command == "sign":
        sign_command(args)
    elif args.command == "serve":
        run_server()
    else:
        # Default to check if no command provided
        asyncio.run(check_command(argparse.Namespace(policy="agent.policy.yaml", author="human")))

if __name__ == "__main__":
    main()
