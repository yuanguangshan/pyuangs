from fastapi import FastAPI, HTTPException, Body, Depends, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn
import os

from .. import TrustedGuard
from ..engine.types import Proposal, Decision

try:  # 已安装时取真实版本；源码直跑时退回默认值
    from importlib.metadata import version as _pkg_version, PackageNotFoundError
    APP_VERSION = _pkg_version("trusted-agent-engine")
except Exception:  # pragma: no cover
    APP_VERSION = "2.0.0"

# 这是一个能按路径读写磁盘的治理接口：默认只监听回环地址。
# 需要对外时显式 TAE_HOST=0.0.0.0，并强烈建议同时设置 TAE_API_TOKEN。
HOST = os.environ.get("TAE_HOST", "127.0.0.1")
API_TOKEN = os.environ.get("TAE_API_TOKEN")
ALLOWED_BASE = os.path.realpath(os.path.abspath(os.environ.get("TAE_BASE_DIR", os.getcwd())))

app = FastAPI(title="Trusted Governance API", version=APP_VERSION)

class EvaluationRequest(BaseModel):
    workspaceRoot: str
    proposal: Proposal
    allowUnsignedPolicy: bool = False

async def require_auth(authorization: Optional[str] = Header(None)) -> None:
    if not API_TOKEN:
        return
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/health")
async def health():
    return {"status": "ok", "engine": "trusted-agent-engine", "version": APP_VERSION}

@app.post("/v1/evaluate", response_model=Decision, dependencies=[Depends(require_auth)])
async def evaluate(request: EvaluationRequest = Body(...)):
    # 路径围栏：workspaceRoot 必须落在允许的基目录内（防任意路径读写）
    root = os.path.realpath(os.path.abspath(request.workspaceRoot))
    if root != ALLOWED_BASE and not root.startswith(ALLOWED_BASE + os.sep):
        raise HTTPException(status_code=400, detail={
            "error": "workspaceRoot is outside the allowed base directory",
            "allowedBase": ALLOWED_BASE,
        })
    if not os.path.exists(root):
        raise HTTPException(status_code=400, detail=f"Workspace root not found: {request.workspaceRoot}")

    try:
        decision = await TrustedGuard.evaluate(
            root, request.proposal,
            allow_unsigned_policy=request.allowUnsignedPolicy,
        )
        return decision
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    port = int(os.environ.get("PORT", 3000))
    print(f"🛡️ Trusted Governance API v{APP_VERSION} on http://{HOST}:{port}")
    print(f"Auth: {'Bearer token' if API_TOKEN else 'none (local only)'}")
    print(f"Workspace base dir: {ALLOWED_BASE}")
    uvicorn.run(app, host=HOST, port=port)

if __name__ == "__main__":
    main()
