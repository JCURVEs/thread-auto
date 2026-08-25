"""Tests for local Threads asset storage."""

from threads_assets import group_posts_into_threads, normalize_post, read_jsonl, save_threads_export


def make_post(post_id, text="테스트 글입니다."):
    return {
        "id": post_id,
        "username": "jokerburg.builder",
        "text": text,
        "timestamp": "2026-08-07T01:02:03+0000",
        "media_type": "TEXT_POST",
        "media_url": "https://example.com/image.jpg",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "alt_text": "테스트 이미지",
        "permalink": f"https://threads.net/@jokerburg.builder/post/{post_id}",
    }


def test_normalize_post_parses_timestamp_and_text():
    normalized = normalize_post(make_post("1", "  핵심은 이겁니다.  "))

    assert normalized["id"] == "1"
    assert normalized["date"] == "2026-08-07"
    assert normalized["text"] == "핵심은 이겁니다."
    assert normalized["media_url"] == "https://example.com/image.jpg"
    assert normalized["thumbnail_url"] == "https://example.com/thumb.jpg"
    assert normalized["alt_text"] == "테스트 이미지"
    assert normalized["raw"]["id"] == "1"


def test_save_threads_export_writes_raw_and_deduped_normalized(tmp_path):
    data_dir = tmp_path / "threads"

    save_threads_export([make_post("1", "첫 글")], data_dir=data_dir, run_id="run1")
    raw_path, normalized_path, count = save_threads_export(
        [make_post("1", "수정된 글"), make_post("2", "둘째 글")],
        data_dir=data_dir,
        run_id="run2",
    )

    assert count == 2
    assert raw_path.exists()
    assert normalized_path.exists()

    normalized = read_jsonl(normalized_path)
    assert len(normalized) == 2
    assert {post["id"] for post in normalized} == {"1", "2"}
    assert next(post for post in normalized if post["id"] == "1")["text"] == "수정된 글"


def test_group_posts_into_threads_preserves_reply_chain_and_media():
    root = normalize_post(make_post("root", "AI 뉴스입니다."))
    reply = normalize_post({
        **make_post("reply", "1/ 핵심은 이겁니다."),
        "is_reply": True,
        "is_reply_owned_by_me": True,
        "root_post": {"id": "root"},
        "replied_to": {"id": "root"},
        "timestamp": "2026-08-07T01:03:03+0000",
    })

    threads = group_posts_into_threads([reply, root])

    assert len(threads) == 1
    assert threads[0]["root_post_id"] == "root"
    assert threads[0]["post_count"] == 2
    assert "AI 뉴스입니다." in threads[0]["combined_text"]
    assert "1/ 핵심은 이겁니다." in threads[0]["combined_text"]
    assert threads[0]["media"][0]["media_url"] == "https://example.com/image.jpg"
