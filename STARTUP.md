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
# Open .env and fill in your ANTHROPIC_API_KEY
```

---

## Daily startup

## 1. Activate virtual environment

```bash
source .venv/Scripts/activate
```

## 2. Backend

```bash
uvicorn backend.main:app --reload --port 8000
```

## 3. Frontend

```bash
streamlit run frontend/app.py
```
