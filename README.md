HR Docs Desktop

Desktop application built with Python and PySide6 to manage employees
disciplinary events (Absence, Late Arrival, Job Abandonment), generate
reports and documents from templates.

------------------------------------------------------------------------

Tech Stack

-   Python 3.12
-   PySide6 (Qt for Desktop)
-   Supabase (Auth + Postgres + Storage)
-   openpyxl (Excel export)
-   python-docx (Document rendering)
-   PyInstaller (Executable build)
-   Inno Setup (Windows Installer)

------------------------------------------------------------------------

Development Setup

1. Install dependencies

PowerShell:

& “C:_USER.exe” -m pip install -U pip & “C:_USER.exe” -m pip install -r
requirements.txt

------------------------------------------------------------------------

2. Environment configuration

Create a .env file in project root:

SUPABASE_URL=your_url_here SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_TEMPLATES_BUCKET=templates

Important: .env is ignored by Git and should NOT be committed.

------------------------------------------------------------------------

3. Run the app locally

PowerShell:

& “C:_USER.exe” app.py

------------------------------------------------------------------------

Build Executable (PyInstaller)

PowerShell:

& “C:_USER.exe” -m PyInstaller --clean –noconfirm --name HRDocs
–windowed --onedir –add-data “.env;.” --add-data "app;app" app.py

After build:

dist/HRDocs/

------------------------------------------------------------------------

Create Installer (Inno Setup)

1.  Install Inno Setup
2.  Open installer.iss
3.  Click Compile

Installer will be generated in:

Output/HRDocs_Setup.exe

That is the file distributed.

------------------------------------------------------------------------

Deployment Flow

feature branch → develop → main → build → installer → client

Never build installer from feature branch.

Always: 1. Merge into develop 2. Test 3. Merge into main 4. Build
installer from main

------------------------------------------------------------------------

Production Notes

-   Supabase anon key is safe to ship (RLS protects data)
-   App is multi-tenant by firm_id
-   .env is bundled into installer for production
-   No user configuration required
