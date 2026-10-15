# Forage-AI
Open-source AI tool that finds GitHub OSS projects from plain-English descriptions and packages them for Windows (.exe or browser shortcut).

## Development

Windows + Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\forage --help
```

Configuration is environment-only: `FORAGE_GITHUB_TOKEN` and `FORAGE_LLM_API_KEY`. Run `forage setup` for step-by-step instructions on creating both.

