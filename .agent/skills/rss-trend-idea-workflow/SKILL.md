---
name: rss-trend-idea-workflow
description: "`/rss-trend-idea-workflow -f 10_idea-google-search` Autonomously collects, summarizes, and analyzes current RSS feed trends from a specified folder to propose four highly actionable, popular business ideas via python scripts."
---

# Skill: rss-trend-idea-workflow

This skill executes a two-phase data collection process via Python, utilizing `step1.py` and `step2.py` in the specified folder (default `10_idea-google-search`). It loads RSS feeds from `rss-feeds.json`, processes redirects and summaries, and synthesizes the data into one main summary Markdown file and four deep-dive idea execution Markdown files.

## 사용방법

```txt
/rss-trend-idea-workflow -f [폴더명]
```
기본값: `/rss-trend-idea-workflow -f 10_idea-google-search`

## ⚠️ Prerequisites & Quirks
- **Environment & Encoding (Critical)**: The workspace is on a Win32 system using PowerShell. To prevent `UnicodeEncodeError` during Python prints and file writes, you **must** set the Python IO encoding to UTF-8. 
  - Always prefix your Python execution commands with: `$env:PYTHONIOENCODING="utf-8";`
- **Working Directory**: Always execute the scripts from the workspace root or pass the absolute paths. The Python scripts will look for and save files inside the given `-f` folder.
- **Execution Timeout Restrictions**: `step1.py` tracking redirects and `step2.py` visiting external pages takes significant time (around 3 minutes/180 seconds each). Ensure your bash tool call timeout is sufficiently long (e.g., 300000ms).

## Step-by-Step Execution Guide

### Step 1: 1차 수집 (First Phase Data Collection)
Run `step1.py` located in the folder to fetch the latest 3 items from the feeds defined in `rss-feeds.json`.

- **Command**: 
  ```powershell
  $env:PYTHONIOENCODING="utf-8"; python [폴더명]\step1.py -f [폴더명]
  ```
- **Expected Output**: A JSON file `trends_data_1차_{YYYY-MM-DD_HHMMSS}.json` generated inside the folder.

### Step 2: 2차 수집 (Second Phase Data Summarization)
Run `step2.py` to visit the target original URLs gathered in Step 1.

- **Command**:
  ```powershell
  $env:PYTHONIOENCODING="utf-8"; python [폴더명]\step2.py -f [폴더명]
  ```
- **Expected Output**: A JSON file `trends_data_2차_{YYYY-MM-DD_HHMMSS}.json` generated inside the folder, containing `요약정보` (summary text).

### Step 3: Final Analysis & Markdown Generation
Analyze the generated `trends_data_2차_{YYYY-MM-DD_HHMMSS}.json` output file. Using the collected summaries, generate exactly 5 Markdown files (1 Main File, 4 Detailed Idea Files) directly in the folder, observing the strict business logic from `02_skills\01_트렌드_구글_검색_v2.md`.

#### Content Rules:
1. **Four Unique Ideas**: Propose exactly 4 business ideas targeting different problems/demands, mapped strictly to:
   - **Software**: B2B SaaS, DevTools, Cybersecurity
   - **Data & AI**: LLM Apps, DataOps, Vertical AI, MLOps
   - **IT Services**: Marketplace, Digital Healthcare, Fintech/Insurtech, EdTech
   - **YouTube & Media**: AI Automation, Virtual Human/IP, Interactive, Analytics
2. **Feasibility Scoring**: Score each idea on a 1-5 scale. Include the score and reasoning.
3. **Evidence Mapping**: Every idea must be tied to specific reference RSS Feed titles, links, and summaries.
4. **Execution Time**: The generated Markdown files MUST explicitly state the execution time at the very top of each file in the format `실행시간 : 2026-06-27_125116`. This time can be extracted from the `실행시간` field in the JSON.
5. **Filename Rules**: Idea Markdown files must be named using the format `{실행시간}_idea_{제목}.md` (e.g., `2026-06-27_125116_idea_Main_Summary.md`).

*Note: Write the 5 output Markdown files directly into the specified `-f` folder using the workspace's write tools without overwriting any historical files.*