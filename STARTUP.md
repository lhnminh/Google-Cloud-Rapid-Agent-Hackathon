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

---

## Daily startup

## 1. Activate virtual environment

```bash
source .venv/Scripts/activate
```

## 2. Backend + Front End

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

Then 

open 127.0.0.1:8000
