import pytest

from opengriffin import web_tools


def test_html_to_text_removes_active_content():
    text = web_tools._html_to_text(
        "<html><script>alert(1)</script><h1>Headline</h1><p>Hello <b>web</b></p></html>"
    )
    assert "Headline" in text
    assert "Hello" in text and "web" in text
    assert "alert" not in text


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1:8080/",
        "http://10.0.0.1/",
        "http://[::1]/",
    ],
)
def test_public_url_blocks_non_public_hosts(url):
    with pytest.raises(ValueError):
        web_tools._public_url(url)


def test_search_without_key_is_safe(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert "not configured" in web_tools._tavily_search("OpenGriffin")
