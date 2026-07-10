"""
Source registry tests.
"""

from source_registry import (
    SOURCE_REGISTRY,
    calculate_collection_score,
    get_disabled_sources,
    get_enabled_sources,
    get_source_weight,
)


def test_enabled_sources_cover_priority_collection_groups():
    """활성 소스 조합은 90점 이상 수집 커버리지를 가져야 함."""

    enabled_sources = get_enabled_sources()

    assert calculate_collection_score() >= 90
    assert "nvidia_technical" in enabled_sources
    assert "nvidia_developer_ai" in enabled_sources
    assert "amd_rocm" in enabled_sources
    assert "microsoft_research" in enabled_sources
    assert "azure_ai" in enabled_sources
    assert "aws_machine_learning" in enabled_sources
    assert "google_cloud_ai" in enabled_sources


def test_registry_records_unstable_requested_sources_without_enabling_them():
    """자동 접근이 불안정한 요청 소스는 비활성 사유를 남겨야 함."""

    disabled_sources = get_disabled_sources()

    assert "microsoft_ai" in SOURCE_REGISTRY
    assert "perplexity" in SOURCE_REGISTRY
    assert "microsoft_ai" in disabled_sources
    assert "perplexity" in disabled_sources
    assert disabled_sources["microsoft_ai"]["disabled_reason"]
    assert disabled_sources["perplexity"]["disabled_reason"]


def test_registry_does_not_add_open_source_release_feeds():
    """이번 확장에서는 GitHub 릴리즈 같은 오픈소스 소스를 추가하지 않음."""

    for source_name, config in SOURCE_REGISTRY.items():
        text = " ".join([
            source_name,
            str(config.get("url", "")),
            str(config.get("group", "")),
        ]).lower()
        assert "github.com" not in text
        assert "release" not in text


def test_priority_sources_have_higher_editorial_weight():
    """인프라/클라우드 핵심 소스는 기본보다 높은 가중치를 가져야 함."""

    assert get_source_weight("nvidia_technical") > 1.0
    assert get_source_weight("aws_machine_learning") > 1.0
    assert get_source_weight("microsoft_research") > 1.0
