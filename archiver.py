"""
Archiver module for Thread-Auto.

Handles saving news in the specific 'Newsletter Format' requested by the user.
"""

import os
import glob
from datetime import datetime
from typing import Dict, Any, Optional, Set

def get_archive_path(date: Optional[datetime] = None) -> str:
    """Get daily archive file path."""
    if date is None:
        date = datetime.now()

    filename = date.strftime("%Y-%m-%d.md")
    archive_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "archive")
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)

    return os.path.join(archive_dir, filename)


def get_archived_urls(days: int = 7) -> Set[str]:
    """
    Get all URLs from recent archive files to prevent duplicates.

    Args:
        days: Number of recent days to check (default: 7)

    Returns:
        Set of URLs already archived
    """
    archive_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "archive")
    if not os.path.exists(archive_dir):
        return set()

    archived_urls = set()
    archive_files = glob.glob(os.path.join(archive_dir, "*.md"))

    # Sort by modification time, get recent files
    archive_files.sort(key=os.path.getmtime, reverse=True)
    recent_files = archive_files[:days]

    for filepath in recent_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("전체링크 :"):
                        url = line.replace("전체링크 :", "").strip()
                        archived_urls.add(url)
        except Exception as e:
            print(f"⚠️ 아카이브 파일 읽기 실패 ({filepath}): {e}")

    return archived_urls


def is_duplicate(url: str) -> bool:
    """
    Check if URL is already archived.

    Args:
        url: URL to check

    Returns:
        True if URL is already archived, False otherwise
    """
    archived_urls = get_archived_urls()
    return url in archived_urls

def save_to_archive(
    data: Dict[str, Any],
    image_url: Optional[str],
    source_url: str,
    original_title: str, # Not used in output but kept for interface compatibility
    provider: str,
    model: str
) -> str:
    """
    Save content in the User-Defined Newsletter Format.
    
    Format:
    ---
    제목: ...
    요약: ...
    쉬운설명: ...
    관련분야: ...
    중요도: ...
    전체링크 : ...

    Image
    ---
    """
    filepath = get_archive_path()
    
    # Prepare content block
    lines = []
    
    # Header for new file
    if not os.path.exists(filepath):
        lines.append(f"# Daily Tech News Archive ({datetime.now().strftime('%Y-%m-%d')})\n\n")
    
    # Separator
    lines.append("---\n\n")
    
    # Content Fields
    lines.append(f"제목: {data.get('title', '제목 없음')}\n")
    lines.append(f"요약: {data.get('summary', '요약 없음')}\n")
    lines.append(f"쉬운설명: {data.get('easy_explainer', '설명 없음')}\n")
    lines.append(f"관련분야: {data.get('category', '기타')}\n")
    lines.append(f"중요도: {data.get('importance', 5)}점\n")
    lines.append(f"전체링크 : {source_url}\n\n")
    
    # Image
    if image_url:
        lines.append(f"![Image]({image_url})\n\n")
        
    # Append to file
    with open(filepath, "a", encoding="utf-8") as f:
        f.writelines(lines)
        
    print(f"✅ 아카이브 저장 완료: {filepath}")
    return filepath
