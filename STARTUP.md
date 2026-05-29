# Startup

## First-time setup

### 1. Install uv

```bash
python -m pip install uv
```

If `python` isn't found, download Python from https://python.org first.

### 2. Add uv to PATH (Git Bash)

```bash
echo 'export PATH="/c/Users/<your-username>/AppData/Local/Python/pythoncore-3.14-64/Scripts:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Replace `<your-username>` with your Windows username.

### 3. Create virtual environment and install dependencies

```bash
uv venv
source .venv/Scripts/activate
uv pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
# Open .env and fill in your API keys
```

---

## Daily startup

### 1. Activate virtual environment

```bash
source .venv/Scripts/activate
```

### 2. Start the server

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Then open http://localhost:8000 in your browser.
