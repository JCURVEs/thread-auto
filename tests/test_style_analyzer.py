"""Tests for Threads writing style analysis."""

from style_analyzer import analyze_style


def test_analyze_style_extracts_structure_and_voice_markers():
    posts = [
        {
            "username": "jokerburg.builder",
            "id": "root",
            "text": (
                "AI가 3D 모델을 아티스트처럼 만듭니다\n"
                "근데 뜯어보면 문제가 있습니다.\n"
                "핵심내용 정리했습니다🧵"
            ),
            "timestamp": "2026-08-07T01:02:03+00:00",
        },
        {
            "username": "jokerburg.builder",
            "id": "reply",
            "is_reply": True,
            "root_post_id": "root",
            "replied_to_id": "root",
            "text": (
                "1/ 꼭짓점 흐름으로 푸는 문제\n"
                "핵심은 이겁니다.\n"
                "쉽게 말하면 표면 위 방향표를 만드는 거죠."
            ),
            "timestamp": "2026-08-07T01:03:03+00:00",
        },
    ]

    profile = analyze_style(posts, username="jokerburg.builder")

    assert profile["sample_size"] == 2
    assert profile["structure"]["numbered_post_ratio"] == 0.5
    assert profile["structure"]["hook_phrase_ratio"] == 0.5
    assert profile["structure"]["thread_chain_count"] == 1
    markers = {item["text"] for item in profile["voice"]["style_markers"]}
    assert "근데" in markers
    assert "핵심은" in markers
    assert profile["generation_hints"]["use_numbered_slides"] is True
    assert profile["generation_hints"]["prefer_thread_chain"] is True
