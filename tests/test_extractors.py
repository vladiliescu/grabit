from clipit.core import extractor


def test_extract_readable_content_uses_python_mode_when_runtime_is_unavailable(monkeypatch):
    observed_calls: list[bool] = []

    def fake_simple_json_from_html_string(_html_content, use_readability):
        observed_calls.append(use_readability)
        return {"content": "<p>Example</p>", "title": "Example"}

    monkeypatch.setattr(extractor, "ensure_readabilipy_node_runtime", lambda: False)
    monkeypatch.setattr(extractor, "simple_json_from_html_string", fake_simple_json_from_html_string)

    content_html, title = extractor.extract_readable_content_and_title("<html></html>", True)

    assert observed_calls == [False]
    assert content_html == "<p>Example</p>"
    assert title == "Example"


def test_extract_readable_content_falls_back_to_python_mode_when_js_extracts_no_content(monkeypatch):
    observed_calls: list[bool] = []

    def fake_simple_json_from_html_string(_html_content, use_readability):
        observed_calls.append(use_readability)
        if use_readability:
            return {"content": "", "title": "Example"}
        return {"content": "<p>Example</p>", "title": "Example"}

    monkeypatch.setattr(extractor, "ensure_readabilipy_node_runtime", lambda: True)
    monkeypatch.setattr(extractor, "simple_json_from_html_string", fake_simple_json_from_html_string)

    content_html, title = extractor.extract_readable_content_and_title("<html></html>", True)

    assert observed_calls == [True, False]
    assert content_html == "<p>Example</p>"
    assert title == "Example"


def test_extract_readable_content_falls_back_to_python_mode_when_js_raises(monkeypatch):
    observed_calls: list[bool] = []

    def fake_simple_json_from_html_string(_html_content, use_readability):
        observed_calls.append(use_readability)
        if use_readability:
            raise RuntimeError("broken js runtime")
        return {"content": "<p>Example</p>", "title": "Example"}

    monkeypatch.setattr(extractor, "ensure_readabilipy_node_runtime", lambda: True)
    monkeypatch.setattr(extractor, "simple_json_from_html_string", fake_simple_json_from_html_string)

    content_html, title = extractor.extract_readable_content_and_title("<html></html>", True)

    assert observed_calls == [True, False]
    assert content_html == "<p>Example</p>"
    assert title == "Example"
