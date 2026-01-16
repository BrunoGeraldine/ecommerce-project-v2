# Architecture - E-commerce Project v2

## 📋 Overview

This project implements a **6-layer ETL pipeline** that synchronizes data between Google Sheets and Supabase (PostgreSQL), with continuous generation of simulated sales.

**Main ETL**: `src/validate_and_import.py` (robust validation at each layer)
**Sales Generator**: `src/generate_daily_sales.py` (3 sales/cycle ≈ 864/day)

---

## 🏗️ Project Structure

```
ecommerce-project-v2/
├── 📁 .github/workflows/
│   ├── sync-daily.yml             # Synchronization (3 min)
│   └── generate-daily-sales.yml   # Sales generation (5 min)
│
├── 📁 credentials/
│   └── credentials.json           # Google Service Account (⚠️ gitignore)
│
├── 📁 src/
│   ├── validate_and_import.py     # 🚀 ETL Setup Configuration Tables (run once only)
│   ├── generate_daily_sales.py    # Continuous Generator (3 sales/cycle, 222 lines)
│   └── sync_sheets.py             # 🚀 Main ETL
│
├── test_connection.py             # Diagnostics (58 lines)
├── create_tables.sql              # PostgreSQL Schema
├── requirements.txt               # Python Dependencies
├── ARCHITECTURE.md                # Technical Documentation (this file)
├── README.md                      # Setup and Getting Started
├── .env                           # Config (⚠️ gitignore)
└── .gitignore
```

---

## 🔄 ETL Pipeline - 6 Layers

### **Layer 1: SCHEMA** (Definition)
- Defines expected structure per table
- Lines 41-112 in `validate_and_import.py`

### **Layer 2: CLEANING** (Transform)
- `clean_text()`, `clean_decimal()`, `clean_integer()`, `clean_date()`
- Lines 115-223

### **Layer 3: SAFE READING** (Extract)
- `read_sheet_safe()` - Reads cell by cell
- Lines 225-285

### **Layer 4: RECORD VALIDATION** (Validate)
- `validate_and_clean_row()` - Validates 1 record
- Lines 287-372

### **Layer 5: FK VALIDATION** (Validate FK)
- `validate_foreign_keys()` - Loads IDs into cache
- `load_existing_ids()` - Cache for performance
- Lines 374-441

### **Layer 6: IMPORT** (Load)
- `import_with_validation()` - DELETE + INSERT in batches
- Retry individual if failed
- Lines 443-603

---

## 🚀 Main Scripts

### 1. `src/validate_and_import.py` - ETL Setup 
**Lines**: 640 | **When to use**: Setup, debug, integrity

**Command**:
```bash
python src/validate_and_import.py
```

**Performance**: 2-3 minutes (11,378+ records)

---

### 2. `src/generate_daily_sales.py` - Generator ⚙️
**Lines**: 222 | **When to use**: Simulate continuous sales

**Features**:
- 3 sales/cycle (≈ 864/day)
- Valid IDs from Supabase
- Channel: loja_fisica or ecommerce (50/50)
- Prices: preco_atual ± 0-5%

**Command**:
```bash
python src/generate_daily_sales.py
```

---

### 3. `src/sync_sheets.py` - ⭐ Main ETL and Data Synchronization
**Lines**: 408 | **Status**: Maintenance

2 stages: TRUNCATE CASCADE + basic INSERT

---

### 4. `test_connection.py` - Diagnostics
**Lines**: 58 | **Purpose**: Check connectivity

```bash
python test_connection.py
```

---

## 🤖 Automation - GitHub Actions

### Workflow 1: `sync-daily.yml`
- Trigger: Every 3 minutes
- Executes: `sync_sheets.py`
- Synchronizes clientes → productos → precos → vendas

### Workflow 2: `generate-daily-sales.yml`
- Trigger: Every 5 minutes
- Executes: `generate_daily_sales.py`

