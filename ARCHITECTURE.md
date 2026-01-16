# Arquitetura - Projeto E-commerce v2

## 📋 Visão Geral

Este projeto implementa um **pipeline ETL em 6 camadas** que sincroniza dados entre Google Sheets e Supabase (PostgreSQL), com geração contínua de vendas simuladas.

**ETL Principal**: `src/validate_and_import.py` (validação robusta em cada camada)
**Gerador de Vendas**: `src/generate_daily_sales.py` (3 vendas/ciclo ≈ 864/dia)

---

## 🏗️ Estrutura do Projeto

```
ecommerce-project-v2/
├── 📁 .github/workflows/
│   ├── sync-daily.yml             # Sincronização (5 min)
│   └── generate-daily-sales.yml   # Geração de vendas (5 min)
│
├── 📁 credentials/
│   └── credentials.json           # Google Service Account (⚠️ gitignore)
│
├── 📁 src/
│   ├── validate_and_import.py     # 🚀 Setup de configuracao das tabelas (rodar uma vez apenas)
│   ├── generate_daily_sales.py    # Gerador contínuo (3 vendas/ciclo, 222 linhas)
│   └── sync_sheets.py             # 🚀 ETL Principal
│
├── test_connection.py             # Diagnóstico (58 linhas)
├── create_tables.sql              # Schema PostgreSQL
├── requirements.txt               # Dependências Python
├── ARCHITECTURE.md                # Documentação técnica (este arquivo)
├── README.md                      # Setup e primeiros passos
├── .env                           # Config (⚠️ gitignore)
└── .gitignore
```

---

## 🔄 Pipeline ETL - 6 Camadas

### **Camada 1: SCHEMA** (Definição)
- Define estrutura esperada por tabela
- Linhas 41-112 em `validate_and_import.py`

### **Camada 2: LIMPEZA** (Transform)
- `clean_text()`, `clean_decimal()`, `clean_integer()`, `clean_date()`
- Linhas 115-223

### **Camada 3: LEITURA SEGURA** (Extract)
- `read_sheet_safe()` - Lê célula por célula
- Linhas 225-285

### **Camada 4: VALIDAÇÃO DE REGISTROS** (Validate)
- `validate_and_clean_row()` - Valida 1 registro
- Linhas 287-372

### **Camada 5: VALIDAÇÃO FK** (Validate FK)
- `validate_foreign_keys()` - Carrega IDs em cache
- `load_existing_ids()` - Cache para performance
- Linhas 374-441

### **Camada 6: IMPORTAÇÃO** (Load)
- `import_with_validation()` - DELETE + INSERT em lotes
- Retry individual se falhar
- Linhas 443-603

---

## 🚀 Scripts Principais

### 1. `src/validate_and_import.py` - ETL Setup 
**Linhas**: 640 | **Quando usar**: Setup, debug, integridade

**Comando**:
```bash
python src/validate_and_import.py
```

**Performance**: 2-3 minutos (11.378+ registros)

---

### 2. `src/generate_daily_sales.py` - Gerador ⚙️
**Linhas**: 222 | **Quando usar**: Simular vendas contínuas

**Características**:
- 3 vendas/ciclo (≈ 864/dia)
- IDs válidos do Supabase
- Canal: loja_fisica ou ecommerce (50/50)
- Preços: preco_atual ± 0-5%

**Comando**:
```bash
python src/generate_daily_sales.py
```

---

### 3. `src/sync_sheets.py` - ⭐ ETL principal e sincronizacao dados
**Linhas**: 408 | **Status**: Manutenção

2 etapas: TRUNCATE CASCADE + INSERT básico

---

### 4. `test_connection.py` - Diagnóstico
**Linhas**: 58 | **Propósito**: Verificar conectividade

```bash
python test_connection.py
```

---

## 🤖 Automação - GitHub Actions

### Workflow 1: `sync-daily.yml`
- Trigger: Cada 3 minutos
- Executa: `sync_sheets.py`
- Sincroniza clientes → produtos → precos → vendas

### Workflow 2: `generate-daily-sales.yml`
- Trigger: Cada 5 minutos
- Executa: `generate_daily_sales.py`

