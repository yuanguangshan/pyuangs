from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn
import os

from .. import TrustedGuard
from ..engine.types import Proposal, Decision

app = FastAPI(title="Trusted Governance API", version="2.0.0")

class EvaluationRequest(BaseModel):
    workspaceRoot: str
    proposal: Proposal

@app.get("/health")
async def health():
    return {"status": "ok", "engine": "trusted-agent-engine", "version": "2.0.0"}

@app.post("/v1/evaluate", response_model=Decision)
async def evaluate(request: EvaluationRequest = Body(...)):
    try:
        # Check if workspace exists
        if not os.path.exists(request.workspaceRoot):
            raise HTTPException(status_code=400, detail=f"Workspace root not found: {request.workspaceRoot}")
            
        decision = await TrustedGuard.evaluate(request.workspaceRoot, request.proposal)
        return decision
    except Exception as e:
        # Log error in production
        print(f"[API Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
