"""Task 2 - crawl public explanatory articles for the RAG corpus."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

import requests
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as to_markdown


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "landing" / "news"
REQUEST_TIMEOUT: Final = (15, 90)
MIN_CONTENT_CHARACTERS: Final = 1_000
USER_AGENT: Final = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36 "
    "K4-Day08-RAG-Corpus/1.0"
)


ARTICLE_SOURCES: Final = (
    {
        "id": "NEWS-01",
        "topic": "Luật Bảo hiểm xã hội 2024 và thời điểm có hiệu lực",
        "preferred_url": "https://thuvienphapluat.vn/hoi-dap-phap-luat/839F306-hd-luat-bao-hiem-xa-hoi-moi-nhat-2024-va-cac-van-ban-huong-dan-hien-nay.html",
        "fallback_url": "https://xaydungchinhsach.chinhphu.vn/14-noi-dung-moi-trong-tam-cua-luat-bao-hiem-xa-hoi-2024-119240806172349712.htm",
    },
    {
        "id": "NEWS-02",
        "topic": "Bảo hiểm xã hội tự nguyện theo Luật Bảo hiểm xã hội 2024",
        "preferred_url": "https://thuvienphapluat.vn/hoi-dap-phap-luat/83A8D92-hd-toan-van-nghi-dinh-159-2025-nd-cp-huong-dan-thi-hanh-luat-bao-hiem-xa-hoi-ve-bao-hiem-xa-hoi-tu-ngu.html",
        "fallback_url": "https://xaydungchinhsach.chinhphu.vn/nhung-dieu-can-biet-ve-chinh-sach-bao-hiem-xa-hoi-tu-nguyen-119250913101137277.htm",
    },
    {
        "id": "NEWS-03",
        "topic": "Quyền và lợi ích của người tham gia bảo hiểm xã hội",
        "preferred_url": "https://thuvienphapluat.vn/lao-dong-tien-luong/viec-giai-quyet-cac-che-do-bao-hiem-xa-hoi-duoc-xac-dinh-nhu-the-nao-48959.html",
        "fallback_url": "https://xaydungchinhsach.chinhphu.vn/9-nhom-diem-moi-noi-bat-cua-luat-bao-hiem-xa-hoi-sua-doi-119240629092723909.htm",
    },
    {
        "id": "NEWS-04",
        "topic": "Nội dung hợp đồng lao động theo Bộ luật Lao động 2019",
        "preferred_url": "https://thuvienphapluat.vn/lao-dong-tien-luong/hop-dong-lao-dong-la-su-thoa-thuan-giua-doi-tuong-nao-623718-22482.html",
        "fallback_url": "https://xaydungchinhsach.chinhphu.vn/noi-dung-cua-hop-dong-lao-dong-va-hop-dong-lam-viec-co-gi-khac-nhau-119230830114203459.htm",
    },
    {
        "id": "NEWS-05",
        "topic": "Tiền lương, thời giờ làm việc và giới hạn làm thêm giờ",
        "preferred_url": "https://thuvienphapluat.vn/lao-dong-tien-luong/tien-luong-lam-them-gio-cua-nguoi-lao-dong-duoc-tinh-the-nao-3024.html",
        "fallback_url": "https://xaydungchinhsach.chinhphu.vn/nguoi-su-dung-lao-dong-vi-pham-ve-tien-luong-gio-lam-viec-gio-nghi-ngoi-xu-phat-the-nao-119260717182001954.htm",
    },
)

# Public exercise contract: the preferred crawl targets remain directly visible.
ARTICLE_URLS: Final = [source["preferred_url"] for source in ARTICLE_SOURCES]

MAIN_CONTENT_SELECTORS: Final = (
    "[itemprop='articleBody']",
    ".news-content",
    ".news-content-body",
    ".content-news",
    ".content-detail",
    ".detail-content",
    ".article-content",
    ".entry-content",
    "#news-content",
    "#content-news",
    "article",
    "main",
)
NOISE_PATTERN: Final = re.compile(
    r"(?:^|[-_ ])(?:menu|header|footer|sidebar|related|comment|advert|ads|"
    r"login|register|social|breadcrumb|pagination|banner|tool|toc)(?:$|[-_ ])",
    flags=re.IGNORECASE,
)


def _element_label(element: Tag) -> str:
    classes = " ".join(element.get("class", []))
    return f"{element.get('id', '')} {classes}".strip()


def _clean_candidate(candidate: Tag) -> Tag:
    for element in candidate.select(
        "script, style, nav, header, footer, form, iframe, noscript, aside, svg, "
        "figure, .VCSortableInPreviewMode.type-6, "
        ".VCSortableInPreviewMode.type-6_preview"
    ):
        element.decompose()
    for element in list(candidate.find_all(True)):
        if element.parent is not None and NOISE_PATTERN.search(_element_label(element)):
            element.decompose()
    return candidate


def _select_main_content(soup: BeautifulSoup) -> Tag:
    candidates: list[Tag] = []
    seen: set[int] = set()
    for selector in MAIN_CONTENT_SELECTORS:
        for candidate in soup.select(selector):
            identity = id(candidate)
            if identity not in seen:
                candidates.append(candidate)
                seen.add(identity)

    if not candidates:
        body = soup.body
        if body is None:
            raise ValueError("Page does not contain an HTML body")
        candidates = [body]

    # TVPL uses different templates across Hỏi đáp and Lao động - Tiền lương.
    # The article body is consistently the candidate with the most paragraph /
    # heading text after navigation elements have been excluded.
    eligible = [
        candidate
        for candidate in candidates
        if not NOISE_PATTERN.search(_element_label(candidate))
    ] or candidates
    return max(eligible, key=lambda item: len(item.get_text(" ", strip=True)))


def _extract_title(soup: BeautifulSoup) -> str:
    heading = soup.find("h1")
    if heading and heading.get_text(" ", strip=True):
        return heading.get_text(" ", strip=True)
    og_title = soup.select_one("meta[property='og:title']")
    if og_title and og_title.get("content"):
        return str(og_title["content"]).strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    raise ValueError("Could not extract article title")


def _normalise_markdown(markdown: str, title: str) -> str:
    markdown = markdown.replace("\xa0", " ").replace("\u200b", "")
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    title_pattern = re.compile(
        rf"^#{{1,6}}\s+{re.escape(title)}\s*\n+", flags=re.IGNORECASE
    )
    return title_pattern.sub("", markdown, count=1).strip()


def _validate_article(article: dict) -> None:
    title = article["title"].strip()
    content = article["content_markdown"].strip()
    lowered = f"{title}\n{content[:1000]}".lower()
    if any(marker in lowered for marker in ("access denied", "captcha", "cloudflare")):
        raise ValueError("Crawler received an access/challenge page")
    if title.lower() in {"đăng nhập", "login", "error", "unknown"}:
        raise ValueError(f"Invalid article title: {title!r}")
    if len(content) < MIN_CONTENT_CHARACTERS:
        raise ValueError(
            f"Article body is too short ({len(content)} characters); "
            "refusing to save a likely navigation/login page"
        )
    if not any(term in content.lower() for term in ("lao động", "bảo hiểm xã hội")):
        raise ValueError("Extracted body is not relevant to the selected corpus")


def _crawl_article_sync(url: str) -> dict:
    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    if "html" not in response.headers.get("content-type", "").lower():
        raise ValueError(f"Expected HTML, got {response.headers.get('content-type')!r}")

    soup = BeautifulSoup(response.text, "lxml")
    title = _extract_title(soup)
    candidate = _clean_candidate(_select_main_content(soup))
    content = _normalise_markdown(
        to_markdown(str(candidate), heading_style="ATX", bullets="-"), title
    )
    article = {
        "url": url,
        "final_url": response.url,
        "title": title,
        "date_crawled": datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds"),
        "content_markdown": content,
    }
    _validate_article(article)
    return article


async def crawl_article(url: str) -> dict:
    """Crawl one public page without blocking the asyncio event loop."""
    return await asyncio.to_thread(_crawl_article_sync, url)


async def crawl_all() -> None:
    """Crawl each preferred article, falling back to an official public source."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    saved_count = 0

    for index, source in enumerate(ARTICLE_SOURCES, 1):
        preferred_error: Exception | None = None
        article: dict | None = None
        for source_type, url in (
            ("preferred", source["preferred_url"]),
            ("official_fallback", source["fallback_url"]),
        ):
            try:
                article = await crawl_article(url)
                article.update(
                    {
                        "id": source["id"],
                        "topic": source["topic"],
                        "source_type": source_type,
                        "preferred_url": source["preferred_url"],
                    }
                )
                if preferred_error is not None:
                    article["fallback_reason"] = (
                        f"{type(preferred_error).__name__}: {preferred_error}"
                    )
                break
            except Exception as error:
                if source_type == "preferred":
                    preferred_error = error
                    print(
                        f"Preferred source unavailable for {source['id']}: "
                        f"{type(error).__name__}: {error}; trying official fallback"
                    )
                    continue
                failures.append(
                    f"{source['id']} - preferred: {preferred_error}; "
                    f"fallback: {type(error).__name__}: {error}"
                )

        if article is not None:
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(
                f"Saved: {output} "
                f"({len(article['content_markdown']):,} content characters)"
            )
            saved_count += 1

    if failures or saved_count < len(ARTICLE_SOURCES):
        details = "\n".join(f"- {item}" for item in failures)
        raise RuntimeError(
            f"Corpus crawl incomplete: saved {saved_count}/{len(ARTICLE_SOURCES)}.\n"
            f"{details}"
        )


if __name__ == "__main__":
    asyncio.run(crawl_all())
