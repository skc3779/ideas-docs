import json
import requests
from bs4 import BeautifulSoup
import argparse
from datetime import datetime
try:
    from ddgs import DDGS
except Exception:
    from duckduckgo_search import DDGS
import time
import re
from urllib.parse import urlparse

def parse_args():
    now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    default_output = f"trends_data_2차_{now}.json"
    parser = argparse.ArgumentParser(
        description="RSS 2차 수집: 원문 페이지 방문 후 요약 JSON 생성"
    )
    parser.add_argument(
        "-i",
        "--input-json",
        required=True,
        help="1차 수집 결과 JSON 경로",
    )
    parser.add_argument(
        "-o",
        "--output-json",
        default=default_output,
        help="2차 수집 결과 JSON 경로",
    )
    return parser.parse_args()

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
    source = item.get('source', '')
    if source == 'OpenAI Blog':
        return 'openai.com'
    if source == 'TechCrunch AI':
        return 'techcrunch.com'
    if source.startswith('Google') and '뉴스' in source:
        return normalize_domain(item.get('출처도메인', ''))
    return ''


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
        # 기사 본문 후보 우선
        article_node = soup.find('article')
        nodes = article_node.find_all(['p']) if article_node else soup.find_all(['p'])
        text = ' '.join([n.get_text(strip=True) for n in nodes if len(n.get_text(strip=True)) > 20])
        if not text:
            nodes = soup.find_all(['div'])
            text = ' '.join([n.get_text(strip=True) for n in nodes if len(n.get_text(strip=True)) > 40])
        return text, (soup.title.get_text(strip=True) if soup.title else '')
    except Exception as e:
        return '', str(e)


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
            
    sentences = re.split(r'(?<=[.!?다요])\s+', text)
    valid_sentences = []
    seen = set()
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

    if nav_noise_ratio(text) > 0.5:
        return None, "메뉴/네비게이션 텍스트 비중 과다"
            
    # 요약문이 너무 길면 자르기 (적당히 500자 내외)
    if len(summary) > 500:
        summary = summary[:500] + "..."
        
    return summary, "성공"

def main():
    args = parse_args()
    with open(args.input_json, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
        
    items = loaded_data.get("data", loaded_data) if isinstance(loaded_data, dict) else loaded_data
    exec_time = loaded_data.get("실행시간", datetime.now().strftime("%Y-%m-%d_%H%M%S")) if isinstance(loaded_data, dict) else datetime.now().strftime("%Y-%m-%d_%H%M%S")

    results = []
    ddgs = DDGS()

    for i, item in enumerate(items):
        print(f"[{i+1}/{len(items)}] 처리 중: {item['title']}")

        target_url = item.get('원문링크') or item.get('link')
        valid, reason = is_valid_candidate_url(target_url, item)
        if not valid:
            print(f" -> 초기 원문링크 무효: {reason}")
            target_url = None

        attempts = 0
        max_attempts = 3
        success = False
        tried_urls = []
        fail_reason = ""
        summary_text = ""

        current_url = target_url

        while attempts < max_attempts and not success:
            attempts += 1

            if not current_url:
                # 검색으로 URL 찾기
                try:
                    allowed_domain = derive_allowed_domain(item)
                    raw_query = re.sub(r'\s*-\s*[^-]+$', '', item['title'])
                    query = f"site:{allowed_domain} {raw_query}" if allowed_domain else raw_query
                    search_res = ddgs.text(query, max_results=8)
                    time.sleep(1)
                    found = False
                    for r in search_res:
                        candidate = r.get('href', '')
                        if candidate in tried_urls:
                            continue
                        ok, _ = is_valid_candidate_url(candidate, item)
                        if ok:
                            current_url = candidate
                            found = True
                            break
                    if not found and allowed_domain:
                        # 도메인 제한이 너무 강할 수 있어, 한번 더 일반 검색 후 검증
                        search_res = ddgs.text(raw_query, max_results=8)
                        time.sleep(1)
                        for r in search_res:
                            candidate = r.get('href', '')
                            if candidate in tried_urls:
                                continue
                            ok, _ = is_valid_candidate_url(candidate, item)
                            if ok:
                                current_url = candidate
                                found = True
                                break
                    if not found:
                        fail_reason = "대체 URL 검색 실패"
                        break
                except Exception as e:
                    fail_reason = f"검색 에러: {e}"
                    break

            tried_urls.append(current_url)
            print(f" -> 시도 {attempts}: {current_url}")

            ok, invalid_reason = is_valid_candidate_url(current_url, item)
            if not ok:
                fail_reason = invalid_reason
                current_url = None
                continue

            raw_text, page_title = extract_text(current_url)

            # 제목 키워드 최소 2개 교집합 체크
            tokens = title_tokens(item.get('title', ''))
            text_blob = f"{page_title} {raw_text}".lower()
            overlap = sum(1 for t in tokens if t in text_blob)
            if overlap < 2:
                fail_reason = f"제목 키워드 일치 부족({overlap})"
                current_url = None
                continue

            summary, reason = summarize(raw_text)

            if summary:
                success = True
                summary_text = summary
                item['원문링크'] = current_url
            else:
                fail_reason = reason
                current_url = None  # 다음 시도에서 검색하도록

        if success:
            item['요약정보'] = summary_text
            print(" -> 요약 성공")
        else:
            item['요약정보'] = f"실패 사유: {fail_reason}, 시도 URL: {', '.join(tried_urls)}"
            print(f" -> 요약 실패: {fail_reason}")

        results.append(item)

    out_payload = {
        "실행시간": exec_time,
        "data": results
    }
    with open(args.output_json, 'w', encoding='utf-8') as f:
        json.dump(out_payload, f, ensure_ascii=False, indent=2)

    print("2차 수집 완료.")
    print(f"입력 파일: {args.input_json}")
    print(f"저장 파일: {args.output_json}")


if __name__ == '__main__':
    main()
