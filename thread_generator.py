#!/usr/bin/env python3
"""
Thread Generator - Main orchestration script for thread creation
Routes inputs to appropriate agent teams based on content type
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import hashlib
import re


THREAD_MIN_IMPORTANCE = 8
MAX_THREAD_CHARS = 500
HOOK_CLOSING_LINE = "핵심내용 정리했습니다🧵"
GENERIC_STORYLINE_TITLES = {
    "기존 상식 뒤집기",
    "근본적 문제",
    "핵심 접근법",
    "구체적 구현",
    "기술 깊이",
    "결과와 성과",
    "미래 전망",
}
THREAD_FORBIDDEN_EXPRESSIONS = (
    "혁신적인",
    "획기적인",
    "정말",
    "매우",
    "엄청",
    "세계 최초",
    "완전히",
    "무조건",
    "압도적",
)
THREAD_OVERCLAIM_EXPRESSIONS = (
    "판도를 바꿉니다",
    "게임체인저",
    "완전히 대체",
    "모든 산업",
    "역사를 바꿉니다",
)
WEAK_GENERIC_LINES = (
    "방향은 분명합니다.",
    "시장에 영향을 줄 수 있습니다.",
    "앞으로가 중요합니다.",
    "많은 변화가 예상됩니다.",
)


class ThreadGenerator:
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.agents_dir = self.project_root / ".claude" / "agents"
        self.threads_dir = self.project_root / "threads"
        self.archive_dir = self.project_root / "archive"

    def route_input(self, input_text: str, content_type: str = None) -> str:
        """
        Route input to appropriate agent team
        Returns the content type (news/paper/company)
        """
        if content_type:
            return content_type

        # Auto-detect content type
        input_lower = input_text.lower()

        # Check for paper indicators
        if "arxiv.org" in input_lower or "paper" in input_lower or "논문" in input_lower:
            return "paper"

        # Check for news indicators
        if "news" in input_lower or "뉴스" in input_lower or "archive" in input_lower:
            return "news"

        # Check for company indicators
        # Simple heuristic: if it's a short phrase without spaces or a known company name
        company_keywords = ["openai", "anthropic", "google", "meta", "microsoft", "nvidia",
                          "tesla", "apple", "분석", "기업"]
        if any(keyword in input_lower for keyword in company_keywords):
            return "company"

        # Default to news if unclear
        return "news"

    def generate_news_thread(self, date_input: str = "latest"):
        """Generate thread from daily news archive"""
        print(f"[ROUTE] 데일리뉴스 팀")
        print(f"[INPUT] {date_input}")

        archive_file = self.find_archive_file(date_input)
        if not archive_file:
            print(f"[ERROR] Archive file not found: {date_input}")
            return 1

        print(f"[SOURCE] {archive_file}")

        items = self.parse_archive(archive_file)
        if not items:
            print("[ERROR] 스레드 후보를 파싱하지 못했습니다.")
            return 1

        candidate = self.select_news_candidate(items)
        if not candidate:
            print(f"[ERROR] 중요도 {THREAD_MIN_IMPORTANCE}점 이상 기술 뉴스가 없습니다.")
            return 1

        output_dir = self.write_news_thread(candidate, archive_file)

        print()
        print("=" * 60)
        print("[OK] 스레드 초안 생성 완료")
        print(f"[OUTPUT] {output_dir}")
        print(f"[THREADS] {candidate['thread_count']}개")
        print("[NEXT] reviewer.md 기준으로 문장/팩트 최종 검수")
        print("=" * 60)

        return 0

    def find_archive_file(self, date_input: str = "latest") -> Optional[Path]:
        """Find an archive file in year/month archive folders."""
        archive_files = self.list_archive_files()
        if date_input == "latest":
            return archive_files[0] if archive_files else None

        target_name = f"{date_input}.md" if not date_input.endswith(".md") else date_input
        for archive_file in archive_files:
            if archive_file.name == target_name:
                return archive_file
        return None

    def list_archive_files(self) -> List[Path]:
        """List archive markdown files from both nested and legacy flat layouts."""
        if not self.archive_dir.exists():
            return []

        files = {path for path in self.archive_dir.rglob("*.md") if path.is_file()}
        return sorted(files, key=self._archive_file_sort_key, reverse=True)

    def _archive_file_sort_key(self, archive_file: Path) -> tuple:
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})", archive_file.stem)
        if match:
            return ("".join(match.groups()), archive_file.stat().st_mtime)
        return ("00000000", archive_file.stat().st_mtime)

    def parse_archive(self, archive_file: Path) -> List[Dict[str, Any]]:
        """Parse an archive markdown file into structured news items."""
        lines = archive_file.read_text(encoding="utf-8").splitlines()
        items = []
        current = []

        for line in lines:
            if line.startswith("## "):
                if current:
                    item = self._parse_archive_block(current)
                    if item:
                        items.append(item)
                current = [line]
            elif current:
                current.append(line)

        if current:
            item = self._parse_archive_block(current)
            if item:
                items.append(item)

        return items

    def _parse_archive_block(self, lines: List[str]) -> Optional[Dict[str, Any]]:
        header = lines[0].strip()
        match = re.match(r"^## \[(?P<company>[^\]]+)\]\s+(?P<title>.+)$", header)
        if not match:
            return None

        metadata = self._parse_category_importance(lines)
        if not metadata:
            return None

        item = {
            "company": match.group("company").strip(),
            "title": match.group("title").strip(),
            "category": metadata["category"],
            "importance": metadata["importance"],
            "summary": self._extract_field(lines, "요약"),
            "easy_explainer": self._extract_field(lines, "쉬운설명"),
            "source_url": self._extract_field(lines, "출처"),
            "original_title": self._extract_field(lines, "원문제목"),
            "image_url": self._extract_image_url(lines),
        }
        return item

    def _parse_category_importance(self, lines: List[str]) -> Optional[Dict[str, Any]]:
        for line in lines:
            match = re.search(r"\*\*분야:\*\*\s*(.*?)\s*\|\s*\*\*중요도:\*\*\s*(\d+)점", line)
            if match:
                return {
                    "category": match.group(1).strip(),
                    "importance": int(match.group(2)),
                }
        return None

    def _extract_field(self, lines: List[str], field_name: str) -> str:
        prefix = f"**{field_name}:**"
        for index, line in enumerate(lines):
            if not line.startswith(prefix):
                continue

            inline_value = line[len(prefix):].strip()
            if inline_value:
                return inline_value

            values = []
            for next_line in lines[index + 1:]:
                stripped = next_line.strip()
                if not stripped and values:
                    break
                if stripped.startswith("**") or stripped.startswith("![") or stripped.startswith("## "):
                    break
                if stripped:
                    values.append(stripped)
            return " ".join(values).strip()

        return ""

    def _extract_image_url(self, lines: List[str]) -> str:
        for line in lines:
            match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", line)
            if match:
                return match.group(1).strip()
        return ""

    def select_news_candidate(self, items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Pick the strongest non-business item for a news thread."""
        candidates = [
            item for item in items
            if item["importance"] >= THREAD_MIN_IMPORTANCE
            and item["category"] != "비즈니스"
            and item.get("source_url")
        ]
        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (
                item["importance"],
                item["category"] in {"LLM 출시", "오픈소스 도구", "API/인프라"},
                item["company"] != "arXiv AI",
            ),
            reverse=True,
        )
        return candidates[0]

    def write_news_thread(self, item: Dict[str, Any], archive_file: Path) -> Path:
        """Write thread markdown files and metadata for a selected news item."""
        archive_date = self._archive_date(archive_file)
        output_dir = self.threads_dir / "news" / f"{archive_date}-{self._slug(item)}"
        output_dir.mkdir(parents=True, exist_ok=True)

        posts = self.build_news_posts(item)
        item["thread_count"] = len(posts)

        for index, post in enumerate(posts, 1):
            path = output_dir / f"thread-{index:02d}.md"
            path.write_text(post.strip() + "\n", encoding="utf-8")

        review = self.review_news_posts(item, posts)
        metadata = {
            "source": str(archive_file.relative_to(self.project_root)),
            "source_url": item.get("source_url", ""),
            "company": item["company"],
            "title": item["title"],
            "category": item["category"],
            "importance": item["importance"],
            "thread_count": len(posts),
            "image_url": item.get("image_url", ""),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "draft",
            "generator": "thread_generator.py",
            "review_status": review["status"],
            "review_blocking_count": len(review["blocking"]),
            "review_warning_count": len(review["warnings"]),
        }
        (output_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )

        review_report = self.build_review_report(metadata, review)
        (output_dir / "review-report.md").write_text(review_report, encoding="utf-8")

        return output_dir

    def review_news_posts(self, item: Dict[str, Any], posts: List[str]) -> Dict[str, Any]:
        """Run pre-publish checks on generated thread posts."""
        blocking = []
        warnings = []
        passed = []

        if len(posts) != 9:
            blocking.append(f"post_count:{len(posts)}")
        else:
            passed.append("post_count:9")

        if posts:
            if "\n" in posts[0].strip():
                blocking.append("title_not_single_line")
            else:
                passed.append("title_single_line")

        if len(posts) >= 2:
            hook_lines = posts[1].splitlines()
            if len(hook_lines) != 5:
                blocking.append(f"hook_line_count:{len(hook_lines)}")
            else:
                passed.append("hook_line_count:5")
            if not hook_lines or hook_lines[-1] != HOOK_CLOSING_LINE:
                blocking.append("hook_closing_missing")
            else:
                passed.append("hook_closing")

        for index, post in enumerate(posts[2:], 1):
            lines = post.splitlines()
            if not 7 <= len(lines) <= 9:
                blocking.append(f"slide_{index}_line_count:{len(lines)}")
            first_line = lines[0] if lines else ""
            prefix = f"{index}/ "
            if not first_line.startswith(prefix):
                blocking.append(f"slide_{index}_numbering")
                continue
            subtitle = first_line.removeprefix(prefix).strip()
            if subtitle in GENERIC_STORYLINE_TITLES:
                blocking.append(f"slide_{index}_generic_subtitle:{subtitle}")
            if len(subtitle) < 8:
                warnings.append(f"slide_{index}_thin_subtitle")

        for index, post in enumerate(posts, 1):
            if len(post.strip()) > MAX_THREAD_CHARS:
                blocking.append(f"thread_{index:02d}_too_long:{len(post.strip())}")

        full_text = "\n".join(posts)
        for expression in THREAD_FORBIDDEN_EXPRESSIONS:
            if expression in full_text:
                blocking.append(f"forbidden_expression:{expression}")
        for expression in THREAD_OVERCLAIM_EXPRESSIONS:
            if expression in full_text:
                blocking.append(f"overclaim:{expression}")

        unsupported_metrics = self._unsupported_metrics(full_text, item)
        for metric in unsupported_metrics:
            blocking.append(f"unsupported_metric:{metric}")

        for weak_line in WEAK_GENERIC_LINES:
            count = full_text.count(weak_line)
            if count >= 2:
                warnings.append(f"generic_line_repeated:{weak_line}")

        if item.get("source_url") and item["source_url"] in posts[-1]:
            passed.append("source_url_present")
        else:
            blocking.append("source_url_missing")

        if not blocking:
            passed.append("no_blocking_publish_issues")

        return {
            "status": "BLOCKED" if blocking else "READY_FOR_HUMAN_REVIEW",
            "blocking": blocking,
            "warnings": warnings,
            "passed": passed,
        }

    def build_review_report(self, metadata: Dict[str, Any], review: Dict[str, Any]) -> str:
        """Build a markdown review report for generated thread drafts."""
        lines = [
            "# 검수 리포트",
            "",
            "## 요약",
            f"- 상태: {review['status']}",
            f"- 스레드 수: {metadata['thread_count']}개",
            f"- 원본: {metadata['source']}",
            "",
            "## 차단 이슈",
        ]

        if review["blocking"]:
            lines.extend(f"- {issue}" for issue in review["blocking"])
        else:
            lines.append("- 없음")

        lines.extend(["", "## 주의 이슈"])
        if review["warnings"]:
            lines.extend(f"- {issue}" for issue in review["warnings"])
        else:
            lines.append("- 없음")

        lines.extend(["", "## 통과 체크"])
        lines.extend(f"- {check}" for check in review["passed"])

        lines.extend([
            "",
            "## 수동 확인",
            "- 원문 팩트와 숫자 재확인",
            "- @jokerburg.builder 실제 문체로 최종 다듬기",
            "- 게시 전 첫 줄/마지막 줄 모바일 가독성 확인",
        ])
        return "\n".join(lines) + "\n"

    def _unsupported_metrics(self, text: str, item: Dict[str, Any]) -> List[str]:
        """Return metric-like claims that are not present in source evidence."""
        metric_pattern = re.compile(
            r"\d+(?:\.\d+)?\s?(?:%|배|x|ms|tokens/s|tok/s)",
            re.IGNORECASE,
        )
        metrics = sorted(set(metric_pattern.findall(text)))
        if not metrics:
            return []

        evidence = " ".join([
            str(item.get("title", "")),
            str(item.get("original_title", "")),
            str(item.get("summary", "")),
            str(item.get("easy_explainer", "")),
            str(item.get("source_url", "")),
        ])
        normalized_evidence = re.sub(r"\s+", "", evidence).lower()

        unsupported = []
        for metric in metrics:
            normalized_metric = re.sub(r"\s+", "", metric).lower()
            if normalized_metric not in normalized_evidence:
                unsupported.append(metric)
        return unsupported

    def build_news_posts(self, item: Dict[str, Any]) -> List[str]:
        """Build a storyline-style thread draft."""
        title = item["title"]
        company = item["company"]
        category = item["category"]
        importance = item["importance"]
        summary = item.get("summary") or "핵심 내용은 원문 기준으로 다시 확인이 필요해요."
        easy = item.get("easy_explainer") or "쉽게 말하면, 기술 흐름을 체크할 재료예요."
        source_url = item.get("source_url", "")
        topic = self._topic_phrase(title, company)
        slide_titles = self._story_slide_titles(item)

        posts = [
            self._build_title_post(item),
            self._build_hook_post(item),
            self._build_story_slide("1/", slide_titles[0], [
                f"{topic}는 {category} 흐름에서 봐야 하는 기술입니다.",
                f"{company}가 공개했습니다.",
                "먼저 용어부터.",
                "겉으로는 새 기능 하나처럼 보입니다.",
                "근데 뜯어보면 실제 적용 방식을 건드리는 이야기입니다.",
                "그래서 첫 인상보다 한 단계 더 들여다봐야 합니다.",
            ]),
            self._build_story_slide("2/", slide_titles[1], [
                "핵심은 이겁니다.",
                "좋은 모델이나 도구가 나와도 실무 적용은 느립니다.",
                "성능, 비용, 지연 시간, 운영 난이도가 한꺼번에 걸리거든요.",
                "논문이나 발표만 보면 쉬워 보입니다.",
                "근데 현장에서는 연결하고 검증하는 시간이 더 오래 걸립니다.",
                "이러면 좋은 기술이어도 바로 쓰기 어렵습니다.",
            ]),
            self._build_story_slide("3/", slide_titles[2], [
                f"접근법은 {self._shorten(summary, 68)}",
                "복잡하게 들리지만 발상은 단순합니다.",
                "사용자가 일일이 맞춰야 했던 부분을 줄이는 겁니다.",
                "기존 도구와 이어지는 지점을 더 명확히 만든 거죠.",
                "화려한 기능보다 붙이기 쉬운 구조가 더 중요할 때가 있습니다.",
                "개발자는 새 기술보다 붙이기 쉬운 기술을 먼저 쓰거든요.",
            ]),
            self._build_story_slide("4/", slide_titles[3], [
                "주목할 건 구현부입니다.",
                f"{company}가 공개한 내용의 중심도 여기에 있습니다.",
                f"{self._shorten(summary, 86)}",
                "여기서 중요한 건 추상적인 방향성이 아닙니다.",
                "실제로 어떤 입력을 받고 어떤 출력으로 이어지는지가 핵심입니다.",
                "API, 라이브러리, 백엔드 같은 연결부가 그래서 중요합니다.",
            ]),
            self._build_story_slide("5/", slide_titles[4], [
                f"쉽게 말하면 {self._sentence_case(easy)}",
                "비유하면 좋은 엔진을 차에 얹는 것과 비슷합니다.",
                "엔진만 좋아도 안 됩니다.",
                "차체와 변속기까지 맞아야 제대로 달리죠.",
                "AI 시스템도 모델 하나만 빠르다고 끝나지 않습니다.",
                "데이터가 들어오고 결과가 나가는 길 전체가 중요합니다.",
            ]),
            self._build_story_slide("6/", slide_titles[5], [
                "결과는 숫자로 봐야 합니다.",
                f"현재 아카이브 기준 중요도는 {importance}점입니다.",
                "성능 수치와 조건은 원문에서 다시 확인하는 게 좋습니다.",
                "다만 방향은 분명합니다.",
                f"{category} 영역에서 실무자가 체크할 이유가 생겼습니다.",
                "특히 속도, 비용, 운영 난이도 중 하나라도 줄면요.",
                "작은 개선처럼 보여도 실제 제품에서는 차이가 큽니다.",
            ]),
            self._build_story_slide("7/", slide_titles[6], [
                "앞으로 바뀌는 건 기술 자체보다 사용 방식일 수 있습니다.",
                "좋은 모델을 아는 사람보다 잘 엮는 사람이 유리해집니다.",
                "도구를 빠르게 검증하는 팀이 먼저 학습합니다.",
                f"{self._shorten(title, 78)}은 그 흐름에서 볼 만한 신호입니다.",
                "이런 업데이트가 쌓일 때 시장이 움직입니다.",
                f"출처: {source_url}",
            ]),
        ]

        return [self._limit_post(post) for post in posts]

    def _story_slide_titles(self, item: Dict[str, Any]) -> List[str]:
        """Create content-specific slide subtitles while preserving storyline order."""
        title = item["title"]
        company = item["company"]
        category = item["category"]
        topic = self._topic_phrase(title, company)
        metric = self._metric_phrase(item)
        topic_subject = f"{topic}{self._topic_marker(topic)}"
        company_subject = f"{company}{self._topic_marker(company)}"
        metric_instrument = f"{metric}{self._instrument_marker(metric)}"

        subtitles = [
            f"{topic_subject} 단순 업데이트가 아닙니다",
            f"{topic}의 병목은 적용 속도입니다",
            f"{company_subject} 연결 방식을 바꿨습니다",
            f"{topic_subject} {category} 구현부를 건드립니다",
            f"{topic}의 핵심은 흐름을 줄이는 겁니다",
            f"{metric_instrument} 성과를 확인해야 합니다",
            f"{topic} 이후엔 쓰는 방식이 바뀝니다",
        ]
        return [self._shorten(subtitle, 38) for subtitle in subtitles]

    def _topic_phrase(self, title: str, company: str) -> str:
        cleaned = re.sub(r"\s+", " ", title).strip()
        cleaned = re.sub(r"^(새로운|최신|네이티브 속도)\s+", "", cleaned)
        cleaned = self._normalize_product_terms(cleaned)
        if len(cleaned) < 6:
            cleaned = f"{company} 발표"
        return self._shorten(cleaned, 24)

    def _display_title(self, item: Dict[str, Any]) -> str:
        return self._normalize_product_terms(item["title"])

    def _normalize_product_terms(self, text: str) -> str:
        cleaned = str(text)
        cleaned = cleaned.replace("vLLM 변형기 모델링 백엔드", "vLLM Transformers 백엔드")
        cleaned = cleaned.replace("변형기 모델링 백엔드", "Transformers 백엔드")
        cleaned = cleaned.replace("변형기", "Transformers")
        return cleaned

    def _metric_phrase(self, item: Dict[str, Any]) -> str:
        text = " ".join([
            item.get("title", ""),
            item.get("summary", ""),
            item.get("easy_explainer", ""),
        ])
        if re.search(r"\d+(\.\d+)?\s?(%|배|x|ms|tokens/s|tok/s)", text, re.IGNORECASE):
            return "숫자"
        if item.get("importance"):
            return f"중요도 {item['importance']}점"
        return "원문 근거"

    def _topic_marker(self, text: str) -> str:
        """Return a natural Korean topic marker for a phrase."""
        if not text:
            return "는"
        last_char = text[-1]
        code = ord(last_char) - ord("가")
        if 0 <= code <= 11171:
            return "은" if code % 28 else "는"
        return "는"

    def _instrument_marker(self, text: str) -> str:
        """Return a natural Korean instrument marker for a phrase."""
        if not text:
            return "로"
        last_char = text[-1]
        code = ord(last_char) - ord("가")
        if 0 <= code <= 11171:
            return "으로" if code % 28 else "로"
        return "로"

    def _build_title_post(self, item: Dict[str, Any]) -> str:
        return self._shorten(self._display_title(item), 120)

    def _build_hook_post(self, item: Dict[str, Any]) -> str:
        title = self._shorten(self._display_title(item), 76)
        return "\n".join([
            f"{item['company']}가 {title} 내용을 공개했습니다.",
            "겉보기엔 평범한 기술 업데이트처럼 보입니다.",
            "근데 뜯어보면 실무 병목을 건드리는 이야기입니다.",
            f"{item['category']} 흐름에서 왜 중요한지 같이 봐야 합니다.",
            HOOK_CLOSING_LINE,
        ])

    def _build_story_slide(self, number: str, subtitle: str, lines: List[str]) -> str:
        if subtitle in GENERIC_STORYLINE_TITLES:
            raise ValueError(f"Generic slide subtitle is not allowed: {subtitle}")
        body = [self._shorten(line, 82) for line in lines[:8]]
        while len(body) < 6:
            body.append("원문 기준으로 추가 확인하면 더 선명해집니다.")
        return "\n".join([f"{number} {subtitle}", *body[:8]])

    def _archive_date(self, archive_file: Path) -> str:
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})", archive_file.stem)
        if match:
            return "".join(match.groups())
        return datetime.now().strftime("%Y%m%d")

    def _slug(self, item: Dict[str, Any]) -> str:
        seed = item.get("source_url") or item["title"]
        source_tail = re.sub(r"[?#].*$", "", seed).rstrip("/").split("/")[-1]
        base = source_tail or item["title"]
        slug = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", base).strip("-").lower()
        slug = slug[:36].strip("-")
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:6]
        return f"{slug or item['company'].lower()}-{digest}"

    def _shorten(self, text: str, limit: int) -> str:
        normalized = " ".join(str(text).split())
        if len(normalized) <= limit:
            return normalized
        return normalized[:limit - 1].rstrip() + "…"

    def _sentence_case(self, text: str) -> str:
        cleaned = self._shorten(text, 220)
        if cleaned.endswith((".", "요", "다", "죠", "…")):
            return cleaned
        return cleaned + "라는 뜻이에요."

    def _hashtag(self, value: str) -> str:
        tag = re.sub(r"[^a-zA-Z0-9가-힣]", "", value)
        return tag or "테크뉴스"

    def _limit_post(self, post: str) -> str:
        if len(post) <= MAX_THREAD_CHARS:
            return post
        return self._shorten(post, MAX_THREAD_CHARS)

    def generate_paper_thread(self, paper_input: str):
        """Generate thread from arXiv paper"""
        print(f"[ROUTE] 논문 팀")
        print(f"[INPUT] {paper_input}")
        print()
        print("=" * 60)
        print("Claude Code Agent 활성화:")
        print("  1. paper-analyzer.md - 논문 분석")
        print("  2. paper-thread-writer.md - 스레드 작성")
        print("  3. reviewer.md - 품질 검수")
        print("=" * 60)
        print()
        print("[TIP] 다음 명령으로 Claude에게 요청하세요:")
        print(f"   claude '{paper_input} 논문 스레드로 만들어줘'")

        return 0

    def generate_company_thread(self, company_input: str):
        """Generate thread from company analysis"""
        print(f"[ROUTE] 기업분석 팀")
        print(f"[INPUT] {company_input}")
        print()
        print("=" * 60)
        print("Claude Code Agent 활성화:")
        print("  1. company-researcher.md - 기업 리서치")
        print("  2. company-thread-writer.md - 스레드 작성")
        print("  3. reviewer.md - 품질 검수")
        print("=" * 60)
        print()
        print("[TIP] 다음 명령으로 Claude에게 요청하세요:")
        print(f"   claude '{company_input} 기업분석 스레드 만들어줘'")

        return 0

    def run(self, input_text: str, content_type: str = None):
        """Main execution"""
        # Route to appropriate team
        detected_type = self.route_input(input_text, content_type)

        if detected_type == "news":
            return self.generate_news_thread(input_text)
        elif detected_type == "paper":
            return self.generate_paper_thread(input_text)
        elif detected_type == "company":
            return self.generate_company_thread(input_text)
        else:
            print(f"[ERROR] Unknown content type: {detected_type}")
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="Thread Generator - AI 콘텐츠 자동 스레드 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 데일리뉴스
  %(prog)s --type news --input latest
  %(prog)s --type news --input 2026-01-31

  # 논문
  %(prog)s --type paper --input "https://arxiv.org/abs/2401.12345"

  # 기업분석
  %(prog)s --type company --input "OpenAI"
  %(prog)s --type company --input "NVDA"

  # Auto-detect
  %(prog)s --input "오늘 뉴스"
  %(prog)s --input "Anthropic 분석"
        """
    )

    parser.add_argument(
        "--type",
        choices=["news", "paper", "company"],
        help="콘텐츠 타입 (미지정시 자동 감지)"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="입력 (날짜/URL/기업명)"
    )

    args = parser.parse_args()

    generator = ThreadGenerator()
    return generator.run(args.input, args.type)


if __name__ == "__main__":
    sys.exit(main())
