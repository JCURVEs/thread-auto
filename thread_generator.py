#!/usr/bin/env python3
"""
Thread Generator - Main orchestration script for thread creation
Routes inputs to appropriate agent teams based on content type
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import json
import subprocess


class ThreadGenerator:
    def __init__(self):
        self.project_root = Path(__file__).parent
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
        print(f"🔀 Routing to: 데일리뉴스 팀")
        print(f"📅 Input: {date_input}")

        # Find archive file
        if date_input == "latest":
            archive_files = sorted(self.archive_dir.glob("*.md"), reverse=True)
            if not archive_files:
                print("❌ No archive files found")
                return 1
            archive_file = archive_files[0]
        else:
            archive_file = self.archive_dir / f"{date_input}.md"
            if not archive_file.exists():
                print(f"❌ Archive file not found: {archive_file}")
                return 1

        print(f"📂 Source: {archive_file}")
        print()
        print("=" * 60)
        print("Claude Code Agent 활성화:")
        print("  1. news-curator.md - 뉴스 큐레이션")
        print("  2. news-thread-writer.md - 스레드 작성")
        print("  3. reviewer.md - 품질 검수")
        print("=" * 60)
        print()
        print("💡 다음 명령으로 Claude에게 요청하세요:")
        print(f"   claude '{archive_file.name} 파일에서 스레드 만들어줘'")

        return 0

    def generate_paper_thread(self, paper_input: str):
        """Generate thread from arXiv paper"""
        print(f"🔀 Routing to: 논문 팀")
        print(f"📄 Input: {paper_input}")
        print()
        print("=" * 60)
        print("Claude Code Agent 활성화:")
        print("  1. paper-analyzer.md - 논문 분석")
        print("  2. paper-thread-writer.md - 스레드 작성")
        print("  3. reviewer.md - 품질 검수")
        print("=" * 60)
        print()
        print("💡 다음 명령으로 Claude에게 요청하세요:")
        print(f"   claude '{paper_input} 논문 스레드로 만들어줘'")

        return 0

    def generate_company_thread(self, company_input: str):
        """Generate thread from company analysis"""
        print(f"🔀 Routing to: 기업분석 팀")
        print(f"🏢 Input: {company_input}")
        print()
        print("=" * 60)
        print("Claude Code Agent 활성화:")
        print("  1. company-researcher.md - 기업 리서치")
        print("  2. company-thread-writer.md - 스레드 작성")
        print("  3. reviewer.md - 품질 검수")
        print("=" * 60)
        print()
        print("💡 다음 명령으로 Claude에게 요청하세요:")
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
            print(f"❌ Unknown content type: {detected_type}")
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
