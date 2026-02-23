from lms_llmsTxt.reasoning import canonicalize_response, sanitize_final_output


def test_sanitize_removes_think_block():
    raw = "<think>internal chain</think>\n\n## Final\ncontent"
    out = sanitize_final_output(raw)
    assert out.was_modified is True
    assert "<think>" not in out.text
    assert out.text.startswith("## Final")


def test_sanitize_strict_prefix_handling():
    raw = "Reasoning: hidden notes\n## Heading\nBody"
    strict_out = sanitize_final_output(raw, strict=True)
    lenient_out = sanitize_final_output(raw, strict=False)
    assert "Reasoning:" not in strict_out.text
    assert "Reasoning:" in lenient_out.text


def test_canonicalize_dict_and_string():
    d = {"content": "final", "reasoning_content": "analysis"}
    out = canonicalize_response(d)
    assert out.final_text == "final"
    assert out.reasoning_text == "analysis"

    s = canonicalize_response("plain text")
    assert s.final_text == "plain text"
    assert s.reasoning_text is None