**Required Secrets**:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SPREADSHEET_NAME`
- `GOOGLE_CREDENTIALS` (credentials.json in base64)

---

## 📊 Data Model

4 tables with FKs:

| Table | Type | PK | FKs |
|-------|------|----|----|
| clientes | Masters | id_cliente | - |
| produtos | Masters | id_produto | - |
| preco_competidores | Transactional | - | id_produto |
| vendas | Transactional | id_venda | id_cliente, id_produto |

**Synchronization Order**:
1. clientes
2. produtos
3. preco_competidores
4. vendas

---

## 🔄 Error Handling & FK

### Problem: Foreign Key Violations
```
❌ Error: insert or update violates foreign key constraint
✓ 3013/4013 inserted
❌ Errors: 1000
```

### Implemented Solutions

#### 1. FK Validation BEFORE Insert (Layer 5)
```python
def validate_foreign_keys(cleaned_data, table_name):
    """Loads IDs into cache, validates each FK"""
    valid_ids = load_existing_ids('clientes', 'id_cliente')
    # Filter records with valid FKs
    return valid_rows, fk_errors
```

#### 2. ID Cache for Performance
```python
def load_existing_ids(table_name, id_column):
    """Loads once into SET"""
    response = supabase.table(table_name).select(id_column).execute()
    return {record[id_column] for record in response.data}
```

#### 3. Data Cleaning (Layer 2)
Removes spaces, invisible characters, normalizes.

#### 4. Correct Order
Master tables BEFORE transactional.

#### 5. Individual Retry
If batch fails: tries 1 by 1.

### Expected Result
```
✓ 4013 rows read
✓ 4013 with valid FKs
✓ 4013/4013 inserted
❌ Errors: 0
```

---

## 📊 Performance & Benchmarks

With 11,378+ records (4 tables):

| Operation | Records | Time |
|-----------|---------|------|
| Google Sheets Reading | 11,378 | 45-60 sec |
| Validation & Cleaning | 11,378 | 30-45 sec |
| FK Validation (cache) | 11,378 | 20-30 sec |
| DELETE tables | - | < 5 sec |
| INSERT in batches (50) | 11,378 | 60-90 sec |
| **TOTAL** | **11,378** | **2-3 min** |

**Tips**:
- ❌ Increase batch > 50 (timeout)
- ✅ Good network connection
- ✅ Avoid 2 scripts simultaneously

---

## 🎯 Design Patterns

1. **6 Independent Layers** - Each with single responsibility
2. **Progressive Validation** - Filter "bad" data early
3. **Idempotence** - Run multiple times = same result
4. **Detailed Logging** - Context in each error
5. **Graceful Degradation** - Errors don't stop sync
6. **Cache for Performance** - FK IDs loaded once

---

## 🚨 Monitoring & Logs

**Success**:
```
✅ IMPORT COMPLETED
  Total inserted: 4013
  Errors: 0
```

**Problem**:
```
❌ ERROR: Foreign key constraint violated
✓ 3013/4013 inserted
❌ Errors: 1000
```

**Debug**:
1. `python test_connection.py`
2. `python src/validate_and_import.py`
3. Check Google Sheets (duplicate data?)
4. Check Supabase Dashboard

---

## 🔍 Troubleshooting

### "FileNotFoundError: credentials.json"
→ Place in `credentials/credentials.json`

### "SUPABASE_URL not found"
→ Create `.env` with variables

### "Foreign key constraint violated"
→ Synchronize in correct order: clientes → produtos → preco → vendas

### "Spreadsheet not found"
→ Confirm exact name in `.env` (case-sensitive)
→ Share sheet with Service Account email

### "Script takes > 5 min"
→ Check connection, API quota (120 req/min)

### "Many validation errors"
→ Check data types in Google Sheets (dates, decimals, IDs)

---

## 🔐 Security

⚠️ **NEVER commit**:
- `credentials.json` (Google keys)
- `.env` (Supabase keys)
- Tokens/credentials

Check `.gitignore`:
```
credentials.json
.env
__pycache__/
*.pyc
venv/
```

---

## 📚 Documentation & Links

- **README.md**: Quick-start and getting started
- **create_tables.sql**: Complete PostgreSQL schema
- **requirements.txt**: Dependencies with versions

### External References
- [Google Cloud Console](https://console.cloud.google.com) - Service Account
- [Supabase Dashboard](https://supabase.com/dashboard) - Database
- [gspread Docs](https://docs.gspread.org) - Google Sheets API Python
- [Supabase Python SDK](https://supabase.com/docs/reference/python)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)

---

**Last Update**: January 2026  
**Version**: 3.1 (6 Layer ETL with validate_and_import.py)
