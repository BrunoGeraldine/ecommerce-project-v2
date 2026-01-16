# E-commerce Project v2 - ETL Google Sheets → Supabase

## 📊 Executive Summary

6-layer ETL pipeline that synchronizes data between Google Sheets and Supabase with robust validation at each step.

**Stack**:
- 🚀 **Main ETL**: `src/validate_and_import.py` (6 layers, 640 lines)
- ⚙️ **Generator**: `src/generate_daily_sales.py` (3 sales/cycle, 222 lines)
- 🤖 **Automation**: GitHub Actions (every 5 minutes)
- 🗄️ **Database**: Supabase (PostgreSQL)
- 📊 **Source**: Google Sheets

---

## 🏗️ Project Structure

```
ecommerce-project-v2/
├── 📁 .github/workflows/
│   ├── sync-daily.yml             # Synchronization (5 min)
│   └── generate-daily-sales.yml   # Sales generation (5 min)
│
├── 📁 credentials/
│   └── credentials.json           # Google Service Account (⚠️ gitignore)
│
├── 📁 src/
│   ├── validate_and_import.py     # 🚀 ETL Setup Configuration Tables (run once only)
│   ├── generate_daily_sales.py    # Continuous generator (3 sales/cycle, 222 lines)
│   └── sync_sheets.py             # 🚀 Main ETL
│
├── test_connection.py             # Diagnostics (58 lines)
├── create_tables.sql              # PostgreSQL Schema
├── requirements.txt               # Python Dependencies
├── ARCHITECTURE.md                # Technical Documentation
├── README.md                      # Setup and Getting Started
├── .env                           # Config (⚠️ gitignore)
└── .gitignore
```

---

## 🚀 Getting Started (5 Steps)

### 1️⃣ Clone Repository
```bash
git clone <your-repo>
cd ecommerce-project-v2
```

### 2️⃣ Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Configure Google Sheets (OAuth2 Service Account)

**In Google Cloud Console**:
1. Create new project
2. Enable APIs: "Google Sheets API" + "Google Drive API"
3. Create "Service Account"
4. Generate JSON key
5. Download to `credentials/credentials.json`
6. **Share** Google Sheets with Service Account email (`seu-sa@seu-projeto.iam.gserviceaccount.com`)

**Expected File**: `credentials/credentials.json`

### 4️⃣ Configure Supabase

