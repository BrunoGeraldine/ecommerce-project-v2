# Arquitetura - Projeto E-commerce v2

## 📋 Visão Geral

Este projeto implementa um **pipeline ETL (Extract, Transform, Load)** que sincroniza dados entre Google Sheets e Supabase (PostgreSQL), com suporte a geração automática de vendas diárias.

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Google Sheets   │  →   │   Python ETL     │  →   │    Supabase      │
│  (Dados Mestres) │      │  (Transformação) │      │  (PostgreSQL)    │
└──────────────────┘      └──────────────────┘      └──────────────────┘
                                   ↓
                          ┌──────────────────┐
                          │ GitHub Actions   │
                          │  (Automação 1x/d)│
                          └──────────────────┘
```

---

## 🏗️ Estrutura do Projeto

```
ecommerce-project-v2/
│
├── 📁 .github/
│   └── workflows/
│       └── generate-daily-sales.yml    # Automação diária
│
├── 📁 credentials/
│   └── credentials.json               # Chaves Google Service Account (⚠️ gitignore)
│
├── 📁 src/
│   ├── sync_sheets.py                 # ETL Principal: Sheets → Supabase
│   ├── validate_and_import.py         # Validação + importação dados
│   ├── generate_daily_sales.py        # Gerador diário de vendas (500/dia)
│   ├── generate_daily_sales_20salesday.py   # Versão leve (20/dia)
│   └── generate_daily_sales500salesday.py   # Versão completa (500/dia)
│
├── 📄 create_tables.sql               # Schema do banco (gerado automaticamente)
├── 📄 test_connection.py              # Teste de conectividade
├── 📄 requirements.txt                # Dependências Python
├── 📄 README.md                       # Setup e primeiros passos
├── 📄 ARCHITECTURE.md                 # Este arquivo
├── 📄 .env                            # Variáveis de ambiente (⚠️ gitignore)
└── 📄 .gitignore                      # Arquivos ignorados no git
```


```
ecommerce-project-v2/
│
├── 📁 .github/
│   └── workflows/
|       ├── sync-daily.yml              # Automacao Sheets → Supabase
│       └── generate-daily-sales.yml    # Automação diária → Gera dados na planilha sheets
│
├── 📁 credentials/
│   └── credentials.json               # Chaves Google Service Account (⚠️ gitignore)
│
├── 📁 src/
│   ├── sync_sheets.py                 # ETL Principal: Sheets → Supabase
│   ├── validate_and_import.py         # Validação + importação dados
│   └── generate_daily_sales.py        # Gerador diário de vendas (500/dia)
│
├── 📄 create_tables.sql               # Schema do banco (gerado automaticamente)
├── 📄 test_connection.py              # Teste de conectividade
├── 📄 requirements.txt                # Dependências Python
├── 📄 README.md                       # Setup e primeiros passos
├── 📄 ARCHITECTURE.md                 # Este arquivo
├── 📄 .env                            # Variáveis de ambiente (⚠️ gitignore)
└── 📄 .gitignore                      # Arquivos ignorados no git
```


---

## 🔄 Pipeline ETL

### **Etapa 1: EXTRAÇÃO (Extract)**

**Fonte**: Google Sheets ("Dados do ecommerce")

**O que é extraído**:
- Tabela `clientes`: id_cliente, nome_cliente, estado, país, data_cadastro
- Tabela `produtos`: id_produto, nome_produto, categoria, marca, preço, data_criação
- Tabela `preco_competidores`: id_produto, concorrente, preço, data_coleta
- Tabela `vendas`: id_venda, data, cliente, produto, canal, quantidade, preço unitário

**Como funciona**:
```python
# sync_sheets.py - Etapa de Extração
spreadsheet = gc.open(SPREADSHEET_NAME)  # Autentica com OAuth2
worksheet = spreadsheet.worksheet(sheet_name)
all_values = worksheet.get_all_values()  # Lê toda a planilha
```

**Autenticação**: OAuth2 via Service Account (credenciais.json)

---

### **Etapa 2: TRANSFORMAÇÃO (Transform)**

**Função**: `limpar_valor(valor, nome_coluna)`

Normaliza dados conforme o tipo de coluna:

| Tipo | Transformação | Exemplo |
|------|---|---|
| **Preço** | Remove símbolos, converte `,` para `.`, float | `"R$ 45,50"` → `45.50` |
| **Quantidade** | Extrai dígitos, converte int | `"5 unidades"` → `5` |
| **Data** | Converte para `YYYY-MM-DD` | `"15/01/2026"` → `"2026-01-15"` |
| **Texto** | Normaliza espaços múltiplos | `"São  Paulo"` → `"São Paulo"` |

**Validações**:
- Remove linhas em branco
- Detecta e corrige células concatenadas (bug Google Sheets)
- Remove valores nulos/vazios

---

### **Etapa 3: CARREGAMENTO (Load)**

**Destino**: Supabase (PostgreSQL REST API)

**Estratégia de inserção**:
- **UPSERT** para tabelas com chave primária (clientes, produtos, vendas)
  - Se registro existe: atualiza
  - Se não existe: insere
- **INSERT** para tabelas sem PK (preco_competidores)

**Ordem de execução** (respeita Foreign Keys):
1. `clientes` (sem dependências)
2. `produtos` (sem dependências)
3. `preco_competidores` (FK → produtos)
4. `vendas` (FK → clientes, produtos)

**Tratamento de erros**:
- Inserção em batches de 1000 registros
- Erros de FK são capturados e registrados
- Sincronização continua mesmo com falhas (não é tudo-ou-nada)

---

## 🗄️ Modelo de Dados

### Relacionamentos

```
┌─────────────┐
│  clientes   │
│ id_cliente  │◄────────┐
└─────────────┘         │ FK
                        │
                     ┌──────────┐
                     │  vendas  │
                     │ id_venda │
                     └──────────┘
                        │ FK
                        │
                     ┌──────────┐
                     │ produtos │
                     │ id_prod  │◄────────┐
                     └──────────┘         │ FK
                                          │
                        ┌─────────────────┴─────────┐
                        │  preco_competidores       │
                        │  (sem PK, apenas FKs)     │
                        └───────────────────────────┘
