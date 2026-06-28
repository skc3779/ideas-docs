# RSS Trend Idea Workflow 사용 가이드 (GUIDE_v1.md)

## 개요
`rss-trend-idea-workflow` 스킬은 최신 RSS 트렌드를 수집하고 분석하여 실현 가능성이 높은 비즈니스 아이디어 4가지를 도출하는 완전 자동화 파이프라인입니다. 기존 버전을 개선하여 폴더 지정 방식과 `rss-feeds.json`을 통한 유연한 소스 관리가 가능해졌습니다.

## 사용 방법
```txt
/rss-trend-idea-workflow -f [폴더명]
```
- `-f, --folder` : 작업 대상 폴더 (예: `10_idea-google-search`). 
- 지정하지 않을 경우 기본적으로 `10_idea-google-search` 폴더를 대상으로 작동합니다.

## 작동 프로세스
1. **피드 수집 (Step 1)**: 지정된 폴더 내의 `rss-feeds.json`을 읽어와 `step1.py`가 최신 기사와 트렌드 URL을 1차적으로 수집합니다.
2. **요약 추출 (Step 2)**: 1차 수집된 URL을 `step2.py`가 순회하며 실제 기사 본문을 파싱하고, 120자 이상의 고품질 핵심 요약본을 2차 JSON 파일로 생성합니다.
3. **인사이트 분석 및 마크다운 생성 (Step 3)**: 생성된 2차 JSON 요약 데이터를 AI가 분석하여, 메인 트렌드 분석 보고서 1건과 각기 다른 4개의 비즈니스 아이디어 상세 실행 계획서(총 5개의 Markdown 문서)를 대상 폴더에 생성합니다.

## 디렉토리 구조 예시
작업 대상 폴더(예: `10_idea-google-search`)에는 다음 파일들이 위치해야 합니다.
- `step1.py`: 1차 수집 파이썬 스크립트
- `step2.py`: 2차 요약 파이썬 스크립트
- `rss-feeds.json`: 수집할 피드 목록
- *(이후 자동 생성되는 .json 중간 파일들과 .md 보고서들)*
