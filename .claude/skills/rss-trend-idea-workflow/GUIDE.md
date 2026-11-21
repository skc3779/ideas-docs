# RSS Trend Idea Workflow 따라하기 가이드 (v2 · Claude Code)

> RSS 피드에서 오늘의 트렌드를 모으고, 그 근거로 **사업 아이디어 4개**를 정리한 보고서 5개를 자동으로 만드는 Claude Code 스킬입니다.
> 이 문서를 위에서 아래로 따라 하면 첫 실행부터 새 피드 추가까지 할 수 있습니다.

---

## 한눈에 보기

```
/rss-trend-idea-workflow 10_idea-google-search
        │
        ├─ ① step1.py   RSS 피드 수집        → trends_data_1차_{시간}.json
        ├─ ② step2.py   원문 방문·요약       → trends_data_2차_{시간}.json
        ├─ ③ Claude     아이디어 분석·작성   → {시간}_idea_*.md × 5
        └─ ④ 검증       check_outputs.py     → PASS / FAIL
```

---

## 따라하기 0. 처음 한 번만 준비하기 (약 2분)

### 0-1. Python 패키지 설치

VS Code 터미널(PowerShell)을 열고 **워크스페이스 루트**(`06_ideas-docs`)에서 실행합니다.

```powershell
pip install -r .claude/skills/rss-trend-idea-workflow/requirements.txt
```

### 0-2. 스킬이 인식되는지 확인

Claude Code 채팅창에 `/`를 입력합니다. 목록에 **`rss-trend-idea-workflow`** 가 보이면 준비가 끝난 것입니다.

> 보이지 않으면 Claude Code를 다시 시작하세요. 스킬은 `.claude/skills/` 폴더에서 자동으로 읽힙니다.

---

## 따라하기 1. 첫 실행 (약 5~8분)

### 1-1. 명령 입력

Claude Code 채팅창에 아래를 입력합니다.

```
/rss-trend-idea-workflow 10_idea-google-search
```

> v1 형식인 `/rss-trend-idea-workflow -f 10_idea-google-search` 도 그대로 동작합니다.
> 폴더명을 생략하면 `10_idea-google-search`를 대상으로 실행합니다.

### 1-2. 진행 화면 읽는 법

| 화면에 보이는 것 | 의미 | 걸리는 시간 |
|---|---|---|
| `Fetching Google 트렌드...` | ① 피드별 최신 기사 수집 | 1~3분 |
| `1차 수집 완료. 총 항목 수: 15` | ① 완료 | |
| `[3/15] 처리 중: ...` → `요약 성공` | ② 기사 원문을 열어 요약 | 1~3분 |
| `요약 성공: 14/15건` | ② 성공률 | |
| `실행시간: 2026-11-21_103226` | **이번 실행의 ID**. 파일 이름에 그대로 쓰입니다 | |
| 마크다운 파일 5개 작성 | ③ Claude가 분석하고 작성 | 2~3분 |
| `결과: PASS` | ④ 규칙 검증 통과 | 수 초 |

> 권한 확인 창이 뜨면 **허용**을 누르세요. 스킬이 자체 스크립트 실행은 미리 허용해 두지만, 환경에 따라 한 번 물어볼 수 있습니다.

### 1-3. 결과 확인

`10_idea-google-search/` 폴더에 다음 파일이 새로 생깁니다.

```
trends_data_1차_2026-11-21_103001.json      ← ① 수집 원본
trends_data_2차_2026-11-21_103226.json      ← ② 요약 포함 (근거 데이터)
2026-11-21_103226_idea_Main_Summary.md      ← ★ 먼저 열어볼 파일
2026-11-21_103226_idea_Software_XXX.md
2026-11-21_103226_idea_DataAI_XXX.md
2026-11-21_103226_idea_ITServices_XXX.md
2026-11-21_103226_idea_Media_XXX.md
```

