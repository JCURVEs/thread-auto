import requests
import time
from typing import Dict, Any, Optional


def format_output(
    data: Dict[str, Any],
    image_url: Optional[str],
    source_url: str
) -> Dict[str, Any]:
    """
    Format the AI-generated content into a structured output.
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
    image_urls: list[str],
    source_url: str
) -> None:
    """
    Print formatted output for Dry Run testing.
    """
    separator = "=" * 50
    sub_separator = "-" * 30

    print(f"\n{separator}")
    print(f"📢 [DRY RUN] 게시물 타입: {data.get('type', 'unknown').upper()}")
    print(separator)

    # Main post
    print(f"\n[1] 메인 포스트")
    
    # Single Post + Multiple Images = Carousel Logic
    if data.get("type", "single") == "single" and len(image_urls) > 1:
        print(f"    🎠 [Carousel Mode] 총 {len(image_urls)}장의 이미지 포함")
        for i, url in enumerate(image_urls):
             print(f"    - 이미지[{i}]: {url[:60]}...")
    elif len(image_urls) > 0:
        print(f"    🖼️ 이미지[0]: {image_urls[0][:60]}...")
    else:
        print("    🖼️ 이미지: 없음")
    print(sub_separator)
    print(data.get("main_post", ""))

    # Replies (for multi-thread)
    if data.get("type") == "multi":
        replies = data.get("replies", [])
        for i, reply in enumerate(replies):
            print(f"\n[{i + 2}] 대댓글")
            
            # Check for Image i+1
            if len(image_urls) > i + 1:
                print(f"    🖼️ 이미지[{i+1}]: {image_urls[i+1][:60]}...")
            
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

THREADS_API_BASE = "https://graph.threads.net/v1.0"


def _create_container(
    user_id: str,
    access_token: str,
    text: str = "",
    image_url: Optional[str] = None,
    reply_to_id: Optional[str] = None,
    # Carousel specific args
    is_carousel_item: bool = False,
    children: Optional[list[str]] = None 
) -> Optional[str]:
    """
    Create a Threads media container. Supports Text, Image, and Carousel.
    """
    url = f"{THREADS_API_BASE}/{user_id}/threads"
    params = {
        "access_token": access_token,
    }

    if is_carousel_item:
        params["media_type"] = "IMAGE"
        params["image_url"] = image_url
        params["is_carousel_item"] = "true"
        # Carousel items don't have text or reply_to_id directly usually, 
        # but Threads API might allow text on the parent carousel container.
    elif children:
        params["media_type"] = "CAROUSEL"
        params["children"] = ",".join(children)
        params["text"] = text
        if reply_to_id:
            params["reply_to_id"] = reply_to_id
    else:
        # Standard Single Post (Image or Text)
        params["media_type"] = "IMAGE" if image_url else "TEXT"
        params["text"] = text
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
    image_urls: list[str],
    source_url: str,
    access_token: str
) -> bool:
    """
    Post content to Threads using the Graph API.
    Distributes images across the Main Post and Replies.
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
    
    container_id = None
    
    # Check if Single Post AND Multiple Images -> Use Carousel
    if data.get("type", "single") == "single" and len(image_urls) > 1:
        print(f"   🎠 단일 포스트 + 다중 이미지({len(image_urls)}장) -> 캐러셀 생성")
        
        # 2-1. Create Item Containers
        item_ids = []
        for img_url in image_urls:
            # Create Carousel Item
            item_id = _create_container(user_id, access_token, is_carousel_item=True, image_url=img_url)
            if item_id:
                item_ids.append(item_id)
            else:
                print(f"   ⚠️ 캐러셀 아이템 생성 실패: {img_url}")
        
        if len(item_ids) > 0:
            # 2-2. Create Carousel Container
            container_id = _create_container(user_id, access_token, text=main_text, children=item_ids)
    
    else:
        # Standard Single Image or Text
        main_image = image_urls[0] if len(image_urls) > 0 else None
        container_id = _create_container(user_id, access_token, text=main_text, image_url=main_image)
    
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
            # Assign Image i+1 to Reply i
            reply_image = image_urls[i+1] if len(image_urls) > i+1 else None
            
            print(f"   ↳ 대댓글 {i+1} 작성 중... (이미지: {'있음' if reply_image else '없음'})")
            cont_id = _create_container(
                user_id, 
                access_token, 
                reply_text, 
                image_url=reply_image, 
                reply_to_id=last_post_id
            )
            
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
