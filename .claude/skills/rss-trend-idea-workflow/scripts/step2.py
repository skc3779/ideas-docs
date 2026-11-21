"""RSS 2차 수집: 1차 JSON의 원문 페이지를 방문해 본문 요약을 추가한 JSON을 저장한다.

사용 예 (워크스페이스 루트에서, PowerShell/Bash 공통):
    python .claude/skills/rss-trend-idea-workflow/scripts/step2.py -f 10_idea-google-search

마지막 줄에 `실행시간: YYYY-MM-DD_HHMMSS` 를 출력한다. Step 3 마크다운의 파일명/헤더에 이 값을 그대로 쓴다.
"""
import sys

# Windows 콘솔(cp949)에서도 한글 출력이 깨지지 않도록 강제 UTF-8
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import glob
import json
import os
import re
import time
from datetime import datetime
from urllib.parse import urlparse

try:
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="RSS 2차 수집: 원문 페이지 방문 후 요약 JSON 생성"
    )
    parser.add_argument(
        "-f", "--folder", default="10_idea-google-search",
        help="대상 폴더 경로 (기본값: 10_idea-google-search)",
    )
    parser.add_argument(
        "-i", "--input-json", default="",
        help="1차 수집 결과 JSON 경로 (미지정 시 대상 폴더의 최신 파일 자동 선택)",
    )
    parser.add_argument("-o", "--output-json", default="", help="2차 수집 결과 JSON 경로")
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        sys.exit(f"[ERROR] 대상 폴더가 없습니다: {args.folder}")

    if not args.input_json:
        # 파일명에 포함된 타임스탬프 기준으로 최신 파일 선택
        # (ctime 은 복사/이동 시 바뀌므로 신뢰하기 어렵다)
        files = sorted(glob.glob(os.path.join(args.folder, "trends_data_1차_*.json")))
        if not files:
            sys.exit(f"[ERROR] 대상 폴더({args.folder})에 1차 수집 결과 파일이 없습니다. step1.py 를 먼저 실행하세요.")
        args.input_json = files[-1]
    elif not os.path.exists(args.input_json):
        args.input_json = os.path.join(args.folder, args.input_json)

    if not args.output_json:
        now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        args.output_json = os.path.join(args.folder, f"trends_data_2차_{now}.json")
    return args


UA = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
    )
}

DISALLOWED_HOSTS = {
    'namu.wiki',
    'wikipedia.org',
    'github.com',
    'telegram.org',
    'desktop.telegram.org',
    'ez3c.tw',
}

MENU_KEYWORDS = [
    '로그인', '회원가입', '전체메뉴', '뉴스레터', '구독', '고객센터', '오피니언',
    '정치', '경제', '사회', '국제', '문화', '스포츠', '연예', '검색', '메뉴',
    'sign up', 'sign in', 'log in', 'subscribe', 'newsletter', 'advertise', 'privacy policy',
]

# 뉴스레터/블로그에 반복되는 상투 문구 (요약 앞부분 잡음 제거용)
BOILERPLATE_PATTERNS = [
    r'\{\{[^}]*\}\}',                                  # {{ first_name | ... }} 템플릿 변수
    r'Read Online\s*\|\s*Sign Up\s*\|\s*Advertise',    # The Rundown AI 헤더
    r'Good morning,?\s*',
    r'Welcome back!?\s*',
]


def host_of(url):
    try:
        return urlparse(url).netloc.lower().replace('www.', '')
    except Exception:
        return ''


def path_of(url):
    try:
        return urlparse(url).path or '/'
    except Exception:
        return '/'


def is_google_news_url(url):
    return 'news.google.com' in host_of(url)


def normalize_domain(value):
    if not value:
        return ''
    if '://' in value:
        return host_of(value)
    return value.lower().replace('www.', '')


def derive_allowed_domain(item):
    """허용 도메인. 피드 '이름'이 아니라 데이터(출처도메인/링크 호스트)로 판단한다.

    - Google 뉴스: RSS source[url] 기반 `출처도메인`
    - 그 외 모든 피드: 피드가 준 link 의 도메인
      (v1 은 OpenAI/TechCrunch 만 제한해서 geeknews·Stratechery 등이 검색 재탐색 시
       전혀 무관한 사이트(쇼핑몰·Pinterest 등)의 글로 바뀌어 요약되는 문제가 있었다)
    """
    if item.get('출처도메인'):
        return normalize_domain(item['출처도메인'])
    link = item.get('link', '')
    if link and not is_google_news_url(link):
        return host_of(link)
    return ''


def is_feed_own_link(url, item):
    """피드가 직접 준 원문 링크인지. 이 경우 URL 모양(기사형 경로)과 무관하게 신뢰한다.
    예: news.hada.io/topic?id=123, stratechery.com/2026/summer-vibes/"""
    link = item.get('link', '')
    return bool(link) and not is_google_news_url(link) and url == link


