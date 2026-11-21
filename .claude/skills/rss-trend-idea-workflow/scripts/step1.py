"""RSS 1차 수집: 피드별 최신 기사 제목/링크/원문링크/출처도메인을 JSON으로 저장한다.

사용 예 (워크스페이스 루트에서, PowerShell/Bash 공통):
    python .claude/skills/rss-trend-idea-workflow/scripts/step1.py -f 10_idea-google-search
"""
import sys

# Windows 콘솔(cp949)에서도 한글 출력이 깨지거나 UnicodeEncodeError가 나지 않도록 강제 UTF-8
# (기존 $env:PYTHONIOENCODING="utf-8" 접두어가 더 이상 필요 없음)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime
from urllib.parse import urlparse

try:
    import feedparser
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    sys.exit(
        f"[ERROR] 필수 패키지 누락: {e.name}\n"
        "  -> pip install -r .claude/skills/rss-trend-idea-workflow/requirements.txt"
    )

try:
    from ddgs import DDGS
except Exception:
    try:
        from duckduckgo_search import DDGS
    except Exception:
        DDGS = None
try:
    from googlenewsdecoder import gnewsdecoder
except Exception:
    gnewsdecoder = None

DEFAULT_FEEDS = {
    "Google 트렌드": "https://trends.google.com/trending/rss?geo=KR",
    "Google 전체 뉴스": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "Google 경제 뉴스": "https://news.google.com/rss/search?q=경제&hl=ko&gl=KR&ceid=KR:ko",
    "Google 과학 뉴스": "https://news.google.com/rss/search?q=과학&hl=ko&gl=KR&ceid=KR:ko",
    "Google AI 뉴스": "https://news.google.com/rss/search?q=AI&hl=ko&gl=KR&ceid=KR:ko",
    "geeknews": "https://feeds.feedburner.com/geeknews-feed",
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "OpenAI Blog": "https://openai.com/blog/rss.xml",
}

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

