---
name: search-flights
description: |
  Search and compare flight prices using Google Flights data.
  Use when user mentions "搜机票", "search flights", "比价", "flight search", "机票", "航班",
  "cheapest flight", "find flights", "单程", "one way", "往返", "round trip",
  "回国机票", "买票", "订机票", or wants to compare flight prices.
user-invocable: true
allowed-tools:
  - Bash(${CLAUDE_SKILL_DIR}/.venv/bin/python3 ${CLAUDE_SKILL_DIR}/scripts/*)
argument-hint: "<natural language flight search request>"
---

Search and compare flight prices across flexible date ranges, exact dates, or one-way.

Parse the user's input: $ARGUMENTS

The user can describe their needs in **natural language** (Chinese or English). Your job is to understand what they want and convert it to structured parameters for the script.

## Examples of User Input

- `温哥华到北京，6月25日到8月30日，25-45天，最多转一次`
- `7月1号飞北京，30号回来`
- `单程温哥华飞东京，8月25日`
- `Vancouver to Beijing, June 25 to Aug 30, 25-45 days`
- `Find cheapest round trip YVR to PEK in July, about 2 weeks`
- `帮我搜个机票回国` (ambiguous — ask for details)

## Three Search Modes

### 1. Flexible Date Range (compare across dates)
When the user gives a travel window and trip duration range:
```bash
${CLAUDE_SKILL_DIR}/.venv/bin/python3 ${CLAUDE_SKILL_DIR}/scripts/search_flights.py \
  <origin> <destination> \
  --from <YYYY-MM-DD> --to <YYYY-MM-DD> \
  --min-days <N> --max-days <N> \
  [--max-stops <N>] [--top <N>]
```

### 2. Exact Dates (specific departure and return)
When the user specifies exact travel dates:
```bash
${CLAUDE_SKILL_DIR}/.venv/bin/python3 ${CLAUDE_SKILL_DIR}/scripts/search_flights.py \
  <origin> <destination> \
  --depart <YYYY-MM-DD> --return <YYYY-MM-DD> \
  [--max-stops <N>] [--top <N>]
```

### 3. One-Way
When the user wants a one-way flight:
```bash
${CLAUDE_SKILL_DIR}/.venv/bin/python3 ${CLAUDE_SKILL_DIR}/scripts/search_flights.py \
  <origin> <destination> \
  --depart <YYYY-MM-DD> --one-way \
  [--max-stops <N>] [--top <N>]
```

## Parameters

- `origin` / `destination` — IATA code (YVR) or city name (温哥华, Vancouver)
- `--from` / `--to` — Travel window (flexible mode)
- `--min-days` / `--max-days` — Trip duration range (default: 7-30, flexible mode)
- `--depart` — Exact departure date (exact/one-way mode)
- `--return` — Exact return date (exact mode)
- `--one-way` — One-way search flag
- `--max-stops` — 0=direct only, 1=one stop (default: no limit)
- `--top` — Number of detailed results (default: 15)

## Workflow

### Step 1: Parse Input

Extract parameters from the user's natural language input.

**City → IATA mapping** (handled by script, common ones):
温哥华=YVR, 北京=PEK, 上海=PVG, 多伦多=YYZ, 东京=NRT, 香港=HKG, 台北=TPE, 新加坡=SIN, 首尔=ICN, 洛杉矶=LAX, 旧金山=SFO, 纽约=JFK, 伦敦=LHR, 广州=CAN, 深圳=SZX, 成都=CTU, 大阪=KIX, 曼谷=BKK, 悉尼=SYD, 巴黎=CDG, 迪拜=DXB, 西雅图=SEA, 杭州=HGH, 南京=NKG, 厦门=XMN, 重庆=CKG, 武汉=WUH, 西安=XIY, 昆明=KMG

**Date conversion**: Convert Chinese date formats (6月25日 → 2026-06-25). If year is omitted, use current year (or next year if the date has passed).

**Clarification strategy** — ask ONE precise follow-up when needed:

| Missing Info | Action |
|---|---|
| Origin or destination | Must ask |
| Dates | Must ask |
| Trip duration (flexible mode) | Ask, suggest "7-14天?" |
| Max stops | Default: no limit, state in output |

Do NOT ask about passenger count, cabin class, or currency — default to 1 adult, economy, USD, and state these defaults in the output.

### Step 2: Run Search

Run the appropriate command based on the detected mode.

The script runs:
- **Flexible mode**: Phase 1 (coarse date scan) → Phase 2 (detail search on top candidates)
- **Exact mode**: Phase 2 only (detail search for the specific dates)
- **One-way**: Direct one-way flight search

If the script fails with an import error, create the venv:
```bash
cd ${CLAUDE_SKILL_DIR} && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

### Step 3: Present Results

The script outputs a markdown table. Print it directly, then add:

- **Best price**: highlight the cheapest option
- **Price trends**: which weeks or trip lengths are cheaper (flexible mode)
- **Tips**: highlight direct flights if they exist, even if slightly more expensive

End with: "需要调整搜索条件，或者查看更多细节吗？"