```

### Tabelas

#### `clientes` (Mestres)
```sql
CREATE TABLE public.clientes (
    id_cliente TEXT PRIMARY KEY,
    nome_cliente TEXT,
    estado TEXT,
    pais TEXT,
    data_cadastro DATE
);
```

#### `produtos` (Mestres)
```sql
CREATE TABLE public.produtos (
    id_produto TEXT PRIMARY KEY,
    nome_produto TEXT,
    categoria TEXT,
    marca TEXT,
    preco_atual DECIMAL(10,2),
    data_criacao DATE
);
```

#### `preco_competidores` (Transacional)
```sql
CREATE TABLE public.preco_competidores (
    id_produto TEXT REFERENCES produtos(id_produto),
    nome_concorrente TEXT,
    preco_concorrente DECIMAL(10,2),
    data_coleta DATE
    -- ⚠️ Sem PK, permite múltiplas linhas por produto/concorrente
);
```

#### `vendas` (Transacional)
```sql
CREATE TABLE public.vendas (
    id_venda TEXT PRIMARY KEY,
    data_venda DATE,
    id_cliente TEXT REFERENCES clientes(id_cliente),
    id_produto TEXT REFERENCES produtos(id_produto),
    canal_venda TEXT,
    quantidade INTEGER,
    preco_unitario DECIMAL(10,2)
);
```

### Índices de Performance
- `idx_preco_competidores_id_produto` (buscar preços de um produto)
- `idx_vendas_data_venda` (relatórios por período)
- `idx_vendas_id_cliente` (histórico do cliente)
- `idx_produtos_categoria` (filtros de categoria)

---

## 🚀 Scripts Principais

### 1. `sync_sheets.py` - Sincronização Principal

**Propósito**: Sincronizar dados mestres do Google Sheets com Supabase

**Fluxo**:
```
Etapa 1: LIMPEZA
├─ TRUNCATE TABLE public.clientes CASCADE
├─ TRUNCATE TABLE public.produtos CASCADE
├─ TRUNCATE TABLE public.preco_competidores CASCADE
└─ TRUNCATE TABLE public.vendas CASCADE

