from docpulse.indexing.doc_parser import parse_markdown

SAMPLE = """\
# Authentication

Intro paragraph.

## Login Flow

Call `AuthService.login` with a user_name to get a token.

~~~python
# this heading-looking line must be ignored
print("hi")
~~~

## Logout

Uses `AuthService.logout`.
"""


def test_sections_by_heading_path():
    sections = parse_markdown("docs/auth.md", SAMPLE)
    ids = [s.id for s in sections]
    assert ids == [
        "docs/auth.md#authentication",
        "docs/auth.md#authentication/login-flow",
        "docs/auth.md#authentication/logout",
    ]
    login = sections[1]
    assert login.heading_path == ["Authentication", "Login Flow"]
    assert "AuthService.login" in login.content
    assert login.start_line == 5


def test_fenced_code_does_not_create_sections():
    # the parser treats both ``` and ~~~ as fences; the sample uses ~~~
    sections = parse_markdown("docs/auth.md", SAMPLE)
    assert all("heading-looking" not in s.id for s in sections)
    assert len(sections) == 3


def test_mentions_extracted():
    sections = parse_markdown("docs/auth.md", SAMPLE)
    login = sections[1]
    assert "AuthService.login" in login.mentions   # backticked
    assert "user_name" in login.mentions           # snake_case in prose
