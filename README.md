# Projeto E-commerce v2 - ETL Google Sheets → Supabase

## 📊 Resumo Executivo

Pipeline ETL em **6 camadas** que sincroniza dados entre Google Sheets e Supabase com validação robusta.

- **ETL Principal**: `validate_and_import.py` (validação em cada camada)
- **Gerador diário**: `generate_daily_sales.py` (popula vendas)
- **Automação**: GitHub Actions (a cada 5 minutos)
- **Database**: Supabase (PostgreSQL)

---

## 🏗️ Estrutura do Projeto

```
ecommerce-project-v2/
├── 📁 credentials/
│   └── credentials.json            # Google Service Account (⚠️ gitignore)
├── 📁 src/
│   ├── validate_and_import.py      # 🚀 ETL Principal (6 Camadas)
│   ├── generate_daily_sales.py     # Gerador de vendas diárias
│   └── test_connection.py           # Teste de conectividade
├── 📄 ARCHITECTURE.md              # Documentação técnica detalhada
├── 📄 create_tables.sql            # Schema do banco
├── 📄 requirements.txt             # Dependências Python
├── 📄 .env                         # Variáveis de ambiente (⚠️ gitignore)
└── 📄 .gitignore
```

---

## 🚀 Setup Inicial (5 passos)

### 1️⃣ Clonar o repositório
```bash
git clone <seu-repo>
cd ecommerce-project-v2
```

### 2️⃣ Instalar dependências
```bash
pip install -r requirements.txt
```

### 3️⃣ Configurar Google Sheets
- Criar projeto no Google Cloud
- Ativar APIs (Sheets + Drive)
- Criar Service Account
- Baixar `credentials.json` para pasta `credentials/`
- Compartilhar planilha com email do Service Account

### 4️⃣ Configurar Supabase
- Criar projeto em supabase.com
- Copiar `SUPABASE_URL` e `SUPABASE_KEY`
- Criar arquivo `.env`:
```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=seu-anon-key-aqui
SPREADSHEET_NAME=Dados do ecommerce
```

### 5️⃣ Executar setup
```bash
# Criar tabelas no Supabase
python create_tables.sql

# Testar conexão
python test_connection.py

# Importar dados iniciais
python src/validate_and_import.py
```

---

## 📋 Como Usar

### Para Importação Inicial
```bash
python src/validate_and_import.py
```
✅ Valida dados em **6 camadas** antes de inserir
✅ Mostra erros **linha por linha**
✅ Ideal para debug e setup

### Para Sincronização Diária
Via GitHub Actions (automático a cada 5 min):
1. `generate_daily_sales.py` → Insere vendas no Sheets
2. `validate_and_import.py` → Sincroniza com Supabase

### Para Gerar Novas Vendas Manualmente
```bash
python src/generate_daily_sales.py
```
Insere 500 novas vendas no Google Sheets

---

## 🔍 O que Acontece em Cada Execução

```
validate_and_import.py executa:

📖 Camada 1: Ler dados do Google Sheets
   └─ Lê célula por célula (evita bugs de concatenação)

🧹 Camada 2-4: Validar & Limpar
   ├─ Normaliza tipos (texto, decimal, int, data)
   ├─ Valida campos obrigatórios
   └─ Remove valores inválidos

🔗 Camada 5: Validar Foreign Keys
   ├─ Carrega IDs existentes em cache
   ├─ Valida cada FK
   └─ Remove registros com FKs inválidas

💾 Camada 6: Inserir
   ├─ Limpa tabelas (DELETE WHERE pk != '___impossible___')
   ├─ Insere em lotes de 50
   └─ Retry individual se batch falhar

📊 Retorna:
   ✅ Quantos inseridos
   ❌ Quantos erros
```

---

## 🔧 Configuração GitHub Actions

### Setup (uma vez)
No GitHub, vá para Settings → Secrets e adicione:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SPREADSHEET_NAME`
- `GOOGLE_CREDENTIALS` (base64 de credentials.json)

### Para encodar credentials.json em base64
```bash
# Linux/Mac
base64 -i credentials/credentials.json | pbcopy

# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("credentials/credentials.json")) | Set-Clipboard
```

---

## 📊 Modelo de Dados

4 tabelas principais:

| Tabela | Tipo | PK | FKs |
|--------|------|----|----|
| `clientes` | Mestres | id_cliente | - |
| `produtos` | Mestres | id_produto | - |
| `preco_competidores` | Transacional | - | id_produto → produtos |
| `vendas` | Transacional | id_venda | id_cliente → clientes, id_produto → produtos |

Para mais detalhes, ver `ARCHITECTURE.md`

---

## 🚨 Troubleshooting

**❌ "Arquivo credentials.json não encontrado"**
→ Coloque em `credentials/credentials.json`

**❌ "SUPABASE_URL not found"**
→ Crie `.env` com `SUPABASE_URL` e `SUPABASE_KEY`

**❌ "Foreign key constraint violated"**
→ Verifique se clientes/produtos foram inseridos antes de vendas

**❌ "Planilha não encontrada"**
→ Confirme nome em `.env` e compartilhe sheet com Service Account

**⚠️ Script demora muito (> 5 min)**
→ Verifique conexão de rede e quota da API

---

## 📚 Documentação Completa

Ver `ARCHITECTURE.md` para:
- Explicação das 6 camadas em detalhes
- Exemplos de código
- Performance benchmarks
- Padrões de design
- Fluxo de dados completo

---

## 🔐 Segurança

⚠️ **Nunca commit**:
- `credentials.json`
- `.env`
- Qualquer arquivo com tokens/chaves

Verificar `.gitignore` está preenchido:
```
credentials.json
.env
__pycache__/
*.pyc
venv/
```