1. Create project at [supabase.com](https://supabase.com)
2. Copy `SUPABASE_URL` and `SUPABASE_KEY` (anon-key)
3. Create `.env` file in root:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=seu-anon-key-aqui
SPREADSHEET_NAME=Dados do ecommerce
```

### 5️⃣ Initialize Database

```bash
# 1. Test connection
python test_connection.py
# Expected output: ✅ Google Sheets connected, ✅ Supabase connected

# 2. Create tables (via Supabase Dashboard or run create_tables.sql)
# 3. Populate initial data
python src/validate_and_import.py
```

---

## 📋 How to Use

### For Initial Import (Setup)
```bash
python src/validate_and_import.py
```
✅ Validates data in **6 layers** before inserting  
✅ Shows errors **line by line** (line number, field, expected value)  
✅ Ideal for debugging and troubleshooting

### For Continuous Synchronization
Automatic via GitHub Actions every **5 minutes**:
- `generate_daily_sales.py` → Inserts sales into Sheets
- `sync_sheets.py` → Synchronizes with Supabase

### To Generate New Sales Manually
```bash
python src/generate_daily_sales.py
```
Inserts 3 new sales into Google Sheets (simulates ERP)

### For Diagnostics
```bash
python test_connection.py
```
Check Google Sheets + Supabase connectivity

---

## 🔍 What Happens on Each Execution of `validate_and_import.py`

```
📖 Layer 1: READ
   └─ Reads Google Sheets cell by cell (avoids concatenation)

🧹 Layers 2-4: VALIDATE & CLEAN
   ├─ Normalizes types (text, decimal, int, date)
   ├─ Validates required fields
   ├─ Removes spaces and invalid characters
   └─ Generates list of valid records + errors

🔗 Layer 5: VALIDATE FOREIGN KEYS
   ├─ Loads existing IDs into cache
   ├─ Validates each FK (id_cliente in clientes?, id_produto in produtos?)
   └─ Removes records with invalid FKs

💾 Layer 6: IMPORT
   ├─ Cleans tables (DELETE WHERE pk != '___impossible___')
   ├─ Inserts records in batches of 50
   ├─ If batch fails: individual retry (1 at a time)
   └─ Returns: how many inserted, how many errors

📊 Result:
   ✅ 250 inserted
   ❌ 0 errors
```

---

## 🔧 GitHub Actions Configuration

### Setup (once on GitHub)

1. Open repository on GitHub
2. Settings → Secrets and variables → Actions
3. Add secrets:

| Secret | Value |
|--------|-------|
| `SUPABASE_URL` | `https://seu-projeto.supabase.co` |
| `SUPABASE_KEY` | Your anon-key |
| `SPREADSHEET_NAME` | Exact spreadsheet name |
| `GOOGLE_CREDENTIALS` | credentials.json in base64 |

### Encode credentials.json in Base64

**Linux/Mac**:
```bash
base64 -i credentials/credentials.json
```

**Windows PowerShell**:
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("credentials/credentials.json")) | Set-Clipboard
```

Then paste as value of `GOOGLE_CREDENTIALS` secret on GitHub.

---

## 📊 Data Model

4 main tables with relationships:

| Table | Type | PK | FKs | Description |
|-------|------|----|----|-------------|
| `clientes` | Masters | id_cliente | - | Customer data |
| `produtos` | Masters | id_produto | - | Product catalog |
| `preco_competidores` | Transactional | - | id_produto → produtos | Competitor prices |
| `vendas` | Transactional | id_venda | id_cliente, id_produto | Sales history |

**Relationships**:
```
clientes ──FK── vendas ──FK── produtos ──FK── preco_competidores
```

For complete SQL schema, see `create_tables.sql`

---

## 🚨 Troubleshooting

### ❌ "FileNotFoundError: credentials.json"
**Solution**: Place file in `credentials/credentials.json`

### ❌ "SUPABASE_URL not found"
**Solution**: Create `.env` with `SUPABASE_URL` and `SUPABASE_KEY`

### ❌ "Foreign key constraint violated"
**Solution**: Verify `clientes` and `produtos` were inserted BEFORE `vendas`

### ❌ "Spreadsheet not found"
**Solution**: 
- Confirm exact name in `.env` (case-sensitive)
- Share Google Sheet with Service Account email

### ⚠️ "Script takes too long (> 5 min)"
**Solution**: Check Google Sheets API quota and Supabase connection

### 📊 "Many FK (Foreign Key) errors"
**Solution**: 
- Check customer and product IDs in Google Sheets
- Confirm `clientes` and `produtos` were synchronized first
- Run `test_connection.py` to diagnose

---

## 📚 Complete Documentation

For technical details, see [ARCHITECTURE.md](ARCHITECTURE.md):
- Explanation of 6 layers in detail
- Code examples (all functions)
- Performance benchmarks
- Design patterns
- Error handling
- Complete data flow

---

## 🔐 Security

⚠️ **NEVER commit**:
- `credentials.json` (Google keys)
- `.env` (Supabase keys)
- Any file with tokens/credentials

Check `.gitignore`:
```
credentials.json
.env
__pycache__/
*.pyc
venv/
.venv/
```

---

## 📊 Available Scripts

| Script | Purpose | Time |
|--------|---------|------|
| `src/validate_and_import.py` | 🚀 ETL with 6 layers | 2-3 min |
| `src/generate_daily_sales.py` | Sales generator (3 per cycle) | < 30 sec |
| `src/sync_sheets.py` | Legacy alternative (2 stages) | 1-2 min |
| `test_connection.py` | Connectivity diagnostics | < 5 sec |

---

## 🔗 Useful References

- [Google Cloud Console](https://console.cloud.google.com) - Create Service Account
- [Supabase Dashboard](https://supabase.com/dashboard) - Manage database
- [gspread Docs](https://docs.gspread.org) - Google Sheets API
- [Supabase Python SDK](https://supabase.com/docs/reference/python) - Python Client

---

**Last Update**: January 2026  
**Version**: 3.1 (6 Layer ETL with validate_and_import.py)
