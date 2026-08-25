"""Tests for optional Threads media asset download."""

from threads_assets import download_media_assets, media_urls_for_post


class FakeResponse:
    def __init__(self, content=b"data", content_type="image/jpeg"):
        self.content = content
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self):
        self.urls = []

    def get(self, url, timeout):
        self.urls.append(url)
        return FakeResponse()


def test_media_urls_for_post_includes_post_and_child_media():
    post = {
        "media_url": "https://example.com/image.jpg",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "children": [
            {"media_url": "https://example.com/child.png"},
        ],
    }

    urls = media_urls_for_post(post)

    assert [item["url"] for item in urls] == [
        "https://example.com/image.jpg",
        "https://example.com/thumb.jpg",
        "https://example.com/child.png",
    ]


def test_download_media_assets_writes_files(tmp_path):
    session = FakeSession()
    post = {
        "id": "post-1",
        "date": "2026-08-07",
        "media_url": "https://example.com/image.jpg",
    }

    manifest = download_media_assets([post], media_dir=tmp_path / "media", session=session)

    assert len(manifest) == 1
    assert session.urls == ["https://example.com/image.jpg"]
    assert (tmp_path / "media" / "2026-08" / "post-1" / "media_url.jpg").exists()
