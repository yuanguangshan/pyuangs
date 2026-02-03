import os
import json
from typing import List
from .types import DecisionTrace

class ContextBank:
    def __init__(self, workspace_root: str):
        self.storage_path = os.path.join(workspace_root, '.ai', 'ledger.jsonl')
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        directory = os.path.dirname(self.storage_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                pass

    async def record(self, trace: DecisionTrace) -> None:
        """
        Records a decision trace (Append-only JSONL).
        """
        log_entry = trace.model_dump_json() + '\n'
        with open(self.storage_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    async def get_history(self) -> List[DecisionTrace]:
        """
        Retrieves historical decisions.
        """
        if not os.path.exists(self.storage_path):
            return []
        
        traces = []
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    traces.append(DecisionTrace.model_validate_json(line))
        
        return traces[::-1]  # Return most recent first

    async def get_success_rate(self) -> float:
        """
        Calculates recent success rate.
        """
        history = await self.get_history()
        recent = history[:1000]
        if not recent:
            return 1.0
        
        applied = sum(1 for t in recent if t.outcome == 'applied')
        return applied / len(recent)
