"""
Archiver module for Thread-Auto.

Handles saving news in the specific 'Newsletter Format' requested by the user.
"""

import os
import glob
from datetime import datetime
from typing import Dict, Any, Optional, Set, List


def get_archive_dir() -> str:
    """Get archive directory path."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "archive")


def get_archive_month_dir(date: Optional[datetime] = None) -> str:
    """Get year/month archive directory path."""
    if date is None:
        date = datetime.now()

    return os.path.join(
        get_archive_dir(),
        date.strftime("%Y"),
        date.strftime("%m월"),
    )


def get_archive_path(date: Optional[datetime] = None) -> str:
    """Get daily archive file path."""
    if date is None:
        date = datetime.now()

    filename = date.strftime("%Y-%m-%d.md")
    archive_dir = get_archive_month_dir(date)
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir, exist_ok=True)

    return os.path.join(archive_dir, filename)


def list_archive_files() -> List[str]:
    """List all archive markdown files, including year/month subdirectories."""
    archive_dir = get_archive_dir()
    if not os.path.exists(archive_dir):
        return []

    files = glob.glob(os.path.join(archive_dir, "**", "*.md"), recursive=True)
    files.extend(glob.glob(os.path.join(archive_dir, "*.md")))
    return sorted(set(files), key=_archive_sort_key, reverse=True)


def _archive_sort_key(filepath: str) -> tuple:
    """Sort archives by date in filename first, then modification time."""
    basename = os.path.basename(filepath)
    try:
        archive_date = datetime.strptime(basename[:10], "%Y-%m-%d")
        return (archive_date, os.path.getmtime(filepath))
    except (ValueError, OSError):
        try:
            return (datetime.min, os.path.getmtime(filepath))
        except OSError:
            return (datetime.min, 0)


def extract_source_url(line: str) -> Optional[str]:
    """Extract a source URL from legacy and current archive lines."""
    stripped = line.strip()
    prefixes = (
        "**출처:**",
        "출처:",
        "출처 :",
        "전체링크 :",
        "전체링크:",
    )

    for prefix in prefixes:
        if stripped.startswith(prefix):
            url = stripped[len(prefix):].strip()
            return url or None

    return None


def get_archived_urls(days: int = 7) -> Set[str]:
    """
    Get all URLs from recent archive files to prevent duplicates.

    Args:
        days: Number of recent days to check (default: 7)

    Returns:
        Set of URLs already archived
    """
    archive_dir = get_archive_dir()
    if not os.path.exists(archive_dir):
        return set()

    archived_urls = set()
    archive_files = list_archive_files()
    recent_files = archive_files[:days]

    for filepath in recent_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    url = extract_source_url(line)
                    if url:
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
    source_name: str = "Unknown",
    original_summary: Optional[str] = None,
    article_content_used: bool = False
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
    archive_date = datetime.now()
    filepath = get_archive_path(archive_date)

    # Prepare content block
    lines = []

    # Header for new file
    if not os.path.exists(filepath):
        lines.append(f"# Daily AI Tech News ({archive_date.strftime('%Y-%m-%d')})\n\n")
        lines.append("*Collected from configured AI lab, infrastructure, cloud, and paper feeds*\n\n")
        lines.append("---\n\n")

    # Company name mapping for readability
    company_names = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "deepmind": "DeepMind",
        "google_research": "Google Research",
        "huggingface": "Hugging Face",
        "meta_research": "Meta AI",
        "nvidia_technical": "NVIDIA",
        "nvidia_developer_ai": "NVIDIA",
        "nvidia_korea_blog": "NVIDIA Korea",
        "amd_rocm": "AMD ROCm",
        "microsoft_research": "Microsoft Research",
        "azure_ai": "Azure AI",
        "aws_machine_learning": "AWS ML",
        "google_cloud_ai": "Google Cloud AI",
        "microsoft_ai": "Microsoft AI",
        "perplexity": "Perplexity",
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

    if data.get("analysis_status"):
        lines.append(f"**분석상태:** {data['analysis_status']}\n\n")

    if data.get("analysis_error"):
        lines.append(f"**분석오류:** {data['analysis_error']}\n\n")

    if "importance_original" in data:
        reason = data.get("importance_adjusted_reason", "rule_based_calibration")
        lines.append(
            f"**중요도보정:** {data['importance_original']}점 → {importance}점 ({reason})\n\n"
        )

    # Summary
    summary = data.get('summary', '요약 없음')
    lines.append(f"**요약:**  \n{summary}\n\n")

    # Easy explanation
    explainer = data.get('easy_explainer', '설명 없음')
    lines.append(f"**쉬운설명:**  \n{explainer}\n\n")

    # Source URL
    lines.append(f"**출처:** {source_url}\n\n")

    # Source metadata for debugging curation quality
    if original_title:
        lines.append(f"**원문제목:** {original_title}\n\n")
    lines.append(f"**본문분석:** {'사용' if article_content_used else '미사용'}\n\n")
    if original_summary:
        lines.append(f"**RSS요약:**  \n{original_summary}\n\n")

    # Image
    if image_url:
        lines.append(f"![Article Image]({image_url})\n\n")
        
    # Append to file
    with open(filepath, "a", encoding="utf-8") as f:
        f.writelines(lines)
        
    print(f"✅ 아카이브 저장 완료: {filepath}")
    return filepath
