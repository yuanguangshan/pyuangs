"""主权签名与策略加载：fail-closed 是这个包的核心卖点，必须有测试兜底。"""
import pytest

from trusted_agent_engine.engine.policy_loader import load_policy
from trusted_agent_engine.engine.sovereign import SovereignManager

POLICY = """meta:
  mode: strict
scopes: []
risks: []
rules: []
"""


@pytest.fixture()
def keys():
    return SovereignManager.generate_key_pair()


def test_sign_and_verify_roundtrip(tmp_path, keys):
    priv, pub = keys
    sig = SovereignManager.sign_policy(POLICY, priv)
    assert SovereignManager.verify_policy(POLICY, sig, pub) is True


def test_tampered_policy_fails_verification(tmp_path, keys):
    priv, pub = keys
    sig = SovereignManager.sign_policy(POLICY, priv)
    tampered = POLICY.replace("mode: strict", "mode: monitor")
    assert SovereignManager.verify_policy(tampered, sig, pub) is False


def test_garbage_signature_returns_false_not_exception(tmp_path, keys):
    _priv, pub = keys
    assert SovereignManager.verify_policy(POLICY, "not-a-signature", pub) is False
    assert SovereignManager.verify_policy(POLICY, "AAAA", pub) is False


def test_load_policy_with_valid_signature(tmp_path, keys):
    priv, pub = keys
    p = tmp_path / "agent.policy.yaml"
    p.write_text(POLICY, encoding="utf-8")
    p.with_suffix(".yaml.sig").write_text(SovereignManager.sign_policy(POLICY, priv), encoding="utf-8")
    cfg = load_policy(str(p), public_key=pub)
    assert cfg.meta["mode"] == "strict"


def test_load_policy_rejects_tampered_file(tmp_path, keys):
    priv, pub = keys
    p = tmp_path / "agent.policy.yaml"
    p.write_text(POLICY, encoding="utf-8")
    p.with_suffix(".yaml.sig").write_text(SovereignManager.sign_policy(POLICY, priv), encoding="utf-8")
    p.write_text(POLICY.replace("mode: strict", "mode: monitor"), encoding="utf-8")
    with pytest.raises(ValueError, match="Unauthorized policy modification"):
        load_policy(str(p), public_key=pub)


def test_load_policy_missing_signature_file(tmp_path, keys):
    _priv, pub = keys
    p = tmp_path / "agent.policy.yaml"
    p.write_text(POLICY, encoding="utf-8")
    with pytest.raises(ValueError, match="signature missing"):
        load_policy(str(p), public_key=pub)


def test_load_policy_without_public_key_is_fail_closed(tmp_path):
    """原 bug：没有公钥就静默跳过验签 —— 删掉 .ai/sovereign.pub 等于关掉全部保护。"""
    p = tmp_path / "agent.policy.yaml"
    p.write_text(POLICY, encoding="utf-8")
    with pytest.raises(ValueError, match="fail-closed"):
        load_policy(str(p))                      # 默认拒绝
    cfg = load_policy(str(p), allow_unsigned=True)   # 显式放行才通过
    assert cfg.meta["mode"] == "strict"


def test_missing_policy_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_policy(str(tmp_path / "nope.yaml"), allow_unsigned=True)
