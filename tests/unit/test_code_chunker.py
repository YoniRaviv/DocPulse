from docpulse.indexing.code_chunker import chunk_source

PY = """\
def helper(x):
    return x * 2


class AuthService:
    def login(self, user):
        return helper(user)
"""


def test_python_chunks():
    chunks = chunk_source("src/auth.py", PY)
    by_id = {c.id: c for c in chunks}
    assert "src/auth.py::helper" in by_id
    assert "src/auth.py::AuthService" in by_id
    assert "src/auth.py::AuthService.login" in by_id
    login = by_id["src/auth.py::AuthService.login"]
    assert login.kind == "method"
    assert login.signature == "def login(self, user):"
    assert login.start_line == 6
    assert by_id["src/auth.py::helper"].kind == "function"


def test_unknown_extension_returns_empty():
    assert chunk_source("notes.txt", "hello") == []
