---
name: rss-trend-idea-workflow
description: 지정 폴더의 rss-feeds.json에 정의된 RSS 피드에서 최신 기사를 수집·요약(step1/step2 파이썬 스크립트)하고, 그 근거로 Software / Data&AI / IT Services / Media 4개 분야 사업 아이디어 보고서(Main Summary 1개 + 상세 4개 마크다운)를 생성·검증한다. "/rss-trend-idea-workflow 10_idea-google-search", "오늘 트렌드로 아이디어 뽑아줘", "RSS 수집해서 아이디어 정리", "전체 폴더 아이디어 갱신" 같은 요청에 사용한다.
argument-hint: "[폴더명 ... | all] [-n 피드별개수]"
allowed-tools: Bash(python .claude/skills/rss-trend-idea-workflow/scripts/*), PowerShell(python .claude/skills/rss-trend-idea-workflow/scripts/*), Read, Write, Edit, Glob, Grep
---

# RSS Trend Idea Workflow

RSS 피드 수집(Step 1) → 원문 요약(Step 2) → 아이디어 보고서 5개 작성(Step 3) → 검증(Step 4)을 수행한다.
사람용 따라하기 안내는 [GUIDE.md](GUIDE.md)에 있다.

- 스크립트: `.claude/skills/rss-trend-idea-workflow/scripts/` (`step1.py`, `step2.py`, `check_outputs.py`)
- Step 3 규칙: [references/idea-rules.md](references/idea-rules.md) (**Step 3 전에 반드시 읽는다**)
- 출력 템플릿: [templates/main-summary.md](templates/main-summary.md), [templates/idea-detail.md](templates/idea-detail.md)

모든 명령은 **워크스페이스 루트**에서 실행한다. 경로에 `/`를 쓰므로 PowerShell과 Bash 모두에서 그대로 동작한다. 스크립트가 UTF-8 출력을 직접 설정하므로 `$env:PYTHONIOENCODING` 접두어는 필요 없다.

## 0. 인자 해석

입력 인자: `$ARGUMENTS`

- 비어 있으면 대상은 `10_idea-google-search`이다.
- `-f 폴더명` 형식(v1 호환)과 `폴더명` 형식을 모두 받는다. 폴더는 공백으로 구분해 여러 개 줄 수 있다.
- `all`이면 루트 바로 아래에서 `rss-feeds.json`을 가진 폴더 전체가 대상이다. Glob `*/rss-feeds.json`으로 찾는다.
- `-n 숫자`가 있으면 step1.py에 그대로 넘긴다(피드별 수집 개수, 기본값 3). 피드가 1~2개뿐인 폴더(예: `13_idea-ai-models`)는 `-n 5`를 권장한다.
- 대상 폴더가 없거나 `rss-feeds.json`이 없으면 그 폴더는 건너뛰고, 마지막 보고에 사유를 적는다.

## 1~2. 수집 (Step 1 → Step 2)

폴더마다 아래 두 명령을 **순서대로** 실행한다. 둘 다 네트워크 대기 때문에 각각 1~3분이 걸리므로 timeout은 `600000`으로 준다.

```
python .claude/skills/rss-trend-idea-workflow/scripts/step1.py -f {폴더} [-n N]
python .claude/skills/rss-trend-idea-workflow/scripts/step2.py -f {폴더}
```

- 대상 폴더가 여러 개면 폴더별로 `step1 && step2`를 묶은 명령을 **백그라운드로 동시에** 실행해 시간을 줄인다. 같은 폴더의 step1과 step2는 반드시 순서대로 실행한다.
- step2.py는 별도 인자 없이도 그 폴더의 최신 `trends_data_1차_*.json`을 고른다(파일명 기준).
- step2.py 출력의 마지막 줄 `실행시간: YYYY-MM-DD_HHMMSS`를 그 폴더의 **RUN_ID**로 기록한다. RUN_ID는 폴더마다 다르다. 다른 폴더의 RUN_ID를 재사용하거나 직접 만들지 않는다.
- 스크립트를 수정하거나 테스트용 프로그램을 따로 만들지 않는다.
- step1의 총 항목 수가 0이면 그 폴더는 중단하고 보고한다. 피드 URL 오류나 네트워크 문제일 가능성이 높다.
- step2의 `요약 성공: S/N`에서 S가 N의 절반 미만이어도 진행하되, 메인 파일에 "데이터 한계"로 적는다.

## 3. 보고서 작성 (폴더마다)

1. `references/idea-rules.md`와 두 템플릿을 읽는다. 여러 폴더를 처리할 때는 한 번만 읽으면 된다.
2. `{폴더}/trends_data_2차_{RUN_ID}.json`을 Read로 읽는다. `수집상태 == "성공"`인 항목만 근거로 쓴다.
3. 같은 폴더의 직전 `*_idea_Main_Summary.md`(이번 RUN_ID가 아닌 것 중 파일명이 가장 큰 것)를 읽고, 이전 아이디어 4개 이름을 확인한다.
4. 아래 5개 파일을 Write로 `{폴더}/`에 생성한다. 각 파일 첫 줄은 `실행시간 : {RUN_ID}`이다.
   - `{RUN_ID}_idea_Main_Summary.md` (templates/main-summary.md 구조)
   - `{RUN_ID}_idea_Software_{이름}.md`
   - `{RUN_ID}_idea_DataAI_{이름}.md`
   - `{RUN_ID}_idea_ITServices_{이름}.md`
   - `{RUN_ID}_idea_Media_{이름}.md` (상세 4개는 templates/idea-detail.md 구조)
5. 같은 이름의 파일이 이미 있으면 덮어쓰지 말고 멈춘 뒤 사용자에게 알린다.

핵심 규칙(자세한 내용은 idea-rules.md 참고):
- 실현 가능성 점수는 **1~5 정수**로 매긴다. 반도체, 의료 인허가, 금융 라이선스, 하드웨어 양산처럼 진입 장벽이 큰 아이디어는 최대 3점이다. 4개가 모두 같은 점수면 다시 검토한다.
- 근거 링크와 제목은 JSON 값을 그대로 쓰고, 요약에 없는 수치는 지어내지 않는다.
- 4개 아이디어는 서로 다른 문제를 다루고, 직전 실행과 겹치면 `(후속)`을 표시한다.

## 4. 검증

```
python .claude/skills/rss-trend-idea-workflow/scripts/check_outputs.py -f {폴더} -r {RUN_ID}
```

- `[FAIL]`이 있으면 해당 파일을 Edit로 고치고 PASS가 될 때까지 다시 실행한다.
- `[WARN] JSON에 없는 링크`가 나오면 그 링크가 근거로 쓰였는지 확인한다. 근거라면 JSON 링크로 바꾸고, 경쟁사 사이트처럼 단순 참고 링크라면 그대로 둔다.

## 5. 최종 보고 (사용자에게)

폴더별로 다음을 짧게 보고한다.
- RUN_ID, 수집 건수와 요약 성공 건수 (예: `15건 중 14건 성공`)
- 아이디어 4개: 영역, 이름, 점수(정수)
- 생성 파일 5개의 경로 링크와 검증 결과(PASS, WARN 건수)
- 건너뛴 폴더나 데이터 한계가 있으면 그 사유
