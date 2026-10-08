"""异常检测：中文不是走私信号，真不可见字符才是。"""
from trusted_agent_engine.engine.anomaly_detector import AnomalyDetector
from trusted_agent_engine.engine.types import Proposal


def prop(diff: str, files=None) -> Proposal:
    return Proposal(id="a", timestamp=1.0, author="ai-agent",
                    reasoning="r", files=files or ["src/a.ts"], diff=diff)


def test_clean_change_is_not_anomaly():
    r = AnomalyDetector().detect(prop("+console.log('ok');\n" * 20))
    assert r.isAnomaly is False and r.score == 0.0


def test_chinese_text_is_not_obfuscation():
    """原 bug：非 ASCII > 20 个字符即 +0.6，本项目通篇中文必然误报。"""
    zh = "// 这是一段正常的中文注释，说明本次变更的目的、影响范围与回归测试策略。\n" * 6
    r = AnomalyDetector().detect(prop(zh))
    assert r.score == 0.0
    assert not any("obfuscation" in x for x in r.reasons)


def test_invisible_characters_are_flagged():
    hidden = "const a = 1;\n" * 30 + ("​‌‍" * 30)
    r = AnomalyDetector().detect(prop(hidden))
    assert r.score >= 0.6
    assert any("obfuscation" in x for x in r.reasons)


def test_large_diff_scores():
    r = AnomalyDetector().detect(prop("line\n" * 600))
    assert r.score >= 0.4
    assert any("large diff" in x for x in r.reasons)


def test_many_files_scores():
    files = [f"src/f{i}.ts" for i in range(11)]
    r = AnomalyDetector().detect(prop("+x", files=files))
    assert r.score >= 0.3
    assert any("Too many files" in x for x in r.reasons)


def test_combined_factors_cross_threshold():
    files = [f"src/f{i}.ts" for i in range(11)]
    r = AnomalyDetector().detect(prop("line\n" * 600, files=files))
    assert r.isAnomaly is True          # 0.4 + 0.3 >= 0.7
    assert r.score >= 0.7
