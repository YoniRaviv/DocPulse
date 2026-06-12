from docpulse.cli import _base_branch, _pr_number


def test_base_branch_strips_origin_prefix():
    assert _base_branch("origin/main") == "main"
    assert _base_branch("origin/feature/x") == "feature/x"
    assert _base_branch("main") == "main"


def test_pr_number_explicit_env():
    assert _pr_number({"DOCPULSE_PR_NUMBER": "12"}) == "12"
    assert _pr_number({"PR_NUMBER": "13"}) == "13"


def test_pr_number_from_github_ref():
    assert _pr_number({"GITHUB_REF": "refs/pull/99/merge"}) == "99"


def test_pr_number_none_when_absent():
    assert _pr_number({}) is None
