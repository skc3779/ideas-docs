"""Step 3 결과물(마크다운 5개) 검증기.

사용 예:
    python .claude/skills/rss-trend-idea-workflow/scripts/check_outputs.py -f 10_idea-google-search
    python .claude/skills/rss-trend-idea-workflow/scripts/check_outputs.py -f 10_idea-google-search -r 2026-07-04_142224

검사 항목
  [FAIL] 파일 5개 규칙: {실행시간}_idea_Main_Summary.md + 카테고리별 1개씩
         ({실행시간}_idea_Software_*.md / _DataAI_* / _ITServices_* / _Media_*)
  [FAIL] 모든 파일 첫 줄이 `실행시간 : {실행시간}`
  [FAIL] 상세 파일마다 실현 가능성 점수(`N / 5`)가 있고 정수 1~5
  [FAIL] 상세 파일마다 2차 JSON에 실제로 존재하는 근거 링크가 1개 이상
  [WARN] 2차 JSON에 없는 링크 인용 (환각 가능성) / 요약 실패 항목을 근거로 인용
종료 코드: FAIL 이 있으면 1, 없으면 0
"""
import sys

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

CATEGORIES = ["Software", "DataAI", "ITServices", "Media"]
URL_RE = re.compile(r"https?://[^\s)\]>\"'|]+")
SCORE_RE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*/\s*5(?:\.0)?(?![\d])")


def parse_args():
    p = argparse.ArgumentParser(description="Step 3 마크다운 결과물 검증")
    p.add_argument("-f", "--folder", required=True, help="대상 폴더")
    p.add_argument("-r", "--run-id", default="", help="실행시간 (미지정 시 최신 2차 JSON의 타임스탬프)")
    return p.parse_args()


def norm_url(u):
    return u.rstrip(".,;:/").replace("://www.", "://")


def main():
    args = parse_args()
    fails, warns = [], []

    jsons = sorted(glob.glob(os.path.join(args.folder, "trends_data_2차_*.json")))
    if args.run_id:
        jsons = [j for j in jsons if args.run_id in os.path.basename(j)]
    if not jsons:
        sys.exit(f"[FAIL] {args.folder} 에서 2차 JSON을 찾지 못했습니다 (run-id={args.run_id or '최신'}).")
    src_json = jsons[-1]
    run_id = args.run_id or re.search(r"(\d{4}-\d{2}-\d{2}_\d{6})", src_json).group(1)

    with open(src_json, encoding="utf-8") as f:
        items = json.load(f)
    if isinstance(items, dict):
        items = items.get("data", [])

    ok_urls, failed_urls = set(), set()
    for it in items:
        failed = it.get("수집상태") == "실패" or str(it.get("요약정보", "")).startswith("실패")
        for key in ("link", "원문링크"):
            if it.get(key):
                (failed_urls if failed else ok_urls).add(norm_url(it[key]))
    known_urls = ok_urls | failed_urls

    print(f"검증 대상: {args.folder} / 실행시간 {run_id}")
    print(f"근거 JSON: {os.path.basename(src_json)} (항목 {len(items)}개)\n")

    md_files = sorted(glob.glob(os.path.join(args.folder, f"{run_id}_idea_*.md")))
    names = [os.path.basename(m) for m in md_files]
    main_name = f"{run_id}_idea_Main_Summary.md"

    # 1) 파일 5개 규칙
    if main_name not in names:
        fails.append(f"메인 파일 없음: {main_name}")
    for cat in CATEGORIES:
        hits = [n for n in names if n.startswith(f"{run_id}_idea_{cat}_")]
        if len(hits) != 1:
            fails.append(f"{cat} 상세 파일이 정확히 1개여야 함 (현재 {len(hits)}개: {hits})")
    extra = [n for n in names if n != main_name and not any(n.startswith(f"{run_id}_idea_{c}_") for c in CATEGORIES)]
    if extra:
        fails.append(f"규칙에 맞지 않는 파일명: {extra}")

    # 2) 파일별 내용 검사
    for path in md_files:
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        if first != f"실행시간 : {run_id}":
            fails.append(f"{name}: 첫 줄이 `실행시간 : {run_id}` 가 아님 (현재: {first[:40]!r})")

        cited = {norm_url(u) for u in URL_RE.findall(text)}
        grounded = cited & known_urls
        unknown = cited - known_urls
        if not grounded:
            fails.append(f"{name}: 2차 JSON에 있는 근거 링크가 하나도 없음")
        if unknown:
            warns.append(f"{name}: JSON에 없는 링크 {len(unknown)}개 → {sorted(unknown)[:3]}")
        bad_evidence = cited & failed_urls
        if bad_evidence:
            warns.append(f"{name}: 요약 실패 항목을 근거로 인용 → {sorted(bad_evidence)[:3]}")

        if name != main_name:
            scores = SCORE_RE.findall(text)
            if not scores:
                fails.append(f"{name}: 실현 가능성 점수(`N / 5`) 표기 없음")
            for s in scores:
                v = float(s)
                if not v.is_integer() or not 1 <= v <= 5:
                    fails.append(f"{name}: 점수는 1~5 정수여야 함 (발견: {s} / 5)")
                    break

    for w in warns:
        print(f"[WARN] {w}")
    for e in fails:
        print(f"[FAIL] {e}")
    if fails:
        print(f"\n결과: FAIL {len(fails)}건, WARN {len(warns)}건 → 위 항목을 수정한 뒤 다시 검증하세요.")
        sys.exit(1)
    print(f"결과: PASS (파일 {len(md_files)}개, WARN {len(warns)}건)")


if __name__ == "__main__":
    main()
