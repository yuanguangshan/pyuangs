from trusted_agent_engine.engine.diff_parser import parse_unified_diff

def test_standard_git_diff():
    diff = ('diff --git a/src/app.ts b/src/app.ts\n'
            'index 83db48f..f735c20 100644\n'
            '--- a/src/app.ts\n'
            '+++ b/src/app.ts\n'
            '@@ -1,3 +1,4 @@\n'
            ' console.log("hello");\n'
            '+console.log("world");')
    result = parse_unified_diff(diff)
    assert result.filesTouched == ['src/app.ts']
    assert result.additions == 1
    assert result.deletions == 0
    assert result.hunks == 1

def test_file_deletion():
    diff = ('diff --git a/src/old.ts b/src/old.ts\n'
            'deleted file mode 100644\n'
            '--- a/src/old.ts\n'
            '+++ /dev/null\n'
            '@@ -1,2 +0,0 @@\n'
            '-console.log("bye");')
    result = parse_unified_diff(diff)
    assert result.filesTouched == ['src/old.ts']
    assert result.deletions == 1

def test_multiple_files():
    diff = ('diff --git a/A.ts b/A.ts\n'
            '--- a/A.ts\n'
            '+++ b/A.ts\n'
            '@@ -1 +1 @@\n'
            '-old\n'
            '+new\n'
            'diff --git a/B.ts b/B.ts\n'
            '--- a/B.ts\n'
            '+++ b/B.ts\n'
            '@@ -5 +5 @@\n'
            '+added')
    result = parse_unified_diff(diff)
    assert set(result.filesTouched) == {'A.ts', 'B.ts'}
    assert result.additions == 2
    assert result.deletions == 1
    assert result.hunks == 2
