# Google Sheets to Supabase Integration - Complete Documentation



## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Step 1: Google Cloud Platform Setup](#step-1-google-cloud-platform-setup)
5. [Step 2: Google Sheets Configuration](#step-2-google-sheets-configuration)
6. [Step 3: Supabase Project Setup](#step-3-supabase-project-setup)
7. [Step 4: Local Project Configuration](#step-4-local-project-configuration)
8. [Step 5: Testing Connections](#step-5-testing-connections)
9. [Step 6: Database Tables Setup](#step-6-database-tables-setup)
10. [Step 7: Initial Data Import](#step-7-initial-data-import)
11. [Step 8: GitHub Actions Automation](#step-8-github-actions-automation)

---

## Overview

This documentation provides a complete guide to integrate Google Sheets with Supabase (PostgreSQL database) using Python scripts and GitHub Actions for automated daily synchronization.

**Use Case**: E-commerce data management system that:
- Sources data from Google Sheets
- Stores data in Supabase PostgreSQL database
- Automatically syncs data once per day using GitHub Actions

---

## Prerequisites

### Required Accounts
- Google Account (for Google Cloud Platform and Google Sheets)
- Supabase Account (free tier available)
- GitHub Account (for automation)

### Required Software
- Python 3.8 or higher
- Git
- Text editor (VS Code)
- Terminal/Command Prompt

### Required Knowledge
- Basic Python programming
- Basic SQL understanding
- Command line navigation
- Git basics

---

## Architecture

```
┌─────────────────┐
│  Google Sheets  │ (Data Source)
│  "Dados do      │
│   ecommerce"    │
└────────┬────────┘
         │
         │ Daily Sync (GitHub Actions)
         │
         ▼
┌─────────────────┐
│   Python Script │ (Data Processing)
│   sync_sheets.py│
└────────┬────────┘
         │
         │ REST API
         │
         ▼
┌─────────────────┐
│    Supabase     │ (PostgreSQL Database)
│  projeto-       │
│  ecommerce-v2   │
└─────────────────┘
```

**Data Flow**:
1. Data is manually entered/updated in Google Sheets
2. GitHub Actions triggers Python script daily at 3 AM UTC
3. Script reads data from Google Sheets via API
4. Script cleans and transforms data
5. Script inserts/updates data in Supabase via REST API

---

## Step 1: Google Cloud Platform Setup

### 1.1 Create New Project

1. **Navigate** to [Google Cloud Console](https://console.cloud.google.com/)
2. **Click** on the project dropdown at the top of the page (next to "Google Cloud")
3. **Click** "NEW PROJECT" button in the top-right corner of the modal
4. **Fill in** the project details:
   - **Project name**: `projeto-ecommerce-sheets` (or your preferred name)
   - **Location**: Leave as default or select your organization
5. **Click** "CREATE"
6. **Wait** 15-30 seconds for project creation
7. **Verify** the new project is selected in the top dropdown

### 1.2 Enable Google Sheets API

1. **Open** the navigation menu (☰ hamburger icon, top-left)
2. **Navigate** to: `APIs & Services` → `Library`
3. **Type** in the search bar: `Google Sheets API`
4. **Click** on the "Google Sheets API" result
5. **Click** the blue "ENABLE" button
6. **Wait** for the API to be enabled (you'll see a success message)

### 1.3 Enable Google Drive API

1. **Stay** in `APIs & Services` → `Library`
2. **Click** the back arrow or search again
3. **Type** in the search bar: `Google Drive API`
4. **Click** on the "Google Drive API" result
5. **Click** the blue "ENABLE" button
6. **Wait** for confirmation

### 1.4 Create Service Account

1. **Navigate** to: `APIs & Services` → `Credentials` (left sidebar)
2. **Click** "+ CREATE CREDENTIALS" button (top of page)
3. **Select** "Service account" from the dropdown
4. **Fill in** the service account details:
   - **Service account name**: `sheets-sync-bot`
   - **Service account ID**: (auto-generated, leave as is)
   - **Description**: `Bot for syncing Google Sheets with Supabase`
5. **Click** "CREATE AND CONTINUE"
6. **Step 2 - Grant access** (Optional):
   - **Role**: You can leave this blank or select "Editor"
7. **Click** "CONTINUE"
8. **Step 3 - Grant users access** (Optional):
   - Leave blank
9. **Click** "DONE"

### 1.5 Download Service Account Credentials

1. **Locate** your service account in the "Service Accounts" section
   - Email format: `sheets-sync-bot@projeto-ecommerce-sheets.iam.gserviceaccount.com`
2. **Click** on the service account email (blue link)
3. **Navigate** to the "KEYS" tab (top of page)
4. **Click** "ADD KEY" button
5. **Select** "Create new key"
6. **Choose** key type: "JSON"
7. **Click** "CREATE"
8. **Save** the downloaded JSON file securely
   - File name example: `projeto-ecommerce-sheets-abc123def456.json`
   - ⚠️ **IMPORTANT**: This file contains sensitive credentials - never commit to Git!

### 1.6 Copy Service Account Email

1. **Copy** the service account email from the page
   - Format: `sheets-sync-bot@PROJECT_ID.iam.gserviceaccount.com`
2. **Save** this email - you'll need it in the next step

---

## Step 2: Google Sheets Configuration

### 2.1 Prepare Your Spreadsheet

1. **Open** [Google Sheets](https://docs.google.com/spreadsheets/)
2. **Create** or open your spreadsheet named "Dados do ecommerce"
3. **Verify** you have these 4 sheets (tabs):
   - `clientes`
   - `produtos`
   - `preco_competidores`
   - `vendas`

### 2.2 Configure Sheet Headers

Each sheet must have headers in **row 1** with exact column names:

#### Sheet: `clientes`
```
| id_cliente | nome_cliente | estado | pais | data_cadastro |
```

#### Sheet: `produtos`
```
| id_produto | nome_produto | categoria | marca | preco_atual | data_criacao |
```

#### Sheet: `preco_competidores`
```
| id_produto | nome_concorrente | preco_concorrente | data_coleta |
```

#### Sheet: `vendas`
```
| id_venda | data_venda | id_cliente | id_produto | canal_venda | quantidade | preco_unitario |
```

**Important Notes**:
- Headers must be in **lowercase**
- Use **underscores** (_) not spaces
- **No merged cells**
- **No empty rows** between header and data
- Data starts in **row 2**

### 2.3 Share Spreadsheet with Service Account

1. **Click** the green "Share" button (top-right corner)
2. **Paste** the service account email you copied earlier:
   ```
   sheets-sync-bot@PROJECT_ID.iam.gserviceaccount.com
   ```
3. **Set permission** to "Viewer" (read-only access)
4. **Uncheck** "Notify people" option
5. **Click** "Share" or "Send"
6. **Verify** the service account appears in the "People with access" list

### 2.4 Copy Spreadsheet ID

1. **Look at** the spreadsheet URL in your browser:
   ```
   https://docs.google.com/spreadsheets/d/1ABC123xyz_THIS_IS_THE_ID/edit
   ```
2. **Copy** the ID (the long string between `/d/` and `/edit`)
3. **Save** this ID - you'll need it for configuration

---

## Step 3: Supabase Project Setup

### 3.1 Create Supabase Account

1. **Navigate** to [Supabase](https://supabase.com/)
2. **Click** "Start your project" or "Sign in"
3. **Sign up** or log in using:
   - GitHub account (recommended)
   - Or email/password

### 3.2 Create New Project

1. **Click** "New project" button in the dashboard
2. **Select** your organization (or create one)
3. **Fill in** project details:
   - **Name**: `projeto-ecommerce-v2`
   - **Database Password**: Create a strong password
     - ⚠️ **SAVE THIS PASSWORD** - you cannot recover it later
   - **Region**: Choose closest to your location
     - Example: `South America (São Paulo)` for Brazil
     - Example: `East US (North Virginia)` for US East Coast
   - **Pricing Plan**: Free (or select your preferred plan)
4. **Click** "Create new project"
5. **Wait** 2-3 minutes for project initialization

### 3.3 Retrieve API Credentials

1. **Click** the gear icon (⚙️) in the left sidebar to open Settings
2. **Navigate** to: `API` section
3. **Copy** the following credentials:

   **Project URL**:
   ```
   https://your-project-id.supabase.co
   ```
   
   **anon public key**:
   - **Locate**: "Project API keys" section
   - **Find**: `anon` `public`
   - **Click** the copy icon
   - Token starts with: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   
   **service_role key** (secret):
   - **Click** "Reveal" button next to `service_role` `secret`
   - **Copy** the revealed key
   - Token starts with: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - ⚠️ **CRITICAL**: This key has full database access - keep it secret!

4. **Save** all three values securely

---

## Step 4: Local Project Configuration

### 4.1 Create Project Directory Structure

**On macOS/Linux**:
```bash
# Create main project folder
mkdir projeto-ecommerce-v2
cd projeto-ecommerce-v2

# Create subdirectories
mkdir -p .github/workflows
mkdir src
mkdir credentials
```

**On Windows (Command Prompt)**:
```cmd
mkdir projeto-ecommerce-v2
cd projeto-ecommerce-v2
mkdir .github
cd .github
mkdir workflows
cd ..
mkdir src
mkdir credentials
```

**Final structure**:
```
projeto-ecommerce-v2/
├── .github/
│   └── workflows/
├── src/
└── credentials/
```

### 4.2 Place Service Account Credentials

1. **Rename** the downloaded JSON file to: `credentials.json`
2. **Move** the file to: `projeto-ecommerce-v2/credentials/credentials.json`
3. **Verify** the file path is correct

### 4.3 Create Environment Variables File

1. **Create** a file named `.env` in the project root:
   ```
   projeto-ecommerce-v2/.env
   ```

2. **Open** the `.env` file in a text editor

3. **Paste** the following template:
   ```env
   # Google Sheets Configuration
   SPREADSHEET_NAME=Dados do ecommerce
   SPREADSHEET_ID=YOUR_SPREADSHEET_ID_HERE
   
   # Supabase Configuration
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your_anon_public_key_here
   SUPABASE_SERVICE_KEY=your_service_role_key_here
   
   # Environment
   ENVIRONMENT=development
   ```

4. **Replace** the placeholder values:
   - `YOUR_SPREADSHEET_ID_HERE`: Paste the ID from Step 2.4
   - `https://your-project-id.supabase.co`: Paste your Supabase URL
   - `your_anon_public_key_here`: Paste your anon public key
   - `your_service_role_key_here`: Paste your service_role key

5. **Save** the file

### 4.4 Create .gitignore File

1. **Create** a file named `.gitignore` in the project root

2. **Paste** the following content:
   ```gitignore
   # Credentials (NEVER commit!)
   credentials/
   *.json
   .env
   *.key
   *.pem
   
   # Python
   __pycache__/
   *.py[cod]
   *$py.class
   *.so
   .Python
   venv/
   env/
   ENV/
   *.pyc
   
   # IDEs
   .vscode/
   .idea/
   *.swp
   *.swo
   
   # Generated files
   create_tables.sql
   *.log
   
   # OS
   .DS_Store
   Thumbs.db
   ```

3. **Save** the file

### 4.5 Create Python Virtual Environment

**On macOS/Linux**:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# You should see (venv) in your terminal prompt
```

**On Windows (Command Prompt)**:
```cmd
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# You should see (venv) in your prompt
```

**On Windows (PowerShell)**:
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\Activate.ps1

# If you get an error about execution policy, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4.6 Install Python Dependencies

**With virtual environment activated**:
```bash
# Install required packages
pip install gspread oauth2client supabase python-dotenv requests

# Create requirements.txt file
pip freeze > requirements.txt
```

**Expected output**:
```
Successfully installed gspread-5.x.x oauth2client-4.x.x supabase-2.x.x ...
```

### 4.7 Verify Installation

```bash
# Check installed packages
pip list

# You should see:
# gspread
# oauth2client
# supabase
# python-dotenv
# requests
```

---

## Step 5: Testing Connections

### 5.1 Create Connection Test Script

1. **Create** file: `test_connection.py` in the project root

2. **Paste** the following code:

```python
import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client

# Load environment variables
load_dotenv()

print("="*60)
print("🧪 TESTING CONNECTIONS")
print("="*60)

# Test 1: Google Sheets
print("\n1️⃣  Testing Google Sheets Connection...")
try:
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials/credentials.json', 
        scope
    )
    gc = gspread.authorize(creds)
    
    spreadsheet_name = os.getenv('SPREADSHEET_NAME')
    spreadsheet = gc.open(spreadsheet_name)
    
    print(f"   ✅ Connected to spreadsheet: {spreadsheet.title}")
    sheets = [ws.title for ws in spreadsheet.worksheets()]
    print(f"   ✅ Found sheets: {sheets}")
    
    # Verify all required sheets exist
    required_sheets = ['clientes', 'produtos', 'preco_competidores', 'vendas']
    missing = [s for s in required_sheets if s not in sheets]
    
    if missing:
        print(f"   ⚠️  Missing sheets: {missing}")
    else:
        print(f"   ✅ All required sheets present")
    
except FileNotFoundError:
    print("   ❌ credentials.json not found!")
    print("   📍 Expected location: credentials/credentials.json")
except gspread.exceptions.SpreadsheetNotFound:
    print("   ❌ Spreadsheet not found!")
    print("   💡 Check:")
    print("      - Spreadsheet name in .env matches exactly")
    print("      - Service account has access to the spreadsheet")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 2: Supabase
print("\n2️⃣  Testing Supabase Connection...")
try:
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("   ❌ Missing Supabase credentials in .env file")
    else:
        supabase = create_client(supabase_url, supabase_key)
        print(f"   ✅ Connected to Supabase: {supabase_url}")
        print(f"   ✅ API client initialized successfully")
    
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 3: Environment Variables
print("\n3️⃣  Testing Environment Variables...")
required_vars = [
    'SPREADSHEET_NAME',
    'SPREADSHEET_ID',
    'SUPABASE_URL',
    'SUPABASE_KEY',
    'SUPABASE_SERVICE_KEY'
]

all_present = True
for var in required_vars:
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if 'KEY' in var:
            display = value[:20] + '...'
        else:
            display = value
        print(f"   ✅ {var}: {display}")
    else:
        print(f"   ❌ {var}: NOT SET")
        all_present = False

print("\n" + "="*60)
if all_present:
    print("✅ ALL TESTS PASSED - Ready to proceed!")
else:
    print("⚠️  SOME TESTS FAILED - Fix issues before proceeding")
print("="*60)
```

3. **Save** the file

### 5.2 Run Connection Test

```bash
# Make sure virtual environment is activated
# You should see (venv) in your prompt

# Run the test
python test_connection.py
```

### 5.3 Interpret Results

**✅ Success Output**:
```
============================================================
🧪 TESTING CONNECTIONS
============================================================

1️⃣  Testing Google Sheets Connection...
   ✅ Connected to spreadsheet: Dados do ecommerce
   ✅ Found sheets: ['clientes', 'produtos', 'preco_competidores', 'vendas']
   ✅ All required sheets present

2️⃣  Testing Supabase Connection...
   ✅ Connected to Supabase: https://xxx.supabase.co
   ✅ API client initialized successfully

3️⃣  Testing Environment Variables...
   ✅ SPREADSHEET_NAME: Dados do ecommerce
   ✅ SPREADSHEET_ID: 1ABC123xyz...
   ✅ SUPABASE_URL: https://xxx.supabase.co
   ✅ SUPABASE_KEY: eyJhbGciOiJIUzI1NiI...
   ✅ SUPABASE_SERVICE_KEY: eyJhbGciOiJIUzI1NiI...

============================================================
✅ ALL TESTS PASSED - Ready to proceed!
============================================================
```

**❌ Common Errors and Solutions**:

| Error | Solution |
|-------|----------|
| `credentials.json not found` | Verify file is at `credentials/credentials.json` |
| `Spreadsheet not found` | Check service account has access and name matches |
| `Missing Supabase credentials` | Verify `.env` file has all required variables |
| `Module not found` | Run `pip install -r requirements.txt` |

---

## Step 6: Database Tables Setup

### 6.1 Create Setup Script

1. **Create** file: `src/setup_tables.py`
2. **Copy** the complete script from the artifact (provided separately)
3. **Save** the file

### 6.2 Create SQL Manually in Supabase

Since automatic SQL execution may not work, we'll create tables manually:

1. **Open** your Supabase project dashboard
2. **Click** "SQL Editor" in the left sidebar (database icon)
3. **Click** "+ New query" button
4. **Paste** the following SQL:

```sql
-- ============================================================
-- E-COMMERCE DATABASE SCHEMA
-- ============================================================

-- Table: clientes (customers)
CREATE TABLE IF NOT EXISTS clientes (
    id_cliente TEXT PRIMARY KEY,
    nome_cliente TEXT,
    estado TEXT,
    pais TEXT,
    data_cadastro DATE
);

-- Table: produtos (products)
CREATE TABLE IF NOT EXISTS produtos (
    id_produto TEXT PRIMARY KEY,
    nome_produto TEXT,
    categoria TEXT,
    marca TEXT,
    preco_atual DECIMAL(10,2),
    data_criacao DATE
);

-- Table: preco_competidores (competitor prices)
CREATE TABLE IF NOT EXISTS preco_competidores (
    id_produto TEXT REFERENCES produtos(id_produto),
    nome_concorrente TEXT,
    preco_concorrente DECIMAL(10,2),
    data_coleta DATE
);

-- Table: vendas (sales)
CREATE TABLE IF NOT EXISTS vendas (
    id_venda TEXT PRIMARY KEY,
    data_venda DATE,
    id_cliente TEXT REFERENCES clientes(id_cliente),
    id_produto TEXT REFERENCES produtos(id_produto),
    canal_venda TEXT,
    quantidade INTEGER,
    preco_unitario DECIMAL(10,2)
);

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_preco_competidores_id_produto 
    ON preco_competidores(id_produto);
    
CREATE INDEX IF NOT EXISTS idx_preco_competidores_data_coleta 
    ON preco_competidores(data_coleta);
    
CREATE INDEX IF NOT EXISTS idx_vendas_data_venda 
    ON vendas(data_venda);
    
CREATE INDEX IF NOT EXISTS idx_vendas_id_cliente 
    ON vendas(id_cliente);
    
CREATE INDEX IF NOT EXISTS idx_vendas_id_produto 
    ON vendas(id_produto);
    
CREATE INDEX IF NOT EXISTS idx_produtos_categoria 
    ON produtos(categoria);
```

5. **Click** "Run" button (or press `Ctrl+Enter` / `Cmd+Enter`)
6. **Wait** for success message: "Success. No rows returned"

### 6.3 Verify Tables Created

1. **Click** "Table Editor" in the left sidebar
2. **Verify** you see 4 tables:
   - ✅ `clientes`
   - ✅ `produtos`
   - ✅ `preco_competidores`
   - ✅ `vendas`

3. **Click** on each table to view structure
4. **Verify** column names match your Google Sheets headers

---

## Step 7: Initial Data Import

### 7.1 Create Import Script

1. **Create** file: `src/import_data.py`
2. **Paste** the import script (provided in previous response)
3. **Save** the file

### 7.2 Run Initial Import

```bash
# Activate virtual environment if not already active
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Run import
python src/import_data.py
```

### 7.3 Monitor Import Progress

**Expected output**:
```
======================================================================
📊 IMPORTING DATA FROM GOOGLE SHEETS
======================================================================

======================================================================
📥 Importing: clientes → clientes
======================================================================
✓ Headers: ['id_cliente', 'nome_cliente', 'estado', 'pais', 'data_cadastro']
✓ Rows: 150
✓ Valid records: 150

  ✓ Batch 1: 50 records
  ✓ Batch 2: 50 records
  ✓ Batch 3: 50 records

✅ Imported: 150/150 | Errors: 0

[... similar output for other tables ...]

======================================================================
✅ COMPLETED - Total: 500 records imported
======================================================================
```

### 7.4 Verify Data in Supabase

1. **Open** Supabase dashboard
2. **Click** "Table Editor"
3. **Click** on `clientes` table
4. **Verify** you see data rows
5. **Repeat** for other tables

**Verification checklist**:
- [ ] All 4 tables have data
- [ ] Row counts match your Google Sheets
- [ ] Data types are correct (text, numbers, dates)
- [ ] No error messages in import output

---

## Step 8: GitHub Actions Automation

### 8.1 Create Sync Script

1. **Create** file: `sync_sheets.py` in project root
2. **Copy** the sync script provided earlier
3. **Save** the file

### 8.2 Create GitHub Actions Workflow

1. **Create** file: `.github/workflows/sync-sheets-supabase.yml`

2. **Paste** the following:

```yaml
name: Sync Google Sheets to Supabase

on:
  schedule:
    # Runs every day at 3:00 AM UTC
    # Adjust time as needed (use crontab.guru for help)
    - cron: '0 3 * * *'
  
  # Allows manual triggering from Actions tab
  workflow_dispatch:

jobs:
  sync-data:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install gspread oauth2client supabase python-dotenv requests
      
      - name: Create credentials file
        run: |
          mkdir -p credentials
          echo '${{ secrets.GOOGLE_CREDENTIALS }}' > credentials/credentials.json
      
      - name: Run sync script
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SPREADSHEET_NAME: ${{ secrets.SPREADSHEET_NAME }}
        run: |
          python sync_sheets.py
      
      - name: Clean up credentials
        if: always()
        run: |
          rm -rf credentials/
```

3. **Save** the file

### 8.3 Initialize Git Repository

```bash
# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Google Sheets to Supabase integration"
```

### 8.4 Create GitHub Repository

1. **Go to** [GitHub](https://github.com/)
2. **Click** "+" icon (top-right) → "New repository"
3. **Fill in**:
   - **Repository name**: `projeto-ecommerce-v2`
   - **Description**: "Google Sheets to Supabase integration with daily sync"
   - **Visibility**: Private (recommended for credentials safety)
4. **Click** "Create repository"
5. **Don't** initialize with README (we already have files)

### 8.5 Push Code to GitHub

```bash
# Add GitHub remote
git remote add origin https://github.com/BrunoGeraldine/projeto-ecommerce-v2.git

# Push code
git branch -M main
git push -u origin main
```

### 8.6 Configure GitHub Secrets

1. **Go to** your repository on GitHub
2. **Click** "Settings" tab
3. **Click** "Secrets and variables" → "Actions" (left sidebar)
4. **Click** "New repository secret" button

**Create these secrets one by one**:

#### Secret 1: GOOGLE_CREDENTIALS
- **Name**: `GOOGLE_CREDENTIALS`
- **Value**: 
  1. Open `credentials/credentials.json` in text editor
  2. Copy the **entire** JSON content (including all brackets)
  3. Paste into the secret value field
- **Click** "Add secret"

#### Secret 2: SUPABASE_URL
- **Name**: `SUPABASE_URL`
- **Value**: Your Supabase project URL (e.g., `https://xxx.supabase.co`)
- **Click** "Add secret"

#### Secret 3: SUPABASE_KEY
- **Name**: `SUPABASE_KEY`
- **Value**: Your Supabase anon or service_role key
- **Click** "Add secret"

#### Secret 4: SPREADSHEET_NAME
- **Name**: `SPREADSHEET_NAME`
- **Value**: `Dados do ecommerce` (exact name of your spreadsheet)
- **Click** "Add secret"

### 8.7 Test GitHub Actions Manually

1. **Go to** "Actions" tab in your repository
2. **Click** on "Sync Google Sheets to Supabase" workflow (left sidebar)
3. **Click** "Run workflow" dropdown (right side)
4. **Select** branch: `main`
5. **Click** green "Run workflow" button
6. **Wait** for workflow to start (refresh page if needed)
7. **Click** on the running workflow to see logs
8. **Monitor** the execution:
   - ✅ Green checkmarks = success
   - ❌ Red X = failure (click to see error details)

**Expected workflow duration**: 30-60 seconds

### 8.8 Verify Automatic Scheduling

1. The workflow will now run automatically every day at 3:00 AM UTC
2. **To change the schedule**:
   - Edit `.github/workflows/sync-sheets-supabase.yml`
   - Modify the cron expression:
     ```yaml
     - cron: '0 3 * * *'  # 3 AM UTC daily
     ```
   - Use [crontab.guru](https://crontab.guru/) to help create cron expressions
   - Examples:
     - `0 */6 * * *` - Every 6 hours
     - `0 9 * * 1` - Every Monday at 9 AM
     - `0 0 * * *` - Every day at midnight

---
