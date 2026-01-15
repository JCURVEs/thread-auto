"""
Thread Formatter module for Thread-Auto.

This module handles formatting and outputting the generated thread content.
Supports both Dry Run (log output) and Production (Threads API) modes.
"""

from typing import Dict, Any, Optional


def format_output(
    data: Dict[str, Any],
    image_url: Optional[str],
    source_url: str
) -> Dict[str, Any]:
    """
    Format the AI-generated content into a structured output.

    Args:
        data: AI-generated content dictionary.
        image_url: Image URL to attach (or None).
        source_url: Original article URL for source citation.

    Returns:
        Formatted output dictionary ready for posting.

    Example:
        >>> output = format_output(data, image_url, source_url)
        >>> print(output['main_post'])
    """
    return {
        "type": data.get("type", "single"),
        "main_post": {
            "text": data.get("main_post", ""),
            "image_url": image_url
        },
        "replies": data.get("replies", []),
        "source_reply": f"출처 : {source_url}"
    }


def print_dry_run(
    data: Dict[str, Any],
    image_url: Optional[str],
    source_url: str
) -> None:
    """
    Print formatted output for Dry Run testing.

    Args:
        data: AI-generated content dictionary.
        image_url: Image URL to attach (or None).
        source_url: Original article URL for source citation.

    Example:
        >>> print_dry_run(data, image_url, source_url)
    """
    separator = "=" * 50
    sub_separator = "-" * 30

    print(f"\n{separator}")
    print(f"📢 [DRY RUN] 게시물 타입: {data.get('type', 'unknown').upper()}")
    print(separator)

    # Main post
    print(f"\n[1] 메인 포스트")
    if image_url:
        print(f"    🖼️ 이미지: {image_url}")
    else:
        print("    🖼️ 이미지: 없음")
    print(sub_separator)
    print(data.get("main_post", ""))

    # Replies (for multi-thread)
    if data.get("type") == "multi":
        replies = data.get("replies", [])
        for i, reply in enumerate(replies):
            print(f"\n[{i + 2}] 대댓글")
            print(sub_separator)
            print(reply)

    # Source citation (always last)
    reply_num = len(data.get("replies", [])) + 2 if data.get("type") == "multi" else 2
    print(f"\n[{reply_num}] 출처 페이지")
    print(sub_separator)
    print(f"출처 : {source_url}")

    print(f"\n{separator}")
    print("✅ Dry Run 완료. 실제 Threads에는 업로드되지 않았습니다.")
    print(separator + "\n")


def post_to_threads(
    data: Dict[str, Any],
    image_url: Optional[str],
    source_url: str,
    access_token: str
) -> bool:
    """
    Post content to Threads using the API.

    Note: This is a placeholder for future implementation.
    Requires Meta Threads API integration.

    Args:
        data: AI-generated content dictionary.
        image_url: Image URL to attach (or None).
        source_url: Original article URL for source citation.
        access_token: Threads API access token.

    Returns:
        True if posting successful, False otherwise.

    Example:
        >>> success = post_to_threads(data, image_url, source_url, token)
    """
    # TODO: Implement actual Threads API integration
    # Reference: https://developers.facebook.com/docs/threads
    print("⚠️ Threads API 업로드는 아직 구현되지 않았습니다.")
    print("   Production 모드를 사용하려면 Threads API 연동이 필요합니다.")
    return False


def generate_summary(data: Dict[str, Any]) -> str:
    """
    Generate a brief summary of the content for logging.

    Args:
        data: AI-generated content dictionary.

    Returns:
        Summary string.

    Example:
        >>> summary = generate_summary(data)
        >>> print(summary)
    """
    content_type = data.get("type", "unknown")
    main_post = data.get("main_post", "")
    preview = main_post[:50] + "..." if len(main_post) > 50 else main_post
    reply_count = len(data.get("replies", []))

    return (
        f"Type: {content_type.upper()}, "
        f"Replies: {reply_count}, "
        f"Preview: {preview}"
    )
