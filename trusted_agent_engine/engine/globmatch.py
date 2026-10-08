"""minimatch-compatible glob matching.

Why not ``fnmatch``
-------------------
``fnmatch`` lets ``*`` cross ``/`` (``fnmatch("src/a/b.ts", "src/*")`` is
``True``), while the TypeScript engine uses ``minimatch`` where ``*`` stays
inside one path segment.  For a scope-enforcement engine that difference is
fail-open in Python: ``src/*`` would silently authorise ``src/deep/secrets.ts``.
This module reproduces minimatch semantics for the subset used by policies:

* ``*``   matches within one segment (never crosses ``/``)
* ``**``  matches zero or more whole segments
* ``?``   matches exactly one character inside a segment
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import List

__all__ = ["minimatch", "minimatch_all"]


def _segment_to_regex(segment: str) -> str:
    out = []
    i = 0
    while i < len(segment):
        ch = segment[i]
        if ch == "*":
            out.append(".*")
        elif ch == "?":
            out.append(".")
        else:
            out.append(re.escape(ch))
        i += 1
    return "^" + "".join(out) + "$"


@lru_cache(maxsize=512)
def _compile(pattern: str):
    # '**' 必须保持字面量标记：_match() 靠它识别 globstar 分支
    return ["**" if seg == "**" else _segment_to_regex(seg) for seg in pattern.split("/")]


def _match(segments: List[str], path: List[str], pi: int, si: int, memo=None) -> bool:
    if memo is None:
        memo = {}
    key = (si, pi)
    if key in memo:
        return memo[key]

    result: bool
    if si == len(segments):
        result = pi == len(path)
    elif segments[si] == "**":
        # ** 可以吃 0..n 段
        result = any(_match(segments, path, pi + skip, si + 1, memo)
                     for skip in range(0, len(path) - pi + 1))
    elif pi >= len(path):
        result = False
    else:
        seg_re = segments[si]
        result = re.match(seg_re, path[pi]) is not None and _match(segments, path, pi + 1, si + 1, memo)

    memo[key] = result
    return result


def minimatch(path: str, pattern: str) -> bool:
    """Return True when ``path`` matches ``pattern`` with minimatch semantics."""
    if not isinstance(path, str) or not isinstance(pattern, str):
        return False
    # 绝对路径与 ./ 前缀在策略里通常写作相对路径，统一掉
    path = path[2:] if path.startswith("./") else path
    pattern = pattern[2:] if pattern.startswith("./") else pattern
    segs = _compile(pattern)
    return _match(segs, path.split("/"), 0, 0)


def minimatch_all(paths, pattern):
    """Filter ``paths`` keeping only those matching ``pattern``."""
    return [p for p in paths if minimatch(p, pattern)]