**`Main_Summary.md` 를 먼저 열어** 다음을 확인하세요.

1. **수집 개요**: 몇 건 중 몇 건이 성공했는지, "데이터 한계"가 있는지
2. **평가표**: 아이디어 4개의 점수(1~5 정수)와 근거 기사 링크
3. 관심 있는 아이디어는 **상세 파일**에서 MVP, 수익 모델, 리스크를 확인

---

## 따라하기 2. 여러 폴더 한 번에 실행하기

```
/rss-trend-idea-workflow 10_idea-google-search 11_idea-geeknews 12_idea-bytebytego
```

전체 폴더(`rss-feeds.json`이 있는 모든 폴더)를 한 번에 실행하려면:

```
/rss-trend-idea-workflow all
```

> 수집은 폴더별로 **동시에** 진행되므로 폴더 5개도 순서대로 돌리는 것보다 빠릅니다.
> 폴더마다 **각자의 실행시간**이 붙습니다. v1에서는 5개 폴더가 같은 시간값을 쓰는 문제가 있었습니다.

### 피드가 적은 폴더는 수집 개수 늘리기

`13_idea-ai-models`처럼 피드가 1개뿐이면 기사가 3건밖에 모이지 않습니다. `-n`으로 피드별 개수를 늘리세요.

```
/rss-trend-idea-workflow 13_idea-ai-models -n 6
```

---

## 따라하기 3. 새 피드 폴더 추가하기

예: Hacker News 기반 폴더 만들기

**① 폴더 만들기**

```powershell
mkdir 15_idea-hackernews
```

**② `15_idea-hackernews/rss-feeds.json` 작성**

```json
{
  "Hacker News": "https://hnrss.org/frontpage",
  "Lobsters": "https://lobste.rs/rss"
}
```

> 피드 이름은 자유롭게 지어도 됩니다. 스킬은 이름이 아니라 **URL로** 피드 종류(Google 트렌드, Google 뉴스, 일반 RSS)를 판별합니다.
> 이제 폴더마다 `step1.py`, `step2.py`를 복사할 필요가 없습니다. 스킬 폴더의 스크립트 하나를 공통으로 씁니다.

**③ 실행**

```
/rss-trend-idea-workflow 15_idea-hackernews
```

---

## 따라하기 4. 스크립트만 직접 실행하기 (선택)

Claude 없이 수집만 하거나 디버깅할 때 사용합니다. 워크스페이스 루트에서 실행하며, PowerShell과 Bash 모두 같은 명령입니다.

```powershell
# ① 1차 수집 (피드별 3건, -n 으로 변경 가능)
python .claude/skills/rss-trend-idea-workflow/scripts/step1.py -f 10_idea-google-search

# ② 2차 요약 (폴더의 최신 1차 파일을 자동 선택)
python .claude/skills/rss-trend-idea-workflow/scripts/step2.py -f 10_idea-google-search

# ④ 보고서 검증 (-r 생략 시 최신 실행시간)
python .claude/skills/rss-trend-idea-workflow/scripts/check_outputs.py -f 10_idea-google-search
```

| 스크립트 | 주요 옵션 |
|---|---|
| `step1.py` | `-f` 폴더, `-n` 피드별 개수(기본 3), `-i` 피드 JSON, `-o` 출력 경로 |
| `step2.py` | `-f` 폴더, `-i` 1차 JSON(생략 시 최신), `-o` 출력 경로 |
| `check_outputs.py` | `-f` 폴더, `-r` 실행시간(생략 시 최신) |

> v1처럼 `$env:PYTHONIOENCODING="utf-8";`를 앞에 붙일 필요가 없습니다.

---