def domain_matches(url, allowed_domain):
    if not allowed_domain:
        return True
    h = host_of(url)
    return h == allowed_domain or h.endswith('.' + allowed_domain)


def is_root_or_section_url(url):
    p = path_of(url).rstrip('/')
    if p == '':
        return True
    section_only = {'/news', '/sports', '/entertainment', '/economy', '/it', '/world'}
    return p in section_only


def looks_like_article_path(url):
    p = path_of(url).lower()
    if p in {'', '/'}:
        return False
    article_keywords = ['article', 'arti', 'view', 'story', 'news', 'read', '/v/']
    if any(k in p for k in article_keywords):
        return True
    if re.search(r'/20\d{2}/\d{2}/\d{2}/', p):
        return True
    if re.search(r'[a-z0-9-]{20,}', p):
        return True
    return False


def is_valid_candidate_url(url, item):
    if not url:
        return False, 'URL 없음'
    if is_google_news_url(url):
        return False, 'Google News 중간 링크'

    host = host_of(url)
    if not host:
        return False, '도메인 파싱 실패'
    if host in DISALLOWED_HOSTS:
        return False, '금지 도메인'

    allowed_domain = derive_allowed_domain(item)
    if allowed_domain and not domain_matches(url, allowed_domain):
        return False, f'허용 도메인 불일치({allowed_domain})'
    if is_root_or_section_url(url):
        return False, '루트/섹션 메인 URL'
    if is_feed_own_link(url, item):
        return True, '피드 원문 링크'
    if not looks_like_article_path(url):
        return False, '기사형 경로 아님'
    return True, '유효'


def title_tokens(title):
    # 언론사 suffix 제거
    clean = re.sub(r'\s*-\s*[^-]+$', '', title or '').lower()
    parts = re.findall(r'[가-힣a-z0-9]{2,}', clean)
    stop = {'속보', '종합', '단독', '뉴스', '기자'}
    return [p for p in parts if p not in stop]


def extract_text(url):
    try:
        resp = requests.get(url, headers=UA, timeout=10)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.content, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
            tag.decompose()
        page_title = soup.title.get_text(strip=True) if soup.title else ''
        # 기사 본문 후보: 텍스트가 가장 많은 <article> (첫 <article> 이 기자정보/공유 박스인 사이트 대응)
        articles = soup.find_all('article')
        container = max(articles, key=lambda a: len(a.get_text(strip=True))) if articles else soup

        def texts_of(root, tags, min_len):
            out = []
            for n in root.find_all(tags):
                t = n.get_text(' ', strip=True)
                if len(t) > min_len:
                    out.append(t)
            return out

        # <p> → <li>(GeekNews 처럼 요약을 목록으로 쓰는 사이트) → 페이지 전체 <div> 순으로
        # 처음 200자 이상 확보되는 결과를 사용. 모두 부족하면 가장 긴 결과.
        attempts = [
            lambda: texts_of(container, ['p'], 20),
            lambda: texts_of(container, ['p', 'li'], 20),
            lambda: texts_of(soup, ['div'], 40),
        ]
        best = []
        for get in attempts:
            parts = get()
            if sum(len(t) for t in parts) >= 200:
                best = parts
                break
            if sum(len(t) for t in parts) > sum(len(t) for t in best):
                best = parts
        # 노드 경계를 줄바꿈으로 보존 → summarize() 에서 문장 경계로 사용
        return '\n'.join(best), page_title
    except Exception as e:
        return '', str(e)


def strip_boilerplate(text):
    for pat in BOILERPLATE_PATTERNS:
        text = re.sub(pat, ' ', text, flags=re.IGNORECASE)
    return re.sub(r'[ \t]{2,}', ' ', text).strip()


def nav_noise_ratio(text):
    if not text:
        return 1.0
    lowered = text.lower()
    hits = sum(lowered.count(k.lower()) for k in MENU_KEYWORDS)
    return hits / max(1, len(text) / 50)


