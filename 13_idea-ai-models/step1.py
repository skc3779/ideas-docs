import feedparser
import requests
from bs4 import BeautifulSoup
import json
import argparse
from datetime import datetime
from urllib.parse import urlparse
import re
try:
    from ddgs import DDGS
except Exception:
    from duckduckgo_search import DDGS
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
    "OpenAI Blog": "https://openai.com/blog/rss.xml"
}

def parse_args():
    now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    default_output = f"trends_data_1차_{now}.json"

    parser = argparse.ArgumentParser(
        description="RSS 1차 수집: 제목/링크/원문링크(해당 시) JSON 생성"
    )
    parser.add_argument(
        "-i",
        "--input-json",
        default="",
        help=(
            "피드 설정 JSON 경로(선택). "
            "미지정 시 내장 기본 피드 사용. "
            "형식: {\"피드명\":\"URL\"} 또는 [{\"name\":\"...\",\"url\":\"...\"}]"
        ),
    )
    parser.add_argument(
        "-o",
        "--output-json",
        default=default_output,
        help="출력 JSON 경로",
    )
    return parser.parse_args()


def load_feeds(input_json_path):
    if not input_json_path:
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
    h = h.replace("www.", "")
    return h


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
    href = ""
    if isinstance(src, dict):
        href = src.get("href") or src.get("url") or ""
    else:
        href = getattr(src, "href", "") or getattr(src, "url", "") or ""
    if not href:
        return ""
    return normalize_domain(href)


def extract_desc_links(entry):
    desc = entry.get("description", "") if isinstance(entry, dict) else getattr(entry, "description", "")
    if not desc:
        return []
    soup = BeautifulSoup(desc, "html.parser")
    links = []
    for a_tag in soup.find_all("a"):
        href = a_tag.get("href", "").strip()
        if href:
            links.append(href)
    return links


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


def find_article_on_source_domain(title, source_domain):
    if not source_domain:
        return ""

    query_title = re.sub(r"\s*-\s*[^-]+$", "", title or "")
    query = f"site:{source_domain} {query_title}"

    try:
        results = DDGS().text(query, max_results=8)
    except Exception:
        return ""

    best_url = ""
    best_score = -999
    for r in results:
        candidate = r.get("href", "")
        if not candidate:
            continue

        # 기본 도메인/경로 검증
        base_score = score_candidate(candidate, source_domain)
        if base_score < 0:
            continue

        # 검색 결과의 title/snippet과 원제목 키워드 일치도 반영
        title_text = r.get("title", "")
        body_text = r.get("body", "")
        overlap = title_overlap_score(title, f"{title_text} {body_text}")
        if overlap < 2:
            continue

        total = base_score + (overlap * 10)
        if total > best_score:
            best_score = total
            best_url = candidate

    return best_url if best_score >= 60 else ""


def score_candidate(url, source_domain):
    host = host_of(url)
    if not host:
        return -999
    if is_google_news_url(url):
        return -999
    if host in BAD_HOSTS:
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


def resolve_google_news_url(entry):
    source_domain = extract_source_domain(entry)
    candidates = []

    # 0) 전용 디코더로 Google 링크 직접 복원 (가장 신뢰도 높음)
    if gnewsdecoder is not None:
        try:
            decoded = gnewsdecoder(entry.link)
            if isinstance(decoded, dict):
                decoded_url = decoded.get("decoded_url", "")
            else:
                decoded_url = ""
            if decoded_url:
                candidates.append(decoded_url)
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

    uniq = []
    seen = set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        uniq.append(c)

    best_url = ""
    best_score = -999
    for c in uniq:
        s = score_candidate(c, source_domain)
        if s > best_score:
            best_score = s
            best_url = c

    if best_score >= 60:
        return best_url, source_domain

    # 4) 리다이렉트가 막히는 환경을 대비한 source-domain 제한 검색 복원
    fallback = find_article_on_source_domain(getattr(entry, "title", ""), source_domain)
    if fallback:
        return fallback, source_domain

    # 60점 미만이면 확정 실패로 반환
    return "", source_domain

def main():
    args = parse_args()
    feeds = load_feeds(args.input_json)

    data = []

    for name, url in feeds.items():
        print(f"Fetching {name}...")
        if name == "Google 트렌드":
            try:
                resp = requests.get(url, timeout=10)
                soup = BeautifulSoup(resp.content, "xml")
                items = soup.find_all("item")
                for item in items[:3]:
                    title_node = item.find("title")
                    title = title_node.text if title_node else ""
                    news_item = item.find("ht:news_item")
                    if news_item:
                        news_title_node = news_item.find("ht:news_item_title")
                        news_url_node = news_item.find("ht:news_item_url")
                        news_title = news_title_node.text if news_title_node else ""
                        news_url = news_url_node.text if news_url_node else ""
                        final_title = f"{title} : {news_title}"
                        final_link = news_url
                    else:
                        final_title = title
                        link_node = item.find("link")
                        final_link = link_node.text if link_node else ""
                    data.append({"source": name, "title": final_title, "link": final_link})
            except Exception as e:
                print(f"Error fetching {name}: {e}")
        else:
            try:
                d = feedparser.parse(url)
                for entry in d.entries[:3]:
                    item_data = {"source": name, "title": entry.title, "link": entry.link}
                    if "Google" in name and "뉴스" in name:
                        orig_url, source_domain = resolve_google_news_url(entry)
                        item_data["원문링크"] = orig_url
                        item_data["출처도메인"] = source_domain
                    elif name in ["OpenAI Blog", "TechCrunch AI", "geeknews"]:
                        item_data["원문링크"] = entry.link
                    data.append(item_data)
            except Exception as e:
                print(f"Error fetching {name}: {e}")

    out_payload = {
        "실행시간": datetime.now().strftime("%Y-%m-%d_%H%M%S"),
        "data": data
    }
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(out_payload, f, ensure_ascii=False, indent=2)

    print(f"1차 수집 완료. 총 항목 수: {len(data)}")
    print(f"저장 파일: {args.output_json}")


if __name__ == "__main__":
    main()
