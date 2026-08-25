"""
Threads history client.

Fetches posts from the authenticated user's Threads account so past writing can
become a local style asset. Access tokens must stay in local environment
variables and should never be committed.
"""

from typing import Any, Dict, Iterator, Optional

import requests


API_BASE_URL = "https://graph.threads.net"
DEFAULT_THREAD_FIELDS = (
    "id,media_product_type,media_type,media_url,gif_url,permalink,owner,username,"
    "text,timestamp,shortcode,thumbnail_url,children,is_quote_post,quoted_post,"
    "reposted_post,alt_text,link_attachment_url,has_replies,is_reply,"
    "is_reply_owned_by_me,root_post,replied_to,topic_tag,location_id,"
    "poll_attachment{option_a,option_b,option_c,option_d,option_a_votes_percentage,"
    "option_b_votes_percentage,option_c_votes_percentage,option_d_votes_percentage,"
    "expiration_timestamp}"
)


class ThreadsApiError(RuntimeError):
    """Raised when the Threads API returns an error response."""


def fetch_threads_page(
    access_token: str,
    fields: str = DEFAULT_THREAD_FIELDS,
    limit: int = 50,
    since: Optional[str] = None,
    until: Optional[str] = None,
    after: Optional[str] = None,
    base_url: str = API_BASE_URL,
    timeout: int = 30,
    session: Any = None,
) -> Dict[str, Any]:
    """Fetch one page of the authenticated user's Threads posts."""
    if not access_token:
        raise ValueError("THREADS_ACCESS_TOKEN is required")

    http = session or requests
    params: Dict[str, Any] = {
        "fields": fields,
        "limit": limit,
    }
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    if after:
        params["after"] = after

    response = http.get(
        f"{base_url.rstrip('/')}/me/threads",
        params=params,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=timeout,
    )

    if response.status_code >= 400:
        raise ThreadsApiError(f"Threads API HTTP {response.status_code}: {response.text}")

    payload = response.json()
    if "error" in payload:
        raise ThreadsApiError(f"Threads API error: {payload['error']}")

    return payload


def iter_user_threads(
    access_token: str,
    fields: str = DEFAULT_THREAD_FIELDS,
    limit: int = 50,
    since: Optional[str] = None,
    until: Optional[str] = None,
    max_pages: Optional[int] = None,
    base_url: str = API_BASE_URL,
    session: Any = None,
) -> Iterator[Dict[str, Any]]:
    """Yield all available posts for the authenticated Threads user."""
    after = None
    seen_cursors = set()
    page_count = 0

    while True:
        if max_pages is not None and page_count >= max_pages:
            break

        payload = fetch_threads_page(
            access_token=access_token,
            fields=fields,
            limit=limit,
            since=since,
            until=until,
            after=after,
            base_url=base_url,
            session=session,
        )
        page_count += 1

        for post in payload.get("data", []):
            yield post

        cursors = payload.get("paging", {}).get("cursors", {})
        next_after = cursors.get("after")
        if not next_after or next_after in seen_cursors:
            break

        seen_cursors.add(next_after)
        after = next_after


def fetch_conversation_page(
    thread_id: str,
    access_token: str,
    fields: str = DEFAULT_THREAD_FIELDS,
    reverse: bool = False,
    after: Optional[str] = None,
    base_url: str = API_BASE_URL,
    timeout: int = 30,
    session: Any = None,
) -> Dict[str, Any]:
    """Fetch one page of a Threads conversation tree."""
    if not thread_id:
        raise ValueError("thread_id is required")
    if not access_token:
        raise ValueError("THREADS_ACCESS_TOKEN is required")

    http = session or requests
    params: Dict[str, Any] = {
        "fields": fields,
        "reverse": str(reverse).lower(),
    }
    if after:
        params["after"] = after

    response = http.get(
        f"{base_url.rstrip('/')}/{thread_id}/conversation",
        params=params,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=timeout,
    )

    if response.status_code >= 400:
        raise ThreadsApiError(f"Threads API HTTP {response.status_code}: {response.text}")

    payload = response.json()
    if "error" in payload:
        raise ThreadsApiError(f"Threads API error: {payload['error']}")

    return payload


def iter_thread_conversation(
    thread_id: str,
    access_token: str,
    fields: str = DEFAULT_THREAD_FIELDS,
    reverse: bool = False,
    max_pages: Optional[int] = None,
    base_url: str = API_BASE_URL,
    session: Any = None,
) -> Iterator[Dict[str, Any]]:
    """Yield posts in a flattened conversation for one root Threads post."""
    after = None
    seen_cursors = set()
    page_count = 0

    while True:
        if max_pages is not None and page_count >= max_pages:
            break

        payload = fetch_conversation_page(
            thread_id=thread_id,
            access_token=access_token,
            fields=fields,
            reverse=reverse,
            after=after,
            base_url=base_url,
            session=session,
        )
        page_count += 1

        for post in payload.get("data", []):
            yield post

        cursors = payload.get("paging", {}).get("cursors", {})
        next_after = cursors.get("after")
        if not next_after or next_after in seen_cursors:
            break

        seen_cursors.add(next_after)
        after = next_after