BAD_HOSTS = {
    "namu.wiki",
    "wikipedia.org",
    "github.com",
    "desktop.telegram.org",
    "telegram.org",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="RSS 1차 수집: 제목/링크/원문링크(해당 시) JSON 생성"
    )
    parser.add_argument(
        "-f", "--folder", default="10_idea-google-search",
        help="대상 폴더 경로 (기본값: 10_idea-google-search)",
    )
    parser.add_argument(
        "-i", "--input-json", default="",
        help="피드 설정 JSON 경로(선택). 미지정 시 폴더 내 rss-feeds.json 사용.",
    )
    parser.add_argument("-o", "--output-json", default="", help="출력 JSON 경로")
    parser.add_argument(
        "-n", "--limit", type=int, default=3,
        help="피드별 수집 항목 수 (기본값: 3)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        sys.exit(f"[ERROR] 대상 폴더가 없습니다: {args.folder}")
    if args.limit < 1:
        sys.exit("[ERROR] --limit 은 1 이상이어야 합니다.")

    if not args.input_json:
        args.input_json = os.path.join(args.folder, "rss-feeds.json")
    if not args.output_json:
        now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        args.output_json = os.path.join(args.folder, f"trends_data_1차_{now}.json")
    return args


def load_feeds(input_json_path):
    if not input_json_path or not os.path.exists(input_json_path):
        print(f"[WARN] 피드 설정 파일이 없어 내장 기본 피드를 사용합니다: {input_json_path}")
        return DEFAULT_FEEDS

    with open(input_json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict):
        return payload

    if isinstance(payload, list):
        out = {}
        for row in payload:
            if not isinstance(row, dict):
                continue
            name = row.get("name") or row.get("source")
            url = row.get("url")
            if name and url:
                out[name] = url
        if out:
            return out

    raise ValueError("입력 JSON 형식이 올바르지 않습니다. dict 또는 list[dict] 형식이어야 합니다.")


def host_of(url):
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def path_of(url):
    try:
        return urlparse(url).path or "/"
    except Exception:
        return "/"


def is_google_news_url(url):
    return "news.google.com" in (host_of(url) or "")


def is_google_trends_feed(url):
    """피드 '이름'이 아니라 URL로 판별 → rss-feeds.json에서 이름을 바꿔도 동작한다."""
    return "trends.google." in (host_of(url) or "")


def is_root_or_section_url(url):
    p = path_of(url).rstrip("/")
    if p == "":
        return True
    section_only = {"/news", "/sports", "/entertainment", "/economy", "/it", "/world"}
    return p in section_only


def looks_like_article_path(url):
    p = path_of(url).lower()
    if p in {"/", ""}:
        return False
    article_keywords = ["article", "arti", "view", "story", "news", "read", "/v/"]
    if any(k in p for k in article_keywords):
        return True
    if re.search(r"/20\d{2}/\d{2}/\d{2}/", p):
        return True
    if re.search(r"[a-z0-9-]{20,}", p):
        return True
    return False


def normalize_domain(domain_or_url):
    h = host_of(domain_or_url) if "://" in (domain_or_url or "") else (domain_or_url or "").lower()
    return h.replace("www.", "")


def domain_matches(candidate_url, source_domain):
    c = host_of(candidate_url)
    s = normalize_domain(source_domain)
    if not c or not s:
        return False
    return c == s or c.endswith("." + s)


def extract_source_domain(entry):
    src = entry.get("source") if isinstance(entry, dict) else getattr(entry, "source", None)
    if not src:
        return ""
    if isinstance(src, dict):
        href = src.get("href") or src.get("url") or ""
    else:
        href = getattr(src, "href", "") or getattr(src, "url", "") or ""
    return normalize_domain(href) if href else ""


def extract_desc_links(entry):
    desc = entry.get("description", "") if isinstance(entry, dict) else getattr(entry, "description", "")
    if not desc:
        return []
    soup = BeautifulSoup(desc, "html.parser")
    return [a.get("href", "").strip() for a in soup.find_all("a") if a.get("href", "").strip()]


def title_tokens(title):
    clean = re.sub(r"\s*-\s*[^-]+$", "", (title or "").lower())
    tokens = re.findall(r"[가-힣a-z0-9]{2,}", clean)
    stopwords = {"속보", "종합", "단독", "기자", "뉴스"}
    return [t for t in tokens if t not in stopwords]


def title_overlap_score(title, text):
    ts = title_tokens(title)
    if not ts:
        return 0
    lower = (text or "").lower()
    return sum(1 for t in ts if t in lower)


def score_candidate(url, source_domain):
    host = host_of(url)
    if not host or is_google_news_url(url) or host in BAD_HOSTS:
        return -999
    score = 0
    if source_domain and domain_matches(url, source_domain):
        score += 40
    if looks_like_article_path(url):
        score += 30
    if is_root_or_section_url(url):
        score -= 50
    if not source_domain:
        score += 5
    return score


def find_article_on_source_domain(title, source_domain):
    if not source_domain or DDGS is None:
        return ""
    query_title = re.sub(r"\s*-\s*[^-]+$", "", title or "")
    try:
        results = DDGS().text(f"site:{source_domain} {query_title}", max_results=8)
    except Exception:
        return ""

    best_url, best_score = "", -999
    for r in results or []:
        candidate = r.get("href", "")
        if not candidate:
            continue
        base_score = score_candidate(candidate, source_domain)
        if base_score < 0:
            continue
        # 검색 결과의 title/snippet과 원제목 키워드 일치도 반영
        overlap = title_overlap_score(title, f"{r.get('title', '')} {r.get('body', '')}")
        if overlap < 2:
            continue
        total = base_score + overlap * 10
        if total > best_score:
            best_score, best_url = total, candidate
    return best_url if best_score >= 60 else ""


def resolve_google_news_url(entry):
    source_domain = extract_source_domain(entry)
    candidates = []

    # 0) 전용 디코더로 Google 링크 직접 복원 (가장 신뢰도 높음)
    if gnewsdecoder is not None:
        try:
            decoded = gnewsdecoder(entry.link)
            if isinstance(decoded, dict) and decoded.get("decoded_url"):
                candidates.append(decoded["decoded_url"])
        except Exception:
            pass

    # 1) description 내부 링크
    candidates.extend(extract_desc_links(entry))

    # 2) 리다이렉트 체인 최종 URL
    try:
        resp = requests.get(entry.link, headers=UA, timeout=8, allow_redirects=True)
        if resp.url:
            candidates.append(resp.url)
    except Exception:
        pass

    # 3) source[url]은 도메인 후보로만 사용 (기사 경로가 없으면 점수 낮음)
    src = entry.get("source") if isinstance(entry, dict) else getattr(entry, "source", None)
    if src:
        if isinstance(src, dict):
            src_url = src.get("href") or src.get("url")
        else:
            src_url = getattr(src, "href", "") or getattr(src, "url", "")
        if src_url:
            candidates.append(src_url)

    best_url, best_score, seen = "", -999, set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        s = score_candidate(c, source_domain)
        if s > best_score:
            best_score, best_url = s, c

    if best_score >= 60:
        return best_url, source_domain

    # 4) 리다이렉트가 막히는 환경을 대비한 source-domain 제한 검색 복원
    fallback = find_article_on_source_domain(getattr(entry, "title", ""), source_domain)
    if fallback:
        return fallback, source_domain

    # 60점 미만이면 확정 실패로 반환 (step2에서 재탐색)
    return "", source_domain


def collect_google_trends(name, url, limit):
    rows = []
    resp = requests.get(url, headers=UA, timeout=10)
    soup = BeautifulSoup(resp.content, "xml")
    for item in soup.find_all("item")[:limit]:
        title_node = item.find("title")
        title = title_node.text if title_node else ""
        news_item = item.find("ht:news_item")
        if news_item:
            nt = news_item.find("ht:news_item_title")
            nu = news_item.find("ht:news_item_url")
            final_title = f"{title} : {nt.text if nt else ''}"
            final_link = nu.text if nu else ""
        else:
            final_title = title
            link_node = item.find("link")
            final_link = link_node.text if link_node else ""
        pub = item.find("pubDate")
        rows.append({
            "source": name,
            "title": final_title,
            "link": final_link,
            "발행일": pub.text if pub else "",
        })
    return rows


def collect_rss(name, url, limit):
    rows = []
    d = feedparser.parse(url, agent=UA["User-Agent"])
    if not d.entries:
        print(f"  [WARN] {name}: 항목 0개 (피드 URL/접속 상태 확인 필요)")
    for entry in d.entries[:limit]:
        row = {
            "source": name,
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "발행일": entry.get("published", "") or entry.get("updated", ""),
        }
        if is_google_news_url(row["link"]):
            orig_url, source_domain = resolve_google_news_url(entry)
            row["원문링크"] = orig_url
            row["출처도메인"] = source_domain
        else:
            # 일반 피드는 link 자체가 원문 (geeknews/TechCrunch/OpenAI/ByteByteGo 등 공통)
            row["원문링크"] = row["link"]
        rows.append(row)
    return rows


def main():
    args = parse_args()
    feeds = load_feeds(args.input_json)

    data = []
    for name, url in feeds.items():
        print(f"Fetching {name}...")
        try:
            if is_google_trends_feed(url):
                data.extend(collect_google_trends(name, url, args.limit))
            else:
                data.extend(collect_rss(name, url, args.limit))
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"1차 수집 완료. 총 항목 수: {len(data)}")
    for src, cnt in Counter(row["source"] for row in data).items():
        print(f"  - {src}: {cnt}건")
    unresolved = sum(1 for row in data if "원문링크" in row and not row["원문링크"])
    if unresolved:
        print(f"  - Google 뉴스 원문링크 미확정: {unresolved}건 (step2에서 재탐색)")
    print(f"저장 파일: {args.output_json}")


if __name__ == "__main__":
    main()
