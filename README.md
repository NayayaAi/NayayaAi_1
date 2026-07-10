# NayayaAi_1
# ⚖️ NyayaAI — AI-Powered FIR Generation & Legal Management System

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Local%2FAtlas-47A248?style=flat&logo=mongodb&logoColor=white)](https://mongodb.com)
[![SQLite](https://img.shields.io/badge/SQLite-IndiaLaw.db-003B57?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-CDN-06B6D4?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![ReportLab](https://img.shields.io/badge/ReportLab-PDF_Engine-red?style=flat)](https://reportlab.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active_Development-brightgreen)]()
[![FYP](https://img.shields.io/badge/Project_Type-Final_Year_Project-blueviolet)]()

> **Bridging the gap between incident and justice** — An intelligent platform
> for police officers, citizens, lawyers, and judges to file, manage, and analyze
> First Information Reports (FIRs) with AI-assisted legal section mapping.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Project Status](#-project-status)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Screenshots](#-screenshots)
- [System Architecture](#-system-architecture)
- [Folder Structure](#-folder-structure)
- [Installation & Setup](#-installation--setup)
- [Environment Variables](#-environment-variables)
- [API Endpoints](#-api-endpoints)
- [Database Schema](#-database-schema)
- [Usage Guide](#-usage-guide)
- [Deployment](#-deployment)
- [Known Limitations](#-known-limitations)
- [Challenges & Learnings](#-challenges--learnings)
- [Future Improvements](#-future-improvements)
- [Contributors](#-contributors)
- [License](#-license)

---

## 🔍 Overview

**NyayaAI** (*Nyaya* = Justice in Sanskrit) is a full-stack web application built
as a Final Year Project to modernize and digitize the FIR (First Information Report)
filing process in India. The Indian legal system often suffers from delays, ambiguous
legal section mapping, and inaccessible documentation for ordinary citizens.
NyayaAI directly addresses these problems by combining a Python/Flask backend,
dual-database architecture, and a lightweight AI engine — all without relying on
any paid external AI API.

### Problem Statement

- Police officers spend hours manually identifying the correct IPC/BNS sections
  for a given complaint narrative — a process prone to error and inconsistency.
- Citizens have no transparent, centralized access to their filed FIRs or
  case-linked evidence.
- Lawyers and judges lack a searchable, role-specific portal for legal document review.
- Paper-based FIR records are prone to loss, tampering, and slow retrieval.

### What NyayaAI Does

NyayaAI provides a role-based legal platform where:

- **Police** can file structured FIRs with AI-suggested IPC sections and export
  them as official PDFs.
- **Citizens** can register accounts and access a personal dashboard (in development).
- **Lawyers** access a dedicated portal for case file review (in development).
- **Judges** have a specialized view for adjudication support (in development).
- All roles share a built-in **Law Library** covering 8 major Indian legal acts,
  stored offline in a bundled SQLite database.

### Target Users

| Role | Primary Use | Status |
|------|-------------|--------|
| 🛡️ Police Officer | File FIRs, manage evidence, view history | ✅ Fully implemented |
| 👤 Citizen | Lodge complaints, track case status | 🔧 Dashboard in development |
| ⚖️ Lawyer | Review case files and legal documents | 🔧 Dashboard in development |
| 🔨 Judge | Access FIR records for court proceedings | 🔧 Dashboard in development |

---

## 📊 Project Status

| Module | Status | Notes |
|--------|--------|-------|
| Authentication (all roles) | ✅ Complete | Signup, login, logout, bcrypt hashing |
| FIR Generation (FORM IF-1) | ✅ Complete | 9-section form + AI section mapping + PDF |
| FIR History & Detail View | ✅ Complete | Tabular view with expandable detail panel |
| Law Library | ✅ Complete | Browse + search across 8 acts |
| Evidence Locker (upload) | ✅ Complete | PIN-gated, FIR-linked file upload |
| Evidence Locker (retrieval) | ⚠️ Partial | `/api/evidence` GET endpoint not yet implemented |
| Citizen Dashboard | 🔧 In Progress | Placeholder page currently |
| Lawyer Dashboard | 🔧 In Progress | Placeholder page currently |
| Judge Dashboard | 🔧 In Progress | Placeholder page currently |
| Social Login (Google/GitHub) | ⚠️ UI Only | Buttons present; OAuth not yet connected |
| Document Analysis | ⚠️ UI Only | Upload interface present; backend processing planned |
| Multi-language Support | ⚠️ Scaffolded | Code written and commented out; not active |

---

## ✨ Features

### 🤖 AI-Powered Legal Section Engine (`ai_engine.py`)
- Analyzes the complaint narrative and automatically suggests relevant IPC,
  BNS, and IT Act sections.
- Uses **keyword matching + fuzzy string comparison** (`thefuzz`) across
  15+ crime categories: theft, assault, fraud, cybercrime, domestic violence,
  kidnapping, murder, attempt to murder, dowry harassment, trespass, property
  damage, defamation, and bribery.
- Fuzzy threshold: `partial_ratio > 65` — tuned to balance recall vs. precision.
- Special-case handler: lost/stolen document complaints that match no crime
  category are correctly classified as administrative (non-criminal) matters.
- Returns top 3 matched sections to avoid cluttering the FIR.
- Works **100% offline** — no external AI API or internet connection required.

### 📄 FIR Generation — FORM IF-1 Compliant
- 9-section structured form matching the **official Indian police FIR format**.
- All fields: District, Police Station, Year, FIR Number, FIR Date, Occurrence
  (day/date/time), GDR Entry, information type (Written/Oral), place of occurrence,
  complainant details (name, father's/husband's name, DOB, nationality, passport,
  occupation, address), accused details, delay reasons, property particulars,
  and full narrative.
- **Duplicate FIR number detection** — rejects already-used FIR numbers at API level.
- Auto-generated unique FIR IDs based on UTC epoch timestamps.
- Police can override AI-suggested sections with manually entered ones.
- Dynamic **Add Additional Act/Section** rows with act dropdown + section autocomplete.

### 📑 PDF Export
- Generates a formatted, printable PDF for every FIR using **ReportLab**.
- Saved as `generated_firs/FIR_<fir_no>.pdf` and filename stored in MongoDB.

### 🔐 Authentication & Role-Based Access
- Secure registration and login using **bcrypt** password hashing (with per-user salt).
- **4 user roles:** `police`, `citizen`, `lawyer`, `judge`.
- Role-coded unique ID system: `POL001`, `CIT001`, `LAW001`, `JUD001`.
- Police, Lawyer, and Judge require a pre-issued verified ID with enforced
  prefix validation (`POL`, `LAW`, `JUD`) at signup.
- Citizens receive an auto-incremented ID on successful registration.
- Session-based authentication via Flask server-side sessions.
- Post-login redirect routes each role to its appropriate dashboard.

### 🔑 Signup Page — Enhanced UX
- **Visual role selector** — animated card buttons (Police, Citizen, Lawyer, Judge)
  with icon, active glow border, and CSS scale animation on selection.
- **Unique ID field** — hidden by default; slides into view with smooth CSS
  transition only when a role requiring verification is selected.
- **Password strength meter** — 4-bar indicator (Weak → Medium → Strong) that
  scores length, uppercase, numbers, and special characters in real time.
- **Confirm password** validation before form submission.
- **Animated background** — three radial gradient orbs with CSS `drift` animation,
  plus a grid overlay for depth.

### 📁 Evidence Locker
- **PIN-protected access** — modal overlay with blur backdrop prompts for a PIN
  before the evidence module is visible.
- Upload images, PDFs, and video files linked to a specific FIR number.
- Files are saved to `static/uploads/evidence/` with `secure_filename` sanitization.
- Evidence retrieval grid (`/api/evidence`) is scaffolded in `script.js` —
  the corresponding backend endpoint is planned for the next development phase.

### 📚 Law Library
- Browse and search sections from **8 Indian legal acts**:
  IPC, CrPC, NIA, IEA, HMA, CPC, IDA, MVA.
- Full-text keyword search across all act titles and descriptions simultaneously.
- Powered by a bundled offline **SQLite database** (`IndiaLaw.db`, ~1.9 MB) —
  completely offline, no external API dependency.
- Sections load in the active page section (no page reload).

### 🗺️ Dynamic Legal Reference Data
- Auto-populated dropdown of all **31 Indian states and UTs**.
- Dynamic **police station lookup** per district via `/api/police-stations/<district>`.
- Act → Section **autocomplete `<datalist>`** in the FIR form — populated live
  via Fetch API as the user selects an act.

### 📊 FIR History & Detail View
- Paginated FIR history table: FIR No., Date, Time, Complainant, Complaint, Status.
- Click any row to expand a **full detail overlay panel** with all 30+ FIR fields.
- Close button (×) dismisses panel and returns to table view.
- **Refresh** button reloads live data from MongoDB.
- `escapeHtml()` utility prevents XSS in dynamically rendered FIR content.

### 🖥️ Responsive Multi-Section SPA Layout
- Single-page application behavior built entirely in Jinja2 + vanilla JS —
  `showSection()` hides all `<section>` elements and reveals the target one.
- Sidebar navigation with **hover-reveal** behavior (slides in on mouse proximity).
- Mobile hamburger menu with outside-click auto-close.
- **URL deep-linking** via `?section=` query parameter (e.g., `/?section=fir-history`
  after police login redirects directly to the history section).
- Global error banner auto-dismisses after 8 seconds for user-facing API errors.

### 🩺 Health Check
- `GET /health` returns `{"status": "ok", "message": "Nyaya AI engine reachable"}`
  for uptime monitoring and deployment health probes.

---

## 🛠️ Tech Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.12 | Core application language |
| **Flask** | ≥ 3.1.3 | Web framework — modular Blueprint architecture |
| **Flask-CORS** | latest | Cross-Origin Resource Sharing |
| **Flask-WTF** | latest | Form utilities (dependency declared) |
| **Werkzeug** | ≥ 3.1.0 | WSGI toolkit; `secure_filename` for file uploads |

### Databases

| Technology | Role | Data Stored |
|------------|------|-------------|
| **MongoDB** (PyMongo) | Primary operational DB | Users, FIR records |
| **SQLite** (`IndiaLaw.db`) | Offline read-only reference DB | 8 Indian legal acts + operational tables |

### AI / NLP

| Technology | Purpose |
|------------|---------|
| **thefuzz** | Fuzzy string matching for complaint-to-section mapping |
| **python-Levenshtein** | C extension speed-up for fuzzy matching (`thefuzz[speedup]`) |

### Document Generation

| Technology | Purpose |
|------------|---------|
| **ReportLab** | Programmatic PDF generation — official FIR documents |

### Security

| Technology | Purpose |
|------------|---------|
| **bcrypt** | Password hashing with per-user bcrypt salt |
| **Flask Sessions** | Server-side session cookie management |
| **Werkzeug `secure_filename`** | Prevents path traversal in uploaded file names |

### Frontend

| Technology | Source | Purpose |
|------------|--------|---------|
| **Jinja2** | Flask built-in | Server-side HTML templating |
| **Tailwind CSS** | CDN (unpkg) | Utility-first responsive styling |
| **Lucide Icons** | CDN (unpkg) | SVG icon set |
| **Google Fonts** | CDN | Inter · Playfair Display · Syne · DM Sans |
| **Vanilla JavaScript** | Inline / `script.js` | Fetch API, DOM manipulation, SPA routing |

### Reference Data

| File | Size | Contents |
|------|------|---------|
| `IndiaLaw.db` | ~1.9 MB | 8 Indian legal act tables (IPC, CrPC, NIA, IEA, HMA, CPC, IDA, MVA) |
| `act data.pdf` | ~1.6 MB | Source reference PDF of Indian legal acts (offline reference material) |

---

## 📸 Screenshots

> Add actual screenshots to a `docs/screenshots/` folder and update the paths below.

### 🏠 Home / Hero Page
```
┌──────────────────────────────────────────────────────────────────┐
│  ⚖️ NyayaAI                                         [Logout]     │
│                                                                  │
│          AI-Powered FIR Generation System                        │
│     Bridge the gap between incident and justice.                 │
│                    [ Get Started ]                               │
│                                                                  │
│  [⚡ Instant Gen] [⚖️ Sections] [📄 PDF Export] [🛡️ Verified]   │
│                                                                  │
│  ① Submit Incident → ② AI Processing → ③ Review → ④ Download   │
└──────────────────────────────────────────────────────────────────┘
```
![Home Page](docs/screenshots/home.png)

### 📝 FIR Creation Form (FORM IF-1)
```
┌──────────────────────────────────────────────────────────────────┐
│  FORM IF-1 — First Information Report              AI Auto ✨     │
│  ① [District ▾]  [Police Station ▾]  [Year]  [FIR No.]  [Date]  │
│  ② Act & Sections: [Select Act ▾]  [Section No.]  [+ Add More]  │
│  ③ Occurrence: [Day]  [Date]  [Time]  [GDR Entry]               │
│  ④ Type: ○ Written  ○ Oral                                       │
│  ⑤ Place of Occurrence: [Direction]  [Address]                   │
│  ⑥ Complainant: [Name]  [Father's Name]  [DOB]  [Nationality]   │
│  ⑦ Accused   ⑧ Delay Reasons   ⑨ Property Particulars           │
│     Detailed Narrative: [incident description in own words...]   │
│          [ Generate Official FIR ]    [ Clear Form ]             │
└──────────────────────────────────────────────────────────────────┘
```
![FIR Form](docs/screenshots/fir_form.png)

### 🔑 Login Page
```
┌──────────────────────────────────────────────────────────────────┐
│   🔐  Welcome Back  ·  Sign in to continue to your account.      │
│                                                                  │
│   [ 📧  Email Address _______________________________ ]          │
│   [ 🔒  Password ______________ ]        Forgot password?        │
│                                                                  │
│                    [ S I G N  I N ]                              │
│             ——————— or continue with ———————                     │
│           [ 🌐 Google ]         [ 🐙 GitHub ]  ← UI only         │
│           Don't have an account?   Create one                    │
└──────────────────────────────────────────────────────────────────┘
```
![Login Page](docs/screenshots/login.png)

### 📝 Signup / Register Page
```
┌──────────────────────────────────────────────────────────────────┐
│   🔐  Create Account  ·  Join us today — it only takes a minute. │
│        ——————————— Select your role ———————————                  │
│   [ 🛡️ Police ]  [ 👤 Citizen ]  [ ⚖️ Lawyer ]  [ 🔨 Judge ]    │
│   ↳ Active role glows with blue border + scale animation         │
│                                                                  │
│   [Unique ID] ← slides in only for Police / Lawyer / Judge       │
│   [ Full Name ]              [ Email Address ]                   │
│   [ Password ]               [ Confirm Password ]                │
│   ■ ■ □ □  Password strength indicator (Weak/Medium/Strong)      │
│                  [ C R E A T E  A C C O U N T ]                  │
└──────────────────────────────────────────────────────────────────┘
```
![Signup Page](docs/screenshots/signup.png)

### 🗂️ Evidence Locker
```
┌──────────────────────────────────────────────────────────────────┐
│  Evidence Locker  (PIN-Protected)                                │
│  ┌─────────────────────────┐  ┌────────────────────────────────┐  │
│  │  🛡️  Secure Upload       │  │  Stored Evidence               │  │
│  │  FIR Number: _________  │  │  [ Search by FIR... ] [Filter] │  │
│  │  [ Choose File _______ ]│  │                                │  │
│  │  Images, PDFs, Videos   │  │  📁  No evidence found.        │  │
│  │  [ Upload to Case File ]│  │  Upload a file linked to FIR.  │  │
│  └─────────────────────────┘  └────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```
![Evidence Locker](docs/screenshots/evidence_locker.png)

### 📚 Law Library
```
┌──────────────────────────────────────────────────────────────────┐
│  Law Library                                                     │
│  ┌────────────────────┐ ┌──────────────────┐ ┌────────────────┐  │
│  │  Indian Penal Code │ │  CrPC            │ │ Search All Acts│  │
│  │  Complete sections │ │  Procedural laws │ │ [ keyword... ] │  │
│  │  [ Browse IPC ]    │ │  [ Browse CrPC ] │ │  Results ↓     │  │
│  └────────────────────┘ └──────────────────┘ └────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```
![Law Library](docs/screenshots/law_library.png)

---

## 🏗️ System Architecture

### High-Level Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                            CLIENT  BROWSER                            │
│                                                                       │
│  Jinja2 Templates  ·  Tailwind CSS (CDN)  ·  Lucide Icons (CDN)      │
│  Vanilla JS  →  Fetch API (JSON)  →  Flask REST Endpoints             │
│  showSection() SPA router  ·  escapeHtml() XSS guard                 │
└──────────────────────────────┬────────────────────────────────────────┘
                               │  HTTP / HTTPS
┌──────────────────────────────▼────────────────────────────────────────┐
│                         FLASK  APPLICATION                            │
│                                                                       │
│  app.py  — creates Flask app, registers blueprints, makes dirs        │
│  │                                                                    │
│  └── main/__init__.py  →  register_blueprints(app)                    │
│       │                                                               │
│       ├── general_routes.py   GET  /                  (home)          │
│       │                       GET  /health            (uptime probe)  │
│       │                                                               │
│       ├── auth_routes.py      GET/POST  /signup                       │
│       │                       GET/POST  /login                        │
│       │                       GET       /logout                       │
│       │                       GET       /dashboard                    │
│       │                                                               │
│       ├── fir_routes.py       POST  /generate_fir                     │
│       │                       GET   /api/fir-records                  │
│       │                       GET   /api/fir-records/<fir_no>         │
│       │                                                               │
│       ├── evidence_routes.py  POST  /upload_evidence/<fir_no>         │
│       │                       POST  /verify-locker-access             │
│       │                       GET   /api/evidence  ← planned          │
│       │                                                               │
│       └── legal_routes.py     GET  /api/districts                     │
│                                GET  /api/police-stations/<district>   │
│                                GET  /api/acts                         │
│                                GET  /api/sections/<act>               │
│                                GET  /api/search-sections?q=...        │
│                                                                       │
│  ai_engine.py  ← pure Python, no Flask dependency                    │
│  └── analyze_complaint_for_sections(complaint_text)                   │
│       ├── Phase 1: exact keyword scan  (15 crime categories)          │
│       └── Phase 2: fuzzy partial_ratio > 65  (typo tolerance)        │
│            → returns top 3 IPC / IT Act / PoCA sections               │
└──────────┬────────────────────────────────┬──────────────────────────┘
           │                                │
┌──────────▼────────────┐       ┌───────────▼────────────────────────┐
│      MONGODB           │       │       SQLITE  (IndiaLaw.db)         │
│   NyayaAI_DB           │       │                                    │
│   ├── users            │       │  Legal Act Tables (read-only):     │
│   └── fir_records      │       │  IPC · CRPC · NIA · IEA            │
└────────────────────────┘       │  HMA · CPC · IDA · MVA             │
                                 │                                    │
                                 │  Operational Tables:               │
                                 │  fir_records · users               │
                                 │  evidence_files                    │
                                 └────────────────────────────────────┘
```

### 🔐 Authentication Flow

```
User submits  email + password
        │
        ▼
MongoDB  →  find user by email
        │
    Found? ── NO ──→  401  "Invalid credentials"
        │
       YES
        │
        ▼
bcrypt.checkpw(submitted_password, stored_hash)
        │
    Match? ── NO ──→  401  "Invalid credentials"
        │
       YES
        │
        ▼
Write Flask session:
  session['user_id']   = str(user['_id'])
  session['role']      = user['role']
  session['unique_id'] = user['unique_id']
        │
        ▼
Role-based redirect:
  police  → /?section=fir-history
  citizen → /citizen_dashboard
  lawyer  → /lawyer_dashboard
  judge   → /   (general dashboard)
```

### 📄 FIR Generation Flow

```
User fills FORM IF-1  →  clicks "Generate Official FIR"
        │
        ▼
POST /generate_fir  (JSON body)
        │
act_sections provided by police officer?
  ├── YES → use police-entered value
  └── NO  → ai_engine.analyze_complaint_for_sections(narrative)
                ├── Scan 15 keyword categories (exact match)
                ├── Fuzzy partial_ratio > 65  (variant / typo match)
                └── Return top 3 sections
        │
        ▼
Check MongoDB: fir_no already exists?
  └── YES → 400  "FIR number already exists"
        │
        ▼
Generate PDF  →  ReportLab SimpleDocTemplate
  └── saved to  generated_firs/FIR_<fir_no>.pdf
        │
        ▼
Insert document into MongoDB  fir_records
        │
        ▼
Return JSON  { fir_id, fir_no, act_sections, formatted_fir, ... }
        │
        ▼
Frontend:  renders FORM IF-1 formatted preview panel
           scrolls to preview  ·  shows success message
```

---

## 📁 Folder Structure

```
NyayaAI/
│
├── app.py                    ← Flask entry point; factory, blueprint registration,
│                                directory creation, DB initialization
├── ai_engine.py              ← Standalone AI module; fuzzy legal section mapper
├── requirements.txt          ← Python package dependencies
├── IndiaLaw.db               ← SQLite: 8 Indian legal acts reference DB (~1.9 MB)
├── act data.pdf              ← Source reference PDF for Indian legal acts (~1.6 MB)
├── script.js                 ← Evidence upload helper + planned search handler
├── .gitignore                ← Excludes: venv/, __pycache__/, *.pyc, .env
├── README.md
│
├── main/                     ← Core application package
│   ├── __init__.py           ← register_blueprints(app)
│   ├── config.py             ← Constants: INDIAN_DISTRICTS, SAMPLE_POLICE_STATIONS,
│   │                            LEGAL_ACTS, PDF_FOLDER, UPLOAD_FOLDER
│   ├── database.py           ← MongoDB client + SQLite path + table initializers
│   ├── auth_routes.py        ← /signup  /login  /logout  /dashboard
│   ├── fir_routes.py         ← /generate_fir  /api/fir-records  (+ PDF logic)
│   ├── evidence_routes.py    ← /upload_evidence  /verify-locker-access
│   ├── legal_routes.py       ← /api/districts  /api/police-stations
│   │                            /api/acts  /api/sections  /api/search-sections
│   └── general_routes.py     ← /  /health
│
├── templates/                ← Jinja2 HTML templates
│   ├── index.html            ← Main SPA dashboard (FIR form, history, law library,
│   │                            evidence locker, doc analysis, settings sections)
│   ├── login.html            ← Login page (glass-morphism, animated background)
│   ├── signup.html           ← Signup page (role selector, password strength meter)
│   ├── citizen_dashboard.html   ← 🔧 Under construction placeholder
│   ├── lawyer_dashboard.html    ← 🔧 Under construction placeholder
│   ├── judge_dashboard.html     ← 🔧 Under construction placeholder
│   └── evidence_locker.html     ← Standalone evidence page (alternate view)
│
├── static/
│   ├── style.css             ← Global custom styles (imported by signup.html)
│   └── uploads/
│       └── evidence/         ← Uploaded evidence files (auto-created; gitignored)
│
├── generated_firs/           ← Output FIR PDFs (auto-created; gitignored)
│   └── FIR_<fir_no>.pdf
│
├── venv/                     ← Python virtual environment (gitignored)
├── check_db.py               ← Dev utility: inspect SQLite table contents
└── check_fir.py              ← Dev utility: inspect FIR records in MongoDB
```

---

## 🚀 Installation & Setup

### Prerequisites

| Requirement | Minimum Version | Notes |
|-------------|----------------|-------|
| Python | 3.10+ | 3.12 recommended |
| MongoDB | 6.0+ | Local instance or Atlas URI |
| pip | Latest | Bundled with Python 3.10+ |
| Git | Any | For cloning |

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/<your-username>/NyayaAI.git
cd NyayaAI
```

---

### Step 2 — Create and Activate a Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate — Linux / macOS
source venv/bin/activate

# Activate — Windows (Command Prompt)
venv\Scripts\activate.bat

# Activate — Windows (PowerShell)
venv\Scripts\Activate.ps1
```

---

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` contents:
```
flask>=3.1.3
flask-wtf
flask-cors
pymongo
bcrypt
thefuzz[speedup]
reportlab
werkzeug>=3.1.0
```

> `thefuzz[speedup]` installs the optional `python-Levenshtein` C extension for
> faster fuzzy matching. If compilation fails on your system, replace it with
> plain `thefuzz` in `requirements.txt`.

---

### Step 4 — Start MongoDB

```bash
# Linux (systemd)
sudo systemctl start mongod

# macOS (Homebrew)
brew services start mongodb-community

# Manual start (any OS)
mongod --dbpath /path/to/your/data/db
```

> For **MongoDB Atlas**, update the `MongoClient` URI in `main/database.py`:
> ```python
> client = MongoClient("mongodb+srv://<user>:<password>@cluster.mongodb.net/")
> ```

---

### Step 5 — Run the Application

```bash
python app.py
```

**On first launch**, the app automatically:
- Creates `generated_firs/` directory
- Creates `static/uploads/evidence/` directory
- Initializes SQLite tables: `fir_records`, `users`, `evidence_files`
- Connects to MongoDB and initializes `NyayaAI_DB`

**Access the application at:**

| URL | Description |
|-----|-------------|
| `http://localhost:5000/signup` | Create a new account |
| `http://localhost:5000/login` | Login |
| `http://localhost:5000/` | Home dashboard (redirects to signup if unauthenticated) |
| `http://localhost:5000/health` | API health check |

---

### Step 6 — Production (Gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## 🔧 Environment Variables

The current version uses hardcoded configuration values. For production,
move all sensitive values to a `.env` file.

**Install python-dotenv:**
```bash
pip install python-dotenv
```

**Create `.env` in the project root:**
```env
# ── Flask ──────────────────────────────────────────────────────────────────
SECRET_KEY=replace_with_a_random_string_minimum_32_characters_long
FLASK_DEBUG=False
FLASK_PORT=5000

# ── MongoDB ────────────────────────────────────────────────────────────────
# Local:
MONGO_URI=mongodb://127.0.0.1:27017/
# MongoDB Atlas (production):
# MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/

MONGO_DB_NAME=NyayaAI_DB

# ── File Storage ───────────────────────────────────────────────────────────
PDF_FOLDER=generated_firs
UPLOAD_FOLDER=static/uploads/evidence

# ── Evidence Locker ────────────────────────────────────────────────────────
# ⚠️ SECURITY: Store a bcrypt hash of the PIN in production, never plaintext.
LOCKER_PIN=secure@123
```

**Load in `app.py`:**
```python
from dotenv import load_dotenv
import os
load_dotenv()

app.secret_key = os.getenv("SECRET_KEY", "dev_fallback_key")
```

> ⚠️ Ensure `.env` is listed in `.gitignore` — **never commit secrets to version control.**

---

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Body (JSON) | Success Response | Auth |
|--------|----------|-------------|-----------------|------|
| `POST` | `/signup` | `{fullname, email, password, role, unique_id}` | `201 {message, unique_id, role}` | No |
| `POST` | `/login` | `{email, password}` | `200 {message, role, unique_id}` | No |
| `GET` | `/logout` | — | Redirect to `/signup` | Yes |
| `GET` | `/dashboard` | — | HTML dashboard | Yes |

**Signup — unique ID rules:**
- `police` → required, must start with `POL` (e.g., `POL001`)
- `lawyer` → required, must start with `LAW`
- `judge` → required, must start with `JUD`
- `citizen` → auto-assigned, format `CIT001`, `CIT002`, ...

---

### FIR Management

| Method | Endpoint | Body / Params | Success Response | Auth |
|--------|----------|---------------|-----------------|------|
| `POST` | `/generate_fir` | Full FIR JSON object | FIR document + `formatted_fir` string | Yes |
| `GET` | `/api/fir-records` | — | Array of all FIR objects | Yes |
| `GET` | `/api/fir-records/<fir_no>` | URL param | Single FIR object | Yes |

**Minimal `POST /generate_fir` payload:**
```json
{
  "fir_no"    : "DL/2026/001",
  "dist"      : "Delhi",
  "ps"        : "North Delhi PS",
  "year"      : "2026",
  "fir_date"  : "2026-05-24",
  "statement" : "My mobile phone was snatched by two men near the metro station at 6:30 PM."
}
```
> If `act_sections` is omitted or empty, the AI engine analyzes `statement` and
> fills it automatically.

---

### Legal Reference

| Method | Endpoint | Description | Sample Response |
|--------|----------|-------------|----------------|
| `GET` | `/api/districts` | All 31 Indian states / UTs | `["Andhra Pradesh", "Delhi", ...]` |
| `GET` | `/api/police-stations/<district>` | Stations for given district | `["North Delhi PS", ...]` |
| `GET` | `/api/acts` | Available legal act codes | `["IPC", "CRPC", "NIA", ...]` |
| `GET` | `/api/sections/<act>` | First 50 sections of act | `[{"section": "302", "title": "..."}]` |
| `GET` | `/api/search-sections?q=theft` | Keyword search across all acts | `[{"act": "IPC", "section": "379", "title": "..."}]` |

---

### Evidence

| Method | Endpoint | Body | Response | Auth |
|--------|----------|------|----------|------|
| `POST` | `/upload_evidence/<fir_no>` | `multipart/form-data` with `file` | `{message, file_path}` | Yes |
| `POST` | `/verify-locker-access` | `{"pin": "secure@123"}` | `{success: true, message}` | No |
| `GET` | `/api/evidence` | — | Planned — not yet implemented | — |

---

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Home — redirects based on session state |
| `GET` | `/health` | `{"status": "ok", "message": "Nyaya AI engine reachable"}` |

---

## 🗄️ Database Schema

### MongoDB — `NyayaAI_DB`

#### Collection: `users`

```json
{
  "_id"           : "ObjectId  (auto-generated)",
  "fullname"      : "String    — full legal name",
  "email"         : "String    — unique; used as login identifier",
  "password_hash" : "Binary    — 60-byte bcrypt hash",
  "role"          : "String    — police | citizen | lawyer | judge",
  "unique_id"     : "String    — e.g. POL001, CIT003, LAW007, JUD002",
  "created_at"    : "DateTime  — UTC timestamp of registration"
}
```

#### Collection: `fir_records`

```json
{
  "_id"                 : "ObjectId  (auto)",
  "fir_id"              : "String    — UTC epoch-based unique ID",
  "fir_no"              : "String    — human-readable FIR number (unique)",
  "dist"                : "String    — district / state name",
  "ps"                  : "String    — police station name",
  "year"                : "String",
  "fir_date"            : "String    — date FIR was filed",
  "act_sections"        : "String    — AI-generated or police-entered IPC sections",
  "occurrence_day"      : "String",
  "occurrence_date"     : "String",
  "occurrence_time"     : "String",
  "info_received_date"  : "String",
  "info_received_time"  : "String",
  "gdr_entry_no"        : "String    — General Diary Reference entry number",
  "type_of_information" : "String    — Written | Oral",
  "place_of_occurrence" : "String    — composite: direction + address + jurisdiction",
  "complainant_name"    : "String",
  "father_husband_name" : "String",
  "dob"                 : "String",
  "nationality"         : "String",
  "passport_no"         : "String",
  "date_of_issue"       : "String",
  "place_of_issue"      : "String",
  "occupation"          : "String",
  "address"             : "String",
  "details_of_accused"  : "String",
  "reasons_for_delay"   : "String",
  "property_particulars": "String",
  "statement"           : "String    — full complaint narrative",
  "pdf_file"            : "String    — filename e.g. FIR_DL2026001.pdf",
  "status"              : "String    — default: Saved to Police Records",
  "created_at"          : "DateTime  — UTC"
}
```

---

### SQLite — `IndiaLaw.db`

#### Legal Act Tables (one per act: `IPC`, `CRPC`, `NIA`, `IEA`, `HMA`, `CPC`, `IDA`, `MVA`)

```sql
CREATE TABLE IPC (
    Section       TEXT,     -- e.g. "302"
    section_title TEXT,     -- e.g. "Punishment for Murder"
    section_desc  TEXT      -- Full statutory description
);
-- Same structure for: CRPC, NIA, IEA, HMA, CPC, IDA, MVA
```

#### `evidence_files` Table

```sql
CREATE TABLE evidence_files (
    id          INTEGER   PRIMARY KEY AUTOINCREMENT,
    fir_no      TEXT      NOT NULL,
    file_path   TEXT      NOT NULL,
    file_type   TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fir_no) REFERENCES fir_records(fir_no)
);
```

#### `fir_records` Table (SQLite — initialized; MongoDB is the primary store)

```sql
CREATE TABLE fir_records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    fir_no           TEXT UNIQUE NOT NULL,
    dist             TEXT NOT NULL,
    ps               TEXT NOT NULL,
    year             TEXT NOT NULL,
    fir_date         TEXT NOT NULL,
    act_sections     TEXT,
    complainant_name TEXT,
    statement        TEXT NOT NULL,
    status           TEXT DEFAULT 'Active',
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- + 20 additional columns for the complete FIR fields
);
```

---

## 📖 Usage Guide

### Step 1 — Register

1. Open `http://localhost:5000/signup`.
2. Click your **role card** (Police / Citizen / Lawyer / Judge) — it glows blue
   when active.
3. **Police, Lawyer, Judge:** The Unique ID field slides down — enter your
   pre-issued ID with the correct prefix (`POL001`, `LAW003`, `JUD002`).
   **Citizen:** No ID needed — one is assigned automatically.
4. Fill in Full Name, Email, Password (watch the strength bars), and Confirm Password.
5. Click **Create Account** — your assigned Unique ID is shown on success.
   You are redirected to login after 2 seconds.

---

### Step 2 — Login

1. Open `http://localhost:5000/login`.
2. Enter registered email and password, then click **Sign In**.
3. You are automatically routed to your role dashboard:
   - **Police** → Main FIR dashboard (FIR History section pre-loaded)
   - **Citizen** → `/citizen_dashboard` *(under construction)*
   - **Lawyer** → `/lawyer_dashboard` *(under construction)*
   - **Judge** → Main dashboard

---

### Step 3 — File an FIR (Police Role)

1. Click **Create FIR** in the sidebar.
2. **Section 1 — Basic Details:**
   Select District → Police Station auto-populates via API.
   Enter Year, FIR Number (must be unique), and FIR Date.
3. **Section 2 — Act & Sections:**
   - Leave blank → the AI engine will suggest sections from the narrative.
   - Or enter sections manually in the text box.
   - Click **+ Add Additional Act/Section** to add multiple act/section rows.
4. **Section 3 — Occurrence:** Enter day, date, time, and GDR Entry Number.
5. **Section 4 — Info Type:** Select Written or Oral.
6. **Section 5 — Place:** Enter direction/distance and exact address.
7. **Section 6 — Complainant:** Full name, father's name, DOB, nationality,
   passport, occupation, address.
8. **Sections 7–9:** Accused details, delay reasons, property particulars.
9. **Narrative:** Type the full incident description in plain language.
   This text drives the AI section analysis.
10. Click **Generate Official FIR**:
    - A formatted FORM IF-1 preview renders on screen.
    - The record is persisted to MongoDB.
    - A PDF is saved to `generated_firs/`.

---

### Step 4 — View FIR History

1. Click **FIR History** in the sidebar.
2. All filed FIRs appear in a table with key fields.
3. Click any row → a **full detail overlay** shows all 30+ fields.
4. Click **×** to close the detail panel.
5. Click **Refresh History** to reload the latest data from MongoDB.

---

### Step 5 — Browse the Law Library

1. Click **Law Library** in the sidebar.
2. Click **Browse IPC** or **Browse CrPC** to load the first 50 sections.
3. Use the **Search All Acts** text box to keyword-search across all 8 acts
   simultaneously.
4. Results display act code, section number, and title.

---

### Step 6 — Upload Evidence

1. Click **Evidence Locker** in the sidebar.
2. A **PIN prompt modal** appears — enter the access PIN (`secure@123` by default).
3. Click **Unlock**.
4. In the Secure Upload panel:
   - Enter the FIR number to link the evidence.
   - Choose a file (image, PDF, or video).
   - Click **Upload to Case File**.
5. The file is stored at `static/uploads/evidence/<fir_no>_<filename>`.

---

## ☁️ Deployment

### Option A — Gunicorn + Nginx on a Linux VPS

**1. Install Gunicorn**
```bash
pip install gunicorn
```

**2. Create a systemd service (`/etc/systemd/system/nyayaai.service`)**
```ini
[Unit]
Description=NyayaAI Flask Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/NyayaAI
Environment="PATH=/var/www/NyayaAI/venv/bin"
ExecStart=/var/www/NyayaAI/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable nyayaai
sudo systemctl start nyayaai
```

**3. Nginx reverse proxy (`/etc/nginx/sites-available/nyayaai`)**
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias  /var/www/NyayaAI/static/;
        expires 1d;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/nyayaai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**4. HTTPS with Let's Encrypt**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

### Option B — Render.com (Free Tier, Recommended for Demo)

1. Push repository to GitHub (ensure `IndiaLaw.db` is committed).
2. Go to [render.com](https://render.com) → **New Web Service** → Connect repo.
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `gunicorn app:app`
5. Add **Environment Variables** in the Render dashboard (from `.env`).
6. Use **MongoDB Atlas** (free M0 tier) — update `MONGO_URI` accordingly.

---

### Option C — Railway.app

1. Connect GitHub repository to [railway.app](https://railway.app).
2. Railway auto-detects Python and installs `requirements.txt`.
3. **Start Command:** `gunicorn app:app`
4. Add environment variables via the Variables panel.
5. Provision a MongoDB plugin or use an Atlas URI.

---

### Production Checklist

- [ ] `FLASK_DEBUG=False` in production environment
- [ ] Strong random `SECRET_KEY` (32+ characters)
- [ ] MongoDB Atlas with IP allowlist configured
- [ ] `IndiaLaw.db` included in deployment (read-only reference DB)
- [ ] `generated_firs/` and `static/uploads/evidence/` on persistent storage
- [ ] HTTPS enabled via Let's Encrypt or CDN (Cloudflare)
- [ ] Evidence Locker PIN replaced with hashed per-user credential
- [ ] File upload size limits configured in Nginx (`client_max_body_size`)

---

## ⚠️ Known Limitations

| Limitation | Detail | Priority Fix |
|------------|--------|-------------|
| Static evidence locker PIN | `secure@123` is hardcoded and shared across all users | High — replace with per-user hashed PIN |
| No evidence retrieval API | `GET /api/evidence` called in `script.js` but not yet implemented in backend | High |
| Role dashboards incomplete | Citizen, Lawyer, and Judge dashboards show "Page Under Construction" | Medium |
| Social login placeholder | Google and GitHub buttons on login page are UI-only; OAuth not wired | Medium |
| No file type validation | Evidence upload accepts any file type; no MIME check or size limit | High |
| AI is keyword-based | Section suggestions use fuzzy matching, not semantic understanding; may miss complex narratives | Medium |
| No pagination | FIR history loads all records at once — will degrade with large datasets | Medium |
| Document analysis UI-only | Upload interface exists; backend OCR/NLP processing not yet built | Low |

---

## 🧠 Challenges & Learnings

### Technical Challenges

**1. Dual Database Architecture**
Operating MongoDB and SQLite in parallel required careful connection lifecycle
management. Both must fail gracefully at startup — if MongoDB is unreachable,
the app logs a warning and continues (law library and PDF generation still work
via SQLite). Designing `database.py` with no Flask imports kept the data layer
cleanly decoupled from the web layer.

**2. AI Legal Section Mapping Without External APIs**
The core technical challenge of the project was building an accurate
section-suggestion engine with zero cost and no internet dependency.
The solution uses `thefuzz` fuzzy string matching against a curated
15-category keyword dictionary. The critical engineering decision was the
`partial_ratio > 65` threshold — low enough to catch varied phrasing and
minor typos, high enough to avoid irrelevant section suggestions on unrelated
complaint text. A special-case handler cleanly routes "lost document" complaints
away from criminal sections.

**3. Flask Blueprint Modularization**
As the application grew to 15+ endpoints across 5 functional domains, avoiding
circular imports required a strict dependency hierarchy: `database.py` has no
Flask imports; all route blueprints import from `database.py`; `ai_engine.py`
is a pure Python module. This made each module independently testable.

**4. FORM IF-1 Field Consistency**
Maintaining consistency of 30+ FIR fields across four representations
simultaneously — HTML form, JSON API payload, MongoDB document, and ReportLab
PDF — required careful field naming discipline. A mismatch in any one layer
would silently produce blank fields in the final PDF.

**5. SPA-Style Navigation in Server-Rendered Templates**
Building section-switching behavior (hide/show) inside Jinja2 templates without
React or Vue required careful JS state management. The `showSection()` function,
`initSidebar()` for mobile close behavior, and `?section=` URL deep-linking
together reproduce the core SPA navigation pattern entirely in vanilla JS.

**6. Secure File Uploads**
Preventing path traversal attacks via `werkzeug.utils.secure_filename` was the
first step, but the implementation exposed additional gaps: no MIME-type
validation, no maximum file size, and no virus scanning. These are documented
as high-priority items for the next development phase.

### Key Learnings

| Area | Takeaway |
|------|----------|
| **Auth design** | Session-based auth is correct for monolithic Flask apps; JWT becomes necessary for decoupled frontends or horizontal scaling |
| **Database selection** | MongoDB excels for semi-structured, evolving documents (FIRs); SQLite is ideal for read-heavy reference data with fixed schema |
| **Fuzzy NLP** | Edit-distance fuzzy matching is a pragmatic, license-free alternative to LLMs for constrained classification tasks with a defined vocabulary |
| **PDF generation** | ReportLab's `SimpleDocTemplate` + Platypus elements provides sufficient control for legal formatted single-page documents without HTML-to-PDF overhead |
| **Input sanitization** | Every system boundary needs guards — `secure_filename` for uploads, parameterized SQLite queries, `escapeHtml()` in frontend JS for innerHTML |
| **Blueprint architecture** | Splitting by feature domain (auth, fir, evidence, legal) rather than by layer (models/views/controllers) produces more cohesive, navigable code |

---

## 🔮 Future Improvements

| Priority | Feature | Description |
|----------|---------|-------------|
| 🔴 High | **BNS / BNSS Migration** | Add Bharatiya Nyaya Sanhita (BNS 2023) and BNSS tables to replace IPC/CrPC — active from July 2024 |
| 🔴 High | **Evidence Retrieval API** | Implement `GET /api/evidence` to display uploaded files in the evidence grid |
| 🔴 High | **PIN Security** | Replace static shared locker PIN with per-user bcrypt-hashed PIN in MongoDB |
| 🔴 High | **File Upload Validation** | Add MIME type whitelist, max file size (20 MB), and extension allowlist |
| 🟠 Medium | **Role Dashboards** | Complete citizen, lawyer, and judge portal pages |
| 🟠 Medium | **JWT Authentication** | Replace Flask sessions with JWT for stateless scalable auth |
| 🟠 Medium | **LLM Integration** | Local Ollama + Mistral/LLaMA for context-aware complaint analysis |
| 🟠 Medium | **OAuth Social Login** | Wire Google and GitHub OAuth to the existing login page buttons |
| 🟠 Medium | **OTP Email Verification** | Flask-Mail based OTP at signup |
| 🟠 Medium | **Real-Time Notifications** | Flask-SocketIO WebSocket alerts for FIR status changes |
| 🟡 Low | **Admin Panel** | Superuser dashboard for user management and audit logs |
| 🟡 Low | **Multi-Language UI** | Hindi and regional languages — scaffolding already present in `index.html` (commented out) |
| 🟡 Low | **Document OCR Analysis** | Tesseract OCR + spaCy to analyze uploaded evidence PDFs |
| 🟡 Low | **Mobile App** | React Native or Flutter client consuming the existing REST API |
| 🟡 Low | **Encrypted Evidence** | AES-256 encryption for stored evidence files |
| 🟡 Low | **Audit Trail** | Immutable append-only log of FIR modifications for legal admissibility |

---

## 👥 Contributors

| Name | Role | GitHub |
|------|------|--------|
| **Satyam** | Full Stack Developer · AI Engine · Backend Architecture · UI Design | [@satyam99git-hub](https://github.com/satyam99git-hub) |
| *(Add teammate name)* | *(Role)* | *(GitHub handle)* |
| *(Add teammate name)* | *(Role)* | *(GitHub handle)* |

---

*Final Year Project — Computer Science Engineering, 2025–2026*

---

## 📄 License

```
MIT License

Copyright (c) 2026 Team NyayaAI

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

**⚖️ NyayaAI — Empowering citizens with legal intelligence.**

*Built with Python · Flask · MongoDB · SQLite · ReportLab · thefuzz · Tailwind CSS*

© 2026 Team NyayaAI · All Rights Reserved

</div>
