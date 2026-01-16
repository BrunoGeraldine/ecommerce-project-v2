# Projeto E-commerce v2 - ETL Google Sheets → Supabase

## 📊 Resumo Executivo

Pipeline ETL em **6 camadas** que sincroniza dados entre Google Sheets e Supabase com validação robusta em cada etapa.

**Stack**:
- 🚀 **ETL Principal**: `src/validate_and_import.py` (6 camadas, 640 linhas)
- ⚙️ **Gerador**: `src/generate_daily_sales.py` (3 vendas/ciclo, 222 linhas)
- 🤖 **Automação**: GitHub Actions (a cada 5 minutos)
- 🗄️ **Database**: Supabase (PostgreSQL)
- 📊 **Fonte**: Google Sheets

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

## 🚀 Primeiros Passos (Setup em 5 passos)

### 1️⃣ Clonar repositório
```bash
git clone <seu-repo>
cd ecommerce-project-v2
```

### 2️⃣ Instalar dependências Python
```bash
pip install -r requirements.txt
```

### 3️⃣ Configurar Google Sheets (OAuth2 Service Account)

**No Google Cloud Console**:
1. Criar novo projeto
2. Ativar APIs: "Google Sheets API" + "Google Drive API"
3. Criar "Service Account"
4. Gerar chave JSON
5. Baixar para `credentials/credentials.json`
6. **Compartilhar** Google Sheets com email do Service Account (`seu-sa@seu-projeto.iam.gserviceaccount.com`)

**Arquivo esperado**: `credentials/credentials.json`

### 4️⃣ Configurar Supabase

