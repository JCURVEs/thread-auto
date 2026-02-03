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
    model: str,
    source_name: str = "Unknown"
) -> str:
    """
    Save content in readable newsletter format with company name.

    Format:
    ## [Company] Title
    **분야:** Category | **중요도:** X점
    **요약:** Summary
    **쉬운설명:** Easy explanation
    **출처:** URL
    ![Image](url)
    ---
    """
    filepath = get_archive_path()

    # Prepare content block
    lines = []

    # Header for new file
    if not os.path.exists(filepath):
        lines.append(f"# Daily AI Tech News ({datetime.now().strftime('%Y-%m-%d')})\n\n")
        lines.append("*Collected from OpenAI, Anthropic, DeepMind, Google Research, Hugging Face, Meta AI, arXiv*\n\n")
        lines.append("---\n\n")

    # Company name mapping for readability
    company_names = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "deepmind": "DeepMind",
        "google_research": "Google Research",
        "huggingface": "Hugging Face",
        "meta_research": "Meta AI",
        "arxiv_ai": "arXiv AI",
        "arxiv_lg": "arXiv ML",
        "arxiv_cv": "arXiv Vision",
        "arxiv_cl": "arXiv NLP"
    }

    company = company_names.get(source_name.lower(), source_name.upper())

    # Title with company name
    title = data.get('title', '제목 없음')
    lines.append(f"## [{company}] {title}\n\n")

    # Metadata line
    category = data.get('category', '기타')
    importance = data.get('importance', 5)
    lines.append(f"**분야:** {category} | **중요도:** {importance}점\n\n")

    # Summary
    summary = data.get('summary', '요약 없음')
    lines.append(f"**요약:**  \n{summary}\n\n")

    # Easy explanation
    explainer = data.get('easy_explainer', '설명 없음')
    lines.append(f"**쉬운설명:**  \n{explainer}\n\n")

    # Source URL
    lines.append(f"**출처:** {source_url}\n\n")

    # Image
    if image_url:
        lines.append(f"![Article Image]({image_url})\n\n")
        
    # Append to file
    with open(filepath, "a", encoding="utf-8") as f:
        f.writelines(lines)
        
    print(f"✅ 아카이브 저장 완료: {filepath}")
    return filepath
