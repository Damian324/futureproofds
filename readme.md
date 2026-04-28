# AI Workflows Dependency Audit

This repo is a lightweight audit to confirm your environment can install all dependencies used across the AI workflows bootcamp projects.

## Requirements
- Python 3.10.x or 3.11.x (this repo enforces `>=3.10,<3.12`)
- Poetry installed

## Install Poetry
**Windows (PowerShell)**:
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

**macOS/Linux**:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

After installation, restart your terminal. If `poetry` is not found:
- **Windows**: Add `%APPDATA%\Python\Scripts` to your system PATH
- **macOS/Linux**: Add `export PATH="$HOME/.local/bin:$PATH"` to your `~/.bashrc` or `~/.zshrc`

## Quick start
```bash
poetry install
```

If Poetry reports an incompatible Python version, point it to a compatible interpreter:
```bash
poetry env use /path/to/python3.11
poetry install
```

## Smoke check
Run the import check:
```bash
poetry run python main.py
```
This checks core runtime dependencies (excludes notebook and viz tooling).

## Git warm-up
Make a tiny change and practice commits (e.g., edit the print line in `main.py`):
```bash
git remote set-url origin <your-new-repo-url>
git add main.py README.md
git commit -m "chore: update audit note"
git push -u origin main
```

If `main` is not the default branch, use:
```bash
git push -u origin master
```
