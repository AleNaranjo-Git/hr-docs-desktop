# HR Docs Desktop

Desktop application built with Python and PySide6 to manage employees  
disciplinary events (Absence, Late Arrival, Job Abandonment), generate  
reports and documents from templates.

---

## Tech Stack

- Python 3.12
- PySide6 (Qt for Desktop)
- Supabase (Auth + Postgres + Storage)
- openpyxl (Excel export)
- python-docx (Document rendering)
- PyInstaller (Executable build)
- Inno Setup (Windows Installer)

---

## Development Setup

### 1. Install dependencies

From the project root:

```bash
python -m pip install -U pip
python -m pip install -r requirements.txt
```

If you have multiple Python versions installed, you may need:

```bash
py -m pip install -r requirements.txt
```

---

### 2. Environment configuration

Create a `.env` file in the project root:

```
SUPABASE_URL=your_url_here
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_TEMPLATES_BUCKET=templates
```

> `.env` is ignored by Git and must NOT be committed.

---

### 3. Run locally

```bash
python app\main.py
```

---

## Build Executable (PyInstaller)

Run from project root:

```bash
python -m PyInstaller --clean --noconfirm --name HRDocs --windowed --onedir --add-data ".env;." --add-data "app;app" app\main.py
```

After build:

```
dist/HRDocs/HRDocs.exe
```

---

## Create Installer (Inno Setup)

1. Install Inno Setup
2. Open `installer.iss`
3. Click **Compile**

Installer output:

```
Output/HRDocs_Setup.exe
```

This is the file distributed to clients.

---

## Deployment Flow

```
feature → develop → main → build → installer → client
```

Never build installer from feature branch.

Always:
1. Merge into `develop`
2. Test
3. Merge into `main`
4. Build installer from `main`

---

## Production Notes

- Supabase anon key is safe to ship (RLS enforces security)
- App is multi-tenant using `firm_id`
- `.env` is bundled into installer
- No user configuration required