Etapa 2: POPULAÇÃO
├─ Ler clientes do Sheets → Limpar → UPSERT no Supabase
├─ Ler produtos do Sheets → Limpar → UPSERT no Supabase
├─ Ler preço_competidores do Sheets → Limpar → INSERT no Supabase
└─ Ler vendas do Sheets → Limpar → UPSERT no Supabase
```

**Tempo típico**: 1-2 minutos (4000+ registros)

**Comando**:
```bash
python src/sync_sheets.py
```

---

### 2. `generate_daily_sales.py` - Gerador de Vendas Diárias

**Propósito**: Simular e popular vendas diárias no Google Sheets

**Características**:
- Gera 500 vendas por dia
- Insere em batches de 100
- Respeita IDs válidos de clientes e produtos (queries do Supabase)
- Canal: "Loja Física" ou "Ecommerce" (aleatório)
- Preço: baseado em `preco_atual` do produto ± variação

**Versões disponíveis**:
- `generate_daily_sales_20salesday.py` - Leve (20 vendas)
- `generate_daily_sales.py` - Padrão (500 vendas)
- `generate_daily_sales500salesday.py` - Completa (500 vendas explícito)

**Comando**:
```bash
python src/generate_daily_sales.py
```

---

### 3. `validate_and_import.py` - Validação & Importação

**Propósito**: Validar dados e importar de forma granular

**Funções**:
- Testa conexão com Google Sheets
- Testa conexão com Supabase
- Valida tipos de dados
- Detecta duplicatas
- Importa com validação linha por linha

---

### 4. `test_connection.py` - Teste de Conectividade

**Propósito**: Verificar se as credenciais estão corretas

```bash
python test_connection.py
```

**Output esperado**:
```
✅ Google Sheets conectado
✅ Supabase conectado
✅ Schema verificado
```

---

## 🔐 Autenticação & Credenciais

### Google Sheets (OAuth2 Service Account)

**Arquivo**: `credentials.json` (⚠️ NÃO commitar)

```json
{
  "type": "service_account",
  "project_id": "seu-projeto",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "seu-sa@seu-projeto.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "...",
  "token_uri": "...",
  "auth_provider_x509_cert_url": "...",
  "client_x509_cert_url": "..."
}
```

**Scopes usados**:
- `https://spreadsheets.google.com/feeds`
- `https://www.googleapis.com/auth/drive`

### Supabase (API Key)

**Arquivo**: `.env` (⚠️ NÃO commitar)

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=seu-anon-key-aqui
SPREADSHEET_NAME=Dados do ecommerce
```

---

## 🔧 Dependências Principais

```
gspread==6.2.1              # Google Sheets API
oauth2client==4.1.3         # Autenticação OAuth2
supabase==2.0+              # Cliente Supabase
postgrest==2.27.2           # PostgreSQL REST
python-dotenv==1.0+         # Gerenciar .env
requests==2.31+             # HTTP requests
```

Instalar: `pip install -r requirements.txt`

---

## 🤖 Automação com GitHub Actions

**Arquivo**: `.github/workflows/generate-daily-sales.yml`

**Frequência**: Todos os dias às 00:00 UTC

**O que faz**:
1. Clona o repositório
2. Instala dependências Python
3. Executa `generate_daily_sales.py`
4. Insere novas vendas no Google Sheets
5. GitHub Actions executa `sync_sheets.py` automaticamente

**Segredos do GitHub** (necesários):
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GOOGLE_CREDENTIALS` (credentials.json em base64)

---

## 🔄 Tratamento de Erros & FK Constraints

### Problema: Foreign Key Violations

**Cenário**: Tentativa de inserir venda com `id_cliente` que não existe

**Sintoma**:
```
❌ Erro: insert or update on table "vendas" violates foreign key constraint
```

**Causas**:
1. Dados inconsistentes no Google Sheets
2. IDs de cliente/produto não existem em `clientes`/`produtos`
3. Sync parcial (vendas inseridas antes de clientes)

