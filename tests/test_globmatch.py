"""minimatch 兼容性：与 TypeScript 版保持同一套通配语义。

fnmatch 的 * 会跨越 /，导致 src/* 放行 src/deep/secret.ts（fail-open 漂移）。
"""
from trusted_agent_engine.engine.globmatch import minimatch, minimatch_all

CASES = [
    # (path, pattern, expected)
    ("src/a.ts", "src/**", True),
    ("src/deep/a.ts", "src/**", True),
    ("src/deep/deeper/a.ts", "src/**", True),
    ("src/a.ts", "src/*", True),
    ("src/deep/a.ts", "src/*", False),        # minimatch：* 不跨目录
    ("README.md", "README.md", True),
    ("docs/x.md", "README.md", False),
    ("docs/x.md", "docs/**", True),
    (".env", "**/.env*", True),
    ("cfg/.env.local", "**/.env*", True),
    ("docker-compose.yml", "**/docker-compose.yml", True),
    ("src/auth/login.ts", "src/auth/**", True),
    ("src/other/login.ts", "src/auth/**", False),
    ("src/a.ts", "**/*.ts", True),
    ("a/b/c.ts", "src/**", False),
    ("src/a.ts", "src/?.ts", True),
    ("src/ab.ts", "src/?.ts", False),
]


def test_minimatch_parity():
    for path, pattern, expected in CASES:
        assert minimatch(path, pattern) is expected, f"{path} vs {pattern} -> {minimatch(path, pattern)}"


def test_minimatch_all_filters():
    paths = ["src/a.ts", "src/deep/b.ts", "README.md"]
    assert minimatch_all(paths, "src/**") == ["src/a.ts", "src/deep/b.ts"]
    assert minimatch_all(paths, "src/*") == ["src/a.ts"]


def test_non_string_inputs_are_not_matching():
    assert minimatch(None, "src/**") is False
    assert minimatch("src/a.ts", None) is False


def test_dot_prefix_is_normalised():
    assert minimatch("./src/a.ts", "src/**") is True
    assert minimatch("src/a.ts", "./src/**") is True