## 문제 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `[ERROR] 필수 패키지 누락: feedparser` | 패키지 미설치 | 따라하기 0-1 실행 |
| `[ERROR] 대상 폴더가 없습니다` | 폴더명 오타 | 폴더명 확인 (`ls`) |
| `[WARN] a16z Blog: 항목 0개` | 피드 URL이 바뀌었거나 차단됨 | 브라우저로 URL을 열어 확인하고 `rss-feeds.json` 수정 |
| `요약 성공: 3/15건`처럼 낮음 | 사이트 차단, JS 렌더링 페이지 | 그대로 진행해도 됩니다. 보고서에 "데이터 한계"로 표시됩니다 |
| `[FAIL] 점수는 1~5 정수여야 함` | 소수점 점수 사용 | Claude가 자동으로 고칩니다. 직접 쓴 경우 정수로 수정 |
| `[WARN] JSON에 없는 링크` | 근거 외 링크 인용 | 근거 링크라면 JSON 링크로 교체하고, 단순 참고 링크면 무시 |
| 기존 파일과 이름 충돌 | 같은 실행시간 재사용 | 스킬이 멈추고 알려줍니다. 수집부터 다시 실행 |

---

## v1 → v2 무엇이 바뀌었나

| 구분 | v1 (`.agent/skills`) | v2 (`.claude/skills`) |
|---|---|---|
| **근거 정확도** | geeknews·Stratechery 등 비-Google 항목의 약 23%(171건 중 40건)가 **무관한 사이트 글**(쇼핑몰, Pinterest 등)로 바뀌어 요약됨 | 피드가 준 원문 링크를 신뢰하고, 재검색은 같은 도메인 안에서만 → 원문 기준 요약 |
| GeekNews 본문 | `<p>`만 읽어 대부분 실패 → 검색 대체 | `<li>` 목록 본문도 읽어 원문 요약 성공 |
| 뉴스레터 잡음 | `Read Online \| Sign Up`, `{{ first_name }}` 포함 | 자동 제거 |
| 실행시간 | "JSON의 실행시간 필드" 지시(필드 없음) → 폴더 간 같은 값 재사용 | step2가 `실행시간:`을 출력하고 폴더마다 고유 |
| 점수 | 소수점, 4.2~4.8에 몰림 | 1~5 정수, 고난도 영역 상한, 근거 4줄 |
| 아이디어 반복 | 직전 실행과 같은 아이디어 반복 | 직전 Main_Summary와 대조, 겹치면 `(후속)` 표시 |
| 결과 검증 | 없음 | `check_outputs.py`가 파일명, 헤더, 점수, 근거 링크를 자동 검사 |
| 인코딩 | `$env:PYTHONIOENCODING` 접두어 필수 (PowerShell 전용) | 스크립트가 직접 처리해 PowerShell·Bash 공통 |
| 피드 판별 | 피드 **이름**에 하드코딩 (`"Google 트렌드"`) | 피드 **URL**로 판별 |
| 스크립트 위치 | 폴더마다 사본 6벌 | 스킬 폴더 1벌 공유 |
| 수집 개수 | 3건 고정 | `-n` 옵션 |
| 실행 단위 | 폴더 1개 | 여러 폴더 또는 `all`, 병렬 수집 |
| 규칙 문서 | 외부 `02_skills/…v2.md` 참조 (CLI 예시가 옛 버전) | 스킬 안 `references/idea-rules.md`에 포함 |

---

## 스킬 폴더 구조

```
.claude/skills/rss-trend-idea-workflow/
├── SKILL.md                  # Claude가 읽는 실행 지침
├── GUIDE.md                  # 이 문서 (사람용 따라하기)
├── requirements.txt          # Python 패키지 목록
├── scripts/
│   ├── step1.py              # ① RSS 수집
│   ├── step2.py              # ② 원문 요약
│   └── check_outputs.py      # ④ 보고서 검증
├── references/
│   └── idea-rules.md         # ③ 아이디어 도출, 점수, 파일 규칙
└── templates/
    ├── main-summary.md       # 메인 보고서 틀
    └── idea-detail.md        # 상세 보고서 틀
```