1. Criar projeto em [supabase.com](https://supabase.com)
2. Copiar `SUPABASE_URL` e `SUPABASE_KEY` (anon-key)
3. Criar arquivo `.env` na raiz:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=seu-anon-key-aqui
SPREADSHEET_NAME=Dados do ecommerce
```

### 5️⃣ Setup inicial do banco

```bash
# 1. Testar conexão
python test_connection.py
# Output esperado: ✅ Google Sheets conectado, ✅ Supabase conectado

# 2. Criar tabelas (via Supabase Dashboard ou rodar create_tables.sql)
# 3. Popular dados iniciais
python src/validate_and_import.py
```

---

## 📋 Como Usar

### Para Importação Inicial (Setup)
```bash
python src/validate_and_import.py
```
✅ Valida dados em **6 camadas** antes de inserir  
✅ Mostra erros **linha por linha** (número da linha, campo, valor esperado)  
✅ Ideal para debug e troubleshooting

### Para Sincronização Contínua
Automático via GitHub Actions a cada **5 minutos**:
- `generate_daily_sales.py` → Insere vendas no Sheets
- `sync_sheets.py` → Sincroniza com Supabase

### Para Gerar Novas Vendas Manualmente
```bash
python src/generate_daily_sales.py
```
Insere 3 novas vendas no Google Sheets (simula ERP)

### Para Diagnóstico
```bash
python test_connection.py
```
Verifica conectividade Google Sheets + Supabase

---

## 🔍 O que Acontece a Cada Execução de `validate_and_import.py`

```
📖 Camada 1: LER
   └─ Lê Google Sheets célula por célula (evita concatenação)

🧹 Camadas 2-4: VALIDAR & LIMPAR
   ├─ Normaliza tipos (text, decimal, int, date)
   ├─ Valida campos obrigatórios
   ├─ Remove espaços e caracteres inválidos
   └─ Gera lista de registros válidos + erros

🔗 Camada 5: VALIDAR FOREIGN KEYS
   ├─ Carrega IDs existentes em cache
   ├─ Valida cada FK (id_cliente em clientes?, id_produto em produtos?)
   └─ Remove registros com FKs inválidas

💾 Camada 6: IMPORTAR
   ├─ Limpa tabelas (DELETE WHERE pk != '___impossible___')
   ├─ Insere registros em lotes de 50
   ├─ Se lote falhar: retry individual (1 por vez)
   └─ Retorna: quantos inseridos, quantos erros

📊 Resultado:
   ✅ 250 inseridos
   ❌ 0 erros
```

---

## 🔧 Configuração GitHub Actions

### Setup (uma vez no GitHub)

1. Abrir repositório no GitHub
2. Settings → Secrets and variables → Actions
3. Adicionar secrets:

| Secret | Valor |
|--------|-------|
| `SUPABASE_URL` | `https://seu-projeto.supabase.co` |
| `SUPABASE_KEY` | Sua anon-key |
| `SPREADSHEET_NAME` | Nome exato da planilha |
| `GOOGLE_CREDENTIALS` | credentials.json em base64 |

### Encodar credentials.json em base64

**Linux/Mac**:
```bash
base64 -i credentials/credentials.json
```

**Windows PowerShell**:
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("credentials/credentials.json")) | Set-Clipboard
```

Depois colar como valor do secret `GOOGLE_CREDENTIALS` no GitHub.

---

## 📊 Modelo de Dados

4 tabelas principais com relacionamentos:

| Tabela | Tipo | PK | FKs | Descrição |
|--------|------|----|----|-----------|
| `clientes` | Mestres | id_cliente | - | Dados de clientes |
| `produtos` | Mestres | id_produto | - | Catálogo de produtos |
| `preco_competidores` | Transacional | - | id_produto → produtos | Preços de concorrentes |
| `vendas` | Transacional | id_venda | id_cliente, id_produto | Histórico de vendas |

**Relacionamentos**:
```
clientes ──FK── vendas ──FK── produtos ──FK── preco_competidores
```

Para schema SQL completo, ver `create_tables.sql`

---

## 🚨 Troubleshooting

### ❌ "FileNotFoundError: credentials.json"
**Solução**: Coloque arquivo em `credentials/credentials.json`

### ❌ "SUPABASE_URL not found"
**Solução**: Crie `.env` com `SUPABASE_URL` e `SUPABASE_KEY`

### ❌ "Foreign key constraint violated"
**Solução**: Verifique se `clientes` e `produtos` foram inseridos ANTES de `vendas`

### ❌ "Spreadsheet not found"
**Solução**: 
- Confirme nome exato em `.env` (case-sensitive)
- Compartilhe Google Sheet com email do Service Account

### ⚠️ "Script demora muito (> 5 min)"
**Solução**: Verifique quota da API Google Sheets e conexão com Supabase

### 📊 "Muitos erros de FK (Foreign Key)"
**Solução**: 
- Verifique IDs de clientes e produtos no Google Sheets
- Confirme que `clientes` e `produtos` foram sincronizados primeiro
- Execute `test_connection.py` para diagnosticar

---

## 📚 Documentação Completa

Para detalhes técnicos, ver [ARCHITECTURE.md](ARCHITECTURE.md):
- Explicação das 6 camadas em detalhes
- Exemplos de código (todas funções)
- Performance benchmarks
- Padrões de design
- Tratamento de erros
- Fluxo de dados completo

---

## 🔐 Segurança

⚠️ **NUNCA commitar**:
- `credentials.json` (chaves do Google)
- `.env` (chaves do Supabase)
- Qualquer arquivo com tokens/credenciais

Verificar `.gitignore`:
```
credentials.json
.env
__pycache__/
*.pyc
venv/
.venv/
```

---

## 📊 Scripts Disponíveis

| Script | Propósito | Tempo |
|--------|-----------|-------|
| `src/validate_and_import.py` | 🚀 ETL com 6 camadas | 2-3 min |
| `src/generate_daily_sales.py` | Gerador de vendas (3 por ciclo) | < 30 seg |
| `src/sync_sheets.py` | Alternativa legada (2 etapas) | 1-2 min |
| `test_connection.py` | Diagnóstico de conectividade | < 5 seg |

---

## 🔗 Referências Úteis

- [Google Cloud Console](https://console.cloud.google.com) - Criar Service Account
- [Supabase Dashboard](https://supabase.com/dashboard) - Gerenciar banco
- [gspread Docs](https://docs.gspread.org) - Google Sheets API
- [Supabase Python SDK](https://supabase.com/docs/reference/python) - Cliente Python

---

**Última atualização**: Janeiro 2026  
**Versão**: 3.1 (6 Camadas ETL com validate_and_import.py)