**Solução implementada**:
- Sync em ordem: clientes → produtos → preco_competidores → vendas
- Logging detalhado de erros por registro
- Inserção em batches permite identificar quais registros falharam

---

## 📊 Fluxo de Dados Típico

### Dia 1: Setup Inicial

```
1. Criar schema no Supabase (create_tables.sql)
2. Preencher dados mestres no Google Sheets (clientes, produtos)
3. Executar: python src/sync_sheets.py
   → Limpa tabelas (TRUNCATE CASCADE)
   → Insere clientes e produtos
4. Executar: python src/generate_daily_sales.py
   → Insere 500 vendas + preços competidores no Sheets
5. Executar novamente: python src/sync_sheets.py
   → Insere as novas vendas no Supabase
```

### Dia 2+: Operação Contínua

```
00:00 UTC → GitHub Actions dispara workflow
   ├─ generate_daily_sales.py: insere 500 novas vendas no Sheets
   └─ sync_sheets.py: sincroniza tudo com Supabase
        (mantém dados mestres, adiciona novas vendas)
```

---

## 🎯 Padrões de Design

### 1. **ETL (Extract, Transform, Load)**
Separação clara das responsabilidades em 3 etapas

### 2. **UPSERT Pattern**
Idempotência: executar script 2x = mesmo resultado

### 3. **Batch Processing**
Inserção em lotes de 1000 para melhor performance

### 4. **Graceful Degradation**
Erros em um registro não interrompem todo o sync

### 5. **Dependency Order**
Tabelas de referência antes de tabelas que as dependem

---

## 📈 Performance

| Operação | Registros | Tempo |
|----------|-----------|-------|
| Limpeza (TRUNCATE CASCADE) | 4000+ | < 1 min |
| Extração Google Sheets | 4000+ | 30-45 seg |
| Transformação (limpeza valores) | 4000+ | 10-15 seg |
| Inserção (4 tabelas) | 4000+ | 30-60 seg |
| **Total (sync completo)** | **4000+** | **1-2 min** |

---

## 🚨 Monitoramento & Logs

**Saída esperada do sync_sheets.py**:

```
======================================================================
🔄 SINCRONIZAÇÃO GOOGLE SHEETS → SUPABASE
📅 2026-01-16 10:30:45
======================================================================

======================================================================
🗑️  ETAPA 1: LIMPANDO TABELAS
======================================================================
  ✓ clientes: limpo
  ✓ produtos: limpo
  ✓ preco_competidores: limpo
  ✓ vendas: limpo

======================================================================
📥 ETAPA 2: POPULANDO TABELAS
======================================================================

🔄 clientes
  📖 Lendo clientes... ✓ 250 linhas
  🧹 Processando... ✓ 250 válidos
  💾 Inserindo... ✓ 250/250 inseridos

...

======================================================================
📊 RESUMO
======================================================================
  ✅ Inseridos: 4018
  ❌ Erros:     0
======================================================================

✅ Sincronização concluída com sucesso!
```

---

## 🔍 Troubleshooting

### Erro: "File not found credentials.json"
→ Coloque o arquivo em `credentials/credentials.json`

### Erro: "SUPABASE_URL not found"
→ Crie `.env` na raiz com `SUPABASE_URL` e `SUPABASE_KEY`

### Erro: "Foreign key constraint violated"
→ Verifique se clientes/produtos foram inseridos antes de vendas

### Erro: "Spreadsheet not found"
→ Confirme nome correto em `.env` e compartilhe sheet com service account

### Lentidão na limpeza (> 10 min)
→ Use `TRUNCATE CASCADE` (já implementado em sync_sheets.py)

---

## 📞 Contato & Documentação

- **Google Cloud Console**: https://console.cloud.google.com
- **Supabase Dashboard**: https://supabase.com/dashboard
- **gspread Docs**: https://docs.gspread.org
- **Supabase Python SDK**: https://supabase.com/docs/reference/python

---

**Última atualização**: Janeiro 2026
**Versão**: 2.0 (Refatoração ETL com TRUNCATE + UPSERT)
