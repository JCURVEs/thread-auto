import requests
import time
from typing import Dict, Any, Optional

THREADS_API_BASE = "https://graph.threads.net/v1.0"

def _create_container(
    user_id: str,
    access_token: str,
    text: str,
    image_url: Optional[str] = None,
    reply_to_id: Optional[str] = None
) -> Optional[str]:
    """
    Create a Threads media container.
    """
    url = f"{THREADS_API_BASE}/{user_id}/threads"
    params = {
        "access_token": access_token,
        "media_type": "IMAGE" if image_url else "TEXT",
        "text": text
    }
    
    if image_url:
        params["image_url"] = image_url
        
    if reply_to_id:
        params["reply_to_id"] = reply_to_id
        
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        container_id = response.json().get("id")
        return container_id
    except Exception as e:
        print(f"❌ 컨테이너 생성 실패: {e} | Response: {response.text}")
        return None

def _publish_container(
    user_id: str,
    access_token: str,
    creation_id: str
) -> Optional[str]:
    """
    Publish a created container.
    """
    url = f"{THREADS_API_BASE}/{user_id}/threads_publish"
    params = {
        "access_token": access_token,
        "creation_id": creation_id
    }
    
    try:
        # Rate limit safety wait
        time.sleep(2)
        
        response = requests.post(url, params=params)
        response.raise_for_status()
        post_id = response.json().get("id")
        return post_id
    except Exception as e:
        print(f"❌ 게시물 발행 실패: {e} | Response: {response.text}")
        return None

def post_to_threads(
    data: Dict[str, Any],
    image_url: Optional[str],
    source_url: str,
    access_token: str
) -> bool:
    """
    Post content to Threads using the Graph API.
    Supports single posts, images, and multi-threaded replies.
    """
    print("🚀 Threads API로 업로드 시작...")
    
    # 1. Get User ID (me)
    try:
        me_res = requests.get(f"{THREADS_API_BASE}/me", params={"access_token": access_token})
        me_res.raise_for_status()
        user_id = me_res.json().get("id")
    except Exception as e:
        print(f"❌ 사용자 정보 조회 실패: {e}")
        return False

    # 2. Main Post
    main_text = data.get("main_post", "")
    
    # Create Container
    container_id = _create_container(user_id, access_token, main_text, image_url)
    if not container_id:
        return False
        
    # Publish
    main_post_id = _publish_container(user_id, access_token, container_id)
    if not main_post_id:
        return False
        
    print(f"✅ 메인 포스트 게시 완료 (ID: {main_post_id})")
    
    # 3. Replies (if multi type)
    last_post_id = main_post_id
    
    if data.get("type") == "multi":
        replies = data.get("replies", [])
        for i, reply_text in enumerate(replies):
            print(f"   ↳ 대댓글 {i+1} 작성 중...")
            cont_id = _create_container(user_id, access_token, reply_text, reply_to_id=last_post_id)
            if cont_id:
                pub_id = _publish_container(user_id, access_token, cont_id)
                if pub_id:
                    last_post_id = pub_id
                else:
                    print(f"   ⚠️ 대댓글 {i+1} 게시 실패, 체인 중단")
                    break
            else:
                print(f"   ⚠️ 대댓글 {i+1} 컨테이너 생성 실패")
                break
    
    # 4. Source Link (Always last reply)
    print("   ↳ 출처 링크 작성 중...")
    source_text = f"출처: {source_url}"
    source_cont_id = _create_container(user_id, access_token, source_text, reply_to_id=last_post_id)
    if source_cont_id:
        _publish_container(user_id, access_token, source_cont_id)
        print("✅ 출처 링크 게시 완료")
    
    return True


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