**Segredos necessários**:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SPREADSHEET_NAME`
- `GOOGLE_CREDENTIALS` (credentials.json em base64)

---

## 📊 Modelo de Dados

4 tabelas com FKs:

| Tabela | Tipo | PK | FKs |
|--------|------|----|----|
| clientes | Mestres | id_cliente | - |
| produtos | Mestres | id_produto | - |
| preco_competidores | Transacional | - | id_produto |
| vendas | Transacional | id_venda | id_cliente, id_produto |

**Ordem de sincronização**:
1. clientes
2. produtos
3. preco_competidores
4. vendas

---

## 🔄 Tratamento de Erros & FK

### Problema: Foreign Key Violations
```
❌ Erro: insert or update violates foreign key constraint
✓ 3013/4013 inseridos
❌ Erros: 1000
```

### Soluções Implementadas

#### 1. Validação FK ANTES de inserir (Camada 5)
```python
def validate_foreign_keys(cleaned_data, table_name):
    """Carrega IDs em cache, valida cada FK"""
    valid_ids = load_existing_ids('clientes', 'id_cliente')
    # Filtrar registros com FKs válidas
    return valid_rows, fk_errors
```

#### 2. Cache de IDs para Performance
```python
def load_existing_ids(table_name, id_column):
    """Carrega uma única vez em SET"""
    response = supabase.table(table_name).select(id_column).execute()
    return {record[id_column] for record in response.data}
```

#### 3. Limpeza de Dados (Camada 2)
Remove espaços, caracteres invisíveis, normaliza.

#### 4. Ordem Correta
Tabelas mestres ANTES de transacionais.

#### 5. Retry Individual
Se batch falhar: tenta 1 por 1.

### Resultado Esperado
```
✓ 4013 linhas lidas
✓ 4013 com FKs válidas
✓ 4013/4013 inseridos
❌ Erros: 0
```

---

## 📊 Performance & Benchmarks

Com 11.378+ registros (4 tabelas):

| Operação | Registros | Tempo |
|----------|-----------|-------|
| Leitura Google Sheets | 11.378 | 45-60 seg |
| Validação & Limpeza | 11.378 | 30-45 seg |
| Validação FK (cache) | 11.378 | 20-30 seg |
| DELETE tabelas | - | < 5 seg |
| INSERT em lotes (50) | 11.378 | 60-90 seg |
| **TOTAL** | **11.378** | **2-3 min** |

**Dicas**:
- ❌ Aumentar batch > 50 (timeout)
- ✅ Boa conexão de rede
- ✅ Evitar 2 scripts simultâneos

---

## 🎯 Padrões de Design

1. **6 Camadas Independentes** - Cada uma com responsabilidade única
2. **Validação Progressiva** - Filtrar dados "ruins" cedo
3. **Idempotência** - Executar múltiplas vezes = mesmo resultado
4. **Logging Detalhado** - Contexto em cada erro
5. **Graceful Degradation** - Erros não interrompem sync
6. **Cache para Performance** - IDs de FK carregados uma única vez

---

## 🚨 Monitoramento & Logs

**Sucesso**:
```
✅ IMPORTAÇÃO CONCLUÍDA
  Total inserido: 4013
  Erros: 0
```

**Problema**:
```
❌ ERRO: Foreign key constraint violated
✓ 3013/4013 inseridos
❌ Erros: 1000
```

**Debug**:
1. `python test_connection.py`
2. `python src/validate_and_import.py`
3. Verificar Google Sheets (dados duplicados?)
4. Verificar Supabase Dashboard

---

## 🔍 Troubleshooting

### "FileNotFoundError: credentials.json"
→ Coloque em `credentials/credentials.json`

### "SUPABASE_URL not found"
→ Crie `.env` com variáveis

### "Foreign key constraint violated"
→ Sincronizar na ordem correta: clientes → produtos → preco → vendas

### "Spreadsheet not found"
→ Confirmar nome exato em `.env` (case-sensitive)
→ Compartilhar sheet com Service Account email

### "Script demora > 5 min"
→ Verificar conexão, quota API (120 req/min)

### "Muitos erros de validação"
→ Verificar tipos de dados no Google Sheets (datas, decimais, IDs)

---

## 🔐 Segurança

⚠️ **NUNCA commitar**:
- `credentials.json` (chaves Google)
- `.env` (chaves Supabase)
- Tokens/credenciais

Verificar `.gitignore`:
```
credentials.json
.env
__pycache__/
*.pyc
venv/
```

---

## 📚 Documentação & Links

- **README.md**: Quick-start e primeiros passos
- **create_tables.sql**: Schema PostgreSQL completo
- **requirements.txt**: Dependências com versões

### Referências Externas
- [Google Cloud Console](https://console.cloud.google.com) - Service Account
- [Supabase Dashboard](https://supabase.com/dashboard) - Banco de dados
- [gspread Docs](https://docs.gspread.org) - Google Sheets API Python
- [Supabase Python SDK](https://supabase.com/docs/reference/python)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)

---

**Última atualização**: Janeiro 2026  
**Versão**: 3.1 (6 Camadas ETL com validate_and_import.py)
