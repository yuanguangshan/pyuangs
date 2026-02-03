from typing import List, Set, Dict
from pydantic import BaseModel

class DiffAnalysis(BaseModel):
    filesTouched: List[str]
    additions: int
    deletions: int
    hunks: int

def parse_unified_diff(diff: str) -> DiffAnalysis:
    """
    Parse unified diff and extract factual change data.
    """
    files: Set[str] = set()
    additions = 0
    deletions = 0
    hunks = 0

    lines = diff.split('\n')

    for line in lines:
        # 1. diff --git header
        if line.startswith('diff --git '):
            parts = line.split(' ')
            b_path = parts[-1]  # b/path
            if b_path.startswith('b/'):
                files.add(b_path[2:])
            continue

        # 2. --- and +++ headers
        if line.startswith('--- ') or line.startswith('+++ '):
            path_part = line[4:].strip()
            if path_part.startswith('a/') or path_part.startswith('b/'):
                files.add(path_part[2:])
            elif path_part != '/dev/null' and path_part != '':
                files.add(path_part)
            continue

        # Support for 4+ pluses/minuses
        if line.startswith('----') or line.startswith('++++'):
            continue

        # 3. Hunk header
        if line.startswith('@@'):
            hunks += 1
            continue

        # 4. Content stats
        if line.startswith('---') or line.startswith('+++') or line.startswith('diff --git'):
            continue

        if line.startswith('+'):
            additions += 1
        elif line.startswith('-'):
            deletions += 1

    return DiffAnalysis(
        filesTouched=list(files),
        additions=additions,
        deletions=deletions,
        hunks=hunks
    )