def summarize(text):
    if not text:
        return None, "본문 없음"

    fail_keywords = [
        "Google News", "Enable JavaScript", "접속 실패", "본문 추출 실패",
        "Access Denied", "Security Check", "로봇이 아닙니다", "Are you a robot",
        "페이지가 없어요", "잘못되었거나 바뀐",
    ]
    for kw in fail_keywords:
        if kw.lower() in text.lower() and len(text) < 1000:
            return None, f"저품질 텍스트 감지: {kw}"

    if nav_noise_ratio(text) > 0.5:
        return None, "메뉴/네비게이션 텍스트 비중 과다"

    text = strip_boilerplate(text)
    # 문장 경계: 종결부호/종결어미 뒤 공백, 또는 노드 경계(줄바꿈)
    sentences = re.split(r'(?<=[.!?다요])\s+|\n+', text)
    valid_sentences, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) > 15 and s not in seen:
            valid_sentences.append(s)
            seen.add(s)

    if len(valid_sentences) < 2:
        return None, "의미 있는 문장 2개 미만"

    summary = " ".join(valid_sentences[:10])
    if len(summary) < 120:
        summary = " ".join(valid_sentences[:20])
        if len(summary) < 120:
            return None, f"본문 길이 120자 미만 (현재 {len(summary)}자)"

    # 요약문이 너무 길면 자르기 (500자 내외)
    if len(summary) > 500:
        summary = summary[:500] + "..."
    return summary, "성공"


def search_candidates(ddgs, query):
    if ddgs is None:
        return []
    try:
        res = ddgs.text(query, max_results=8) or []
    except Exception:
        res = []
    time.sleep(1)  # 검색 rate limit 완화
    return [r.get('href', '') for r in res if r.get('href')]


def run_id_from_path(path):
    m = re.search(r'(\d{4}-\d{2}-\d{2}_\d{6})', os.path.basename(path))
    return m.group(1) if m else datetime.now().strftime("%Y-%m-%d_%H%M%S")


def main():
    args = parse_args()
    with open(args.input_json, 'r', encoding='utf-8') as f:
        items = json.load(f)
    if isinstance(items, dict) and 'data' in items:   # 구버전 {"실행시간":..., "data": [...]} 호환
        items = items['data']

    ddgs = DDGS() if DDGS is not None else None
    if ddgs is None:
        print("[WARN] ddgs/duckduckgo_search 미설치 → 대체 URL 검색을 건너뜁니다.")

    results = []
    for i, item in enumerate(items):
        print(f"[{i+1}/{len(items)}] 처리 중: {item['title']}")

        target_url = item.get('원문링크') or item.get('link')
        valid, reason = is_valid_candidate_url(target_url, item)
        if not valid:
            print(f" -> 초기 원문링크 무효: {reason}")
            target_url = None

        attempts, max_attempts = 0, 3
        success, tried_urls = False, []
        fail_reason, summary_text = "", ""
        current_url = target_url

        while attempts < max_attempts and not success:
            attempts += 1

            if not current_url:
                # 검색으로 URL 찾기: site: 제한 검색 → 일반 검색 순
                allowed_domain = derive_allowed_domain(item)
                raw_query = re.sub(r'\s*-\s*[^-]+$', '', item['title'])
                queries = [f"site:{allowed_domain} {raw_query}", raw_query] if allowed_domain else [raw_query]
                for q in queries:
                    for candidate in search_candidates(ddgs, q):
                        if candidate in tried_urls:
                            continue
                        if is_valid_candidate_url(candidate, item)[0]:
                            current_url = candidate
                            break
                    if current_url:
                        break
                if not current_url:
                    fail_reason = fail_reason or "대체 URL 검색 실패"
                    break

            tried_urls.append(current_url)
            print(f" -> 시도 {attempts}: {current_url}")

            ok, invalid_reason = is_valid_candidate_url(current_url, item)
            if not ok:
                fail_reason, current_url = invalid_reason, None
                continue

            raw_text, page_title = extract_text(current_url)

            # 제목 키워드 최소 2개 교집합 체크
            tokens = title_tokens(item.get('title', ''))
            text_blob = f"{page_title} {raw_text}".lower()
            overlap = sum(1 for t in tokens if t in text_blob)
            if overlap < 2:
                fail_reason, current_url = f"제목 키워드 일치 부족({overlap})", None
                continue

            summary, reason = summarize(raw_text)
            if summary:
                success, summary_text = True, summary
                item['원문링크'] = current_url
            else:
                fail_reason, current_url = reason, None  # 다음 시도에서 검색하도록

        if success:
            item['요약정보'] = summary_text
            item['수집상태'] = '성공'
            print(" -> 요약 성공")
        else:
            item['요약정보'] = f"실패 사유: {fail_reason}, 시도 URL: {', '.join(tried_urls)}"
            item['수집상태'] = '실패'
            print(f" -> 요약 실패: {fail_reason}")
        results.append(item)

    with open(args.output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok_cnt = sum(1 for r in results if r['수집상태'] == '성공')
    print("2차 수집 완료.")
    print(f"요약 성공: {ok_cnt}/{len(results)}건")
    print(f"입력 파일: {args.input_json}")
    print(f"저장 파일: {args.output_json}")
    print(f"실행시간: {run_id_from_path(args.output_json)}")


if __name__ == '__main__':
    main()
