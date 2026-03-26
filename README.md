# Sourcesense S2C Platform

> AI-agent procurement pipeline for steel manufacturing. 19 agents. Gemini 2.5 Pro. LangGraph. SQLite.

## Quick Start

```bash
# 1. Install
pip install -r core/requirements.txt

# 2. Create core/.env with your GEMINI_API_KEY
#    (see core/.env.example for template)

# 3. Pre-flight check
python tests/test_preflight.py

# 4. First run — Phase 1 (PR Consolidation)
python graphs/phase1_graph.py

# 5. Full pipeline
python run.py --phase all
```

## What's in each folder

| Folder | Contents |
|--------|---------|
| `core/` | config.py, db.py, state.py, run.py, requirements.txt |
| `agents/` | 21 Python agent files — PR.01 through PO.19 |
| `graphs/` | LangGraph phase graphs + master_graph.py |
| `database/` | s2c_sourcesense.db (688 rows) + setup scripts |
| `docs/` | BUILD_GUIDE, Phase prompts, ER diagram, run guide |
| `tests/` | test_preflight.py — validates DB + schema before running |
| `DMS_Documents/` | Document storage (populated at runtime) |

## Read these first
- `docs/FIRST_RUN_GUIDE.md` — step-by-step setup
- `CONVERSATION_SUMMARY.md` — full project history, decisions, lessons learned
- `docs/BUILD_GUIDE.md` — agent map and DB statistics

## Database snapshot
232 materials · 45 vendors · 10 buyers · 16 pipeline clusters · 688 total rows
