"""
Source registry for Thread-Auto.

Keeps collection URLs, fetch modes, editorial weights, and coverage scoring in
one place so the pipeline can grow without turning rss_collector.py into a
hard-coded source list.
"""

from typing import Any, Dict, List


SOURCE_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Frontier AI labs
    "openai": {
        "url": "https://openai.com/news/rss.xml",
        "name": "OpenAI",
        "group": "frontier_lab",
        "fetch_mode": "rss",
        "weight": 1.15,
        "enabled": True,
    },
    "anthropic": {
        "url": "https://www.anthropic.com/news",
        "name": "Anthropic",
        "group": "frontier_lab",
        "fetch_mode": "playwright",
        "weight": 1.15,
        "enabled": True,
    },
    "deepmind": {
        "url": "https://deepmind.google/blog/rss.xml",
        "name": "Google DeepMind",
        "group": "frontier_lab",
        "fetch_mode": "rss",
        "weight": 1.1,
        "enabled": True,
    },
    "google_research": {
        "url": "https://research.google/blog/rss",
        "name": "Google Research",
        "group": "research_lab",
        "fetch_mode": "rss",
        "weight": 1.0,
        "enabled": True,
    },
    "huggingface": {
        "url": "https://huggingface.co/blog/feed.xml",
        "name": "Hugging Face",
        "group": "developer_ecosystem",
        "fetch_mode": "rss",
        "weight": 1.05,
        "enabled": True,
    },
    "meta_research": {
        "url": "https://research.facebook.com/feed",
        "name": "Meta AI Research",
        "group": "research_lab",
        "fetch_mode": "rss",
        "weight": 1.0,
        "enabled": True,
    },

    # Infrastructure / chips
    "nvidia_technical": {
        "url": "https://developer.nvidia.com/blog/feed/",
        "name": "NVIDIA Technical Blog",
        "group": "infra_chip",
        "fetch_mode": "rss",
        "weight": 1.25,
        "enabled": True,
    },
    "nvidia_developer_ai": {
        "url": "https://developer.nvidia.com/blog/category/generative-ai/feed/",
        "name": "NVIDIA Developer Blog - Generative AI",
        "group": "infra_chip",
        "fetch_mode": "rss",
        "weight": 1.25,
        "enabled": True,
    },
    "nvidia_korea_blog": {
        "url": "https://blogs.nvidia.co.kr/feed/",
        "name": "NVIDIA Korea Blog",
        "group": "infra_chip",
        "fetch_mode": "rss",
        "weight": 1.15,
        "enabled": True,
    },
    "amd_rocm": {
        "url": "https://rocm.blogs.amd.com/",
        "name": "AMD ROCm Blog",
        "group": "infra_chip",
        "fetch_mode": "html_listing",
        "weight": 1.2,
        "enabled": False,
        "disabled_reason": "Removed from the active editorial collection scope.",
        "url_pattern": "/README.html",
    },

    # Cloud / platform
    "microsoft_research": {
        "url": "https://www.microsoft.com/en-us/research/feed/",
        "name": "Microsoft Research",
        "group": "cloud_platform",
        "fetch_mode": "rss",
        "weight": 1.1,
        "enabled": True,
    },
    "azure_ai": {
        "url": "https://azure.microsoft.com/en-us/blog/feed/",
        "name": "Azure Blog",
        "group": "cloud_platform",
        "fetch_mode": "rss",
        "weight": 1.05,
        "enabled": False,
        "disabled_reason": "Removed from the active editorial collection scope.",
        "topic_keywords": ("ai", "machine learning", "azure ai", "copilot", "agent"),
    },
    "aws_machine_learning": {
        "url": "https://aws.amazon.com/blogs/machine-learning/feed/",
        "name": "AWS Machine Learning Blog",
        "group": "cloud_platform",
        "fetch_mode": "rss",
        "weight": 1.1,
        "enabled": False,
        "disabled_reason": "Removed from the active editorial collection scope.",
    },
    "google_cloud_ai": {
        "url": "https://cloud.google.com/blog/products/ai-machine-learning",
        "name": "Google Cloud AI Blog",
        "group": "cloud_platform",
        "fetch_mode": "html_listing",
        "weight": 1.1,
        "enabled": True,
        "url_pattern": "/blog/products/ai-machine-learning/",
    },
    "microsoft_ai": {
        "url": "https://blogs.microsoft.com/ai/feed/",
        "name": "Microsoft AI Blog",
        "group": "cloud_platform",
        "fetch_mode": "rss",
        "weight": 1.0,
        "enabled": False,
        "disabled_reason": "Official feed currently returns no entries in automated checks.",
    },
    "perplexity": {
        "url": "https://www.perplexity.ai/hub/blog",
        "name": "Perplexity Blog",
        "group": "cloud_platform",
        "fetch_mode": "html_listing",
        "weight": 1.0,
        "enabled": False,
        "disabled_reason": "Official page currently blocks automated collection.",
    },

    # Research / paper feeds
    "arxiv_ai": {
        "url": "https://rss.arxiv.org/rss/cs.AI",
        "name": "arXiv AI",
        "group": "paper_research",
        "fetch_mode": "rss",
        "weight": 0.95,
        "enabled": True,
    },
    "arxiv_lg": {
        "url": "https://rss.arxiv.org/rss/cs.LG",
        "name": "arXiv ML",
        "group": "paper_research",
        "fetch_mode": "rss",
        "weight": 0.95,
        "enabled": True,
    },
    "arxiv_cv": {
        "url": "https://rss.arxiv.org/rss/cs.CV",
        "name": "arXiv Vision",
        "group": "paper_research",
        "fetch_mode": "rss",
        "weight": 0.95,
        "enabled": True,
    },
    "arxiv_cl": {
        "url": "https://rss.arxiv.org/rss/cs.CL",
        "name": "arXiv NLP",
        "group": "paper_research",
        "fetch_mode": "rss",
        "weight": 0.95,
        "enabled": True,
    },
}

