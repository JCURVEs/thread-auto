"""
Image Extractor module for Thread-Auto.

This module handles extracting og:image meta tags from article URLs
for attaching images to Threads posts.
"""

from typing import Optional
import requests
from bs4 import BeautifulSoup


# Default request headers to mimic browser
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Request timeout in seconds
REQUEST_TIMEOUT = 10


def get_article_image(url: str) -> Optional[str]:
    """
    Extract the og:image meta tag from an article URL.

    Args:
        url: The article URL to extract the image from.

    Returns:
        The image URL if found, None otherwise.

    Example:
        >>> image_url = get_article_image("https://techcrunch.com/article")
        >>> if image_url:
        ...     print(f"Found image: {image_url}")
    """
    try:
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Try og:image first (most common)
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]

        # Fallback to twitter:image
        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            return twitter_image["content"]

        # Fallback to first article image
        article_img = soup.find("article")
        if article_img:
            img = article_img.find("img")
            if img and img.get("src"):
                return img["src"]

        return None

    except requests.RequestException as e:
        print(f"⚠️ 이미지 추출 실패 (요청 오류): {e}")
        return None
    except Exception as e:
        print(f"⚠️ 이미지 추출 실패: {e}")
        return None


def download_image(url: str, save_path: str) -> bool:
    """
    Download an image from URL and save to local path.

    Args:
        url: The image URL to download.
        save_path: Local file path to save the image.

    Returns:
        True if download successful, False otherwise.

    Example:
        >>> success = download_image(
        ...     "https://example.com/image.jpg",
        ...     "/tmp/image.jpg"
        ... )
    """
    try:
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT,
            stream=True
        )
        response.raise_for_status()

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True

    except Exception as e:
        print(f"⚠️ 이미지 다운로드 실패: {e}")
        return False


def validate_image_url(url: str) -> bool:
    """
    Validate that a URL points to an actual image.

    Args:
        url: The URL to validate.

    Returns:
        True if URL is a valid image, False otherwise.

    Example:
        >>> is_valid = validate_image_url("https://example.com/image.jpg")
    """
    try:
        response = requests.head(
            url,
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT
        )
        content_type = response.headers.get("Content-Type", "")
        return content_type.startswith("image/")
    except Exception:
        return False
