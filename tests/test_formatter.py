
import pytest
from thread_formatter import format_output, generate_summary, print_dry_run

# Fixtures for test data
@pytest.fixture
def single_post_data():
    return {
        "type": "single",
        "main_post": "This is a single post.",
        "replies": []
    }

@pytest.fixture
def multi_post_data():
    return {
        "type": "multi",
        "main_post": "This is the main post of a thread.",
        "replies": [
            "This is the first reply.",
            "This is the second reply."
        ]
    }

def test_format_output_single(single_post_data):
    """Test formatting for a single post."""
    image_url = "http://example.com/img.jpg"
    source_url = "http://example.com/source"
    
    result = format_output(single_post_data, image_url, source_url)
    
    assert result["type"] == "single"
    assert result["main_post"]["text"] == "This is a single post."
    assert result["main_post"]["image_url"] == image_url
    assert result["source_reply"] == f"출처 : {source_url}"
    assert len(result["replies"]) == 0

def test_format_output_multi(multi_post_data):
    """Test formatting for a multi-post thread."""
    image_url = None
    source_url = "http://example.com/source"
    
    result = format_output(multi_post_data, image_url, source_url)
    
    assert result["type"] == "multi"
    assert result["main_post"]["text"] == "This is the main post of a thread."
    assert result["main_post"]["image_url"] is None
    assert len(result["replies"]) == 2
    assert result["replies"][0] == "This is the first reply."

def test_generate_summary(single_post_data, multi_post_data):
    """Test utility summary generation."""
    summary_single = generate_summary(single_post_data)
    assert "Type: SINGLE" in summary_single
    assert "Replies: 0" in summary_single
    
    summary_multi = generate_summary(multi_post_data)
    assert "Type: MULTI" in summary_multi
    assert "Replies: 2" in summary_multi

def test_print_dry_run_no_error(capsys, multi_post_data):
    """
    Test print_dry_run to ensure it prints expected content and doesn't crash.
    Using capsys to capture stdout.
    """
    # Simply running it to ensure no exceptions
    print_dry_run(multi_post_data, "http://img.com/a.jpg", "http://src.com")
    
    captured = capsys.readouterr()
    assert "[DRY RUN]" in captured.out
    assert "메인 포스트" in captured.out
    assert "대댓글" in captured.out
    assert "출처 페이지" in captured.out