GROUP_COVERAGE_POINTS = {
    "frontier_lab": 20,
    "infra_chip": 20,
    "cloud_platform": 20,
    "research_lab": 15,
    "developer_ecosystem": 10,
    "paper_research": 15,
}


def get_enabled_sources() -> Dict[str, str]:
    """Return enabled source names mapped to collection URLs."""
    return {
        source_name: config["url"]
        for source_name, config in SOURCE_REGISTRY.items()
        if config.get("enabled", True)
    }


def get_source_config(source_name: str) -> Dict[str, Any]:
    """Return source configuration with safe defaults."""
    return SOURCE_REGISTRY.get(
        source_name,
        {
            "url": "",
            "name": source_name,
            "group": "manual",
            "fetch_mode": "rss",
            "weight": 1.0,
            "enabled": True,
        },
    )


def get_source_weight(source_name: str) -> float:
    """Return editorial source weight."""
    return float(get_source_config(source_name).get("weight", 1.0))


def get_source_fetch_mode(source_name: str) -> str:
    """Return source fetch mode."""
    return str(get_source_config(source_name).get("fetch_mode", "rss"))


def get_disabled_sources() -> Dict[str, Dict[str, Any]]:
    """Return registered but disabled sources for reporting."""
    return {
        source_name: config
        for source_name, config in SOURCE_REGISTRY.items()
        if not config.get("enabled", True)
    }


def calculate_collection_score() -> int:
    """Estimate source coverage score out of 100 based on enabled groups."""
    enabled_groups = {
        config["group"]
        for config in SOURCE_REGISTRY.values()
        if config.get("enabled", True)
    }
    return min(
        100,
        sum(
            points
            for group, points in GROUP_COVERAGE_POINTS.items()
            if group in enabled_groups
        ),
    )


def get_high_confidence_online_check_sources() -> List[str]:
    """Return sources known to expose stable RSS feeds for online smoke tests."""
    return [
        source_name
        for source_name, config in SOURCE_REGISTRY.items()
        if config.get("enabled", True)
        and config.get("fetch_mode") == "rss"
        and source_name not in {"azure_ai"}
    ]
