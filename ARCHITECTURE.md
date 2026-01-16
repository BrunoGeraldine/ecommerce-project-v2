# Arquitetura - Projeto E-commerce v2

## 📋 Visão Geral

Este projeto implementa um **pipeline ETL (Extract, Transform, Load)** em 6 camadas que sincroniza dados entre Google Sheets e Supabase (PostgreSQL), com suporte a geração automática de vendas diárias.

```
┌──────────────────┐      ┌────────────────────────┐      ┌──────────────────┐
│  Google Sheets   │  →   │  validate_and_import   │  →   │    Supabase      │
│  (Dados Mestres) │      │  (6 Camadas de ETL)    │      │  (PostgreSQL)    │
└──────────────────┘      └────────────────────────┘      └──────────────────┘
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
│   ├── validate_and_import.py         # 🚀 ETL Principal (6 camadas)
│   ├── test_connection.py              # Teste de conectividade
│   ├── generate_daily_sales.py         # Gerador diário de vendas (500/dia)
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

---

## 🔄 Pipeline ETL - 6 Camadas

`validate_and_import.py` implementa um sistema de importação **robusto e escalável** em 6 camadas independentes:

### **Camada 1: SCHEMA (Definição)**

**Propósito**: Definir a estrutura esperada de cada tabela

**Dados armazenados**:
- Colunas esperadas
- Campos obrigatórios
- Tipos de dados
- Foreign Keys e tabelas referenciadas

```python
SCHEMAS = {
    'clientes': {
        'columns': ['id_cliente', 'nome_cliente', 'estado', 'pais', 'data_cadastro'],
        'required': ['id_cliente'],
        'types': {
            'id_cliente': 'text',
            'nome_cliente': 'text',
            'estado': 'text',
            'pais': 'text',
            'data_cadastro': 'date'
        }
    },
    'vendas': {
        'columns': ['id_venda', 'data_venda', 'id_cliente', 'id_produto', 'canal_venda', 'quantidade', 'preco_unitario'],
        'required': ['id_venda'],
        'foreign_keys': {
            'id_cliente': 'clientes',
            'id_produto': 'produtos'
        },
        'types': {...}
    }
}
```

---

### **Camada 2: LIMPEZA & CONVERSÃO (Transform)**

**Funções especializadas** por tipo de dado:

| Função | Entrada | Saída | Exemplo |
|--------|---------|-------|---------|
| `clean_text()` | `str` | `str` (normalizado) | `"  São  Paulo  "` → `"São Paulo"` |
| `clean_decimal()` | `str` | `float` | `"R$ 45,50"` → `45.50` |
| `clean_integer()` | `str` | `int` | `"5 unidades"` → `5` |
| `clean_date()` | `str` | `str (YYYY-MM-DD)` | `"15/01/2026"` → `"2026-01-15"` |

**Validações**:
- Remove espaços múltiplos e caracteres invisíveis
- Converte vírgula → ponto para decimais
- Suporta múltiplos formatos de data (DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY)
- Valida ranges (ex: preço não pode ser negativo)
- Retorna `None` para valores inválidos/vazios

---

### **Camada 3: LEITURA SEGURA (Extract)**

**Função**: `read_sheet_safe(sheet_name)`

**Propósito**: Ler Google Sheets célula por célula para evitar bugs de concatenação

```python
def read_sheet_safe(sheet_name: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Lê Google Sheets de forma segura
    
    Retorna:
        - headers: ['id_cliente', 'nome_cliente', ...]
        - records: [{'id_cliente': '001', 'nome_cliente': 'João', ...}, ...]
    """
    # 1. Pegar matriz completa de valores
    all_values = worksheet.get_all_values()
    
    # 2. Primeira linha = headers (normalizar)
    headers = [h.strip().lower().replace(' ', '_') for h in all_values[0]]
    
    # 3. Resto = dados (converter para dicts)
    for row in all_values[1:]:
        record = {}
        for col_idx, header in enumerate(headers):
            record[header] = row[col_idx] if col_idx < len(row) else ''
        records.append(record)
    
    return headers, records
```

**Por que segura?**
- ✅ Evita bugs onde primeira célula contém múltiplos valores
- ✅ Lê célula por célula (não linha inteira)
- ✅ Normaliza headers automaticamente
- ✅ Adiciona metadados (`_row_number` para debugging)

---

### **Camada 4: VALIDAÇÃO DE REGISTROS (Validate)**

**Função**: `validate_and_clean_row(row, table_name, row_number)`

**Propósito**: Validar UM registro com erros detalhados

**Validações realizadas**:
1. Campo encontrado no sheet (permite variações de nome)
2. Tipo de dados correto
3. Campos obrigatórios presentes
4. Valores dentro de ranges esperados

**Exemplo de uso**:
```python
for record in raw_records:
    is_valid, cleaned_row, errors = validate_and_clean_row(
        record,
        'vendas',
        row_number=15
    )
    
    if is_valid:
        cleaned_data.append(cleaned_row)
    else:
        print(f"Erro na linha 15: {errors}")
        # Erro específico: "Campo obrigatório 'id_venda' vazio"
```

**Retorna**:
- `is_valid`: bool
- `cleaned_row`: Dict com valores normalizados ou None
- `errors`: List[str] com descrição de cada erro

---

### **Camada 5: VALIDAÇÃO FOREIGN KEYS (Validate FK)**

**Função**: `validate_foreign_keys(cleaned_data, table_name)`

**Propósito**: Garantir que FKs existem antes de inserir (previne erro 23503)

**Como funciona**:
1. Carrega IDs existentes de tabelas referenciadas em **cache**
2. Para cada registro: verifica se `id_cliente` existe em `clientes`
3. Remove registros com FKs inválidas
4. Log detalhado de qual FK falhou

```python
# Exemplo para tabela 'vendas'
valid_data, fk_errors = validate_foreign_keys(cleaned_data, 'vendas')

# Resultado:
# valid_data: [registro1, registro2, ...]  (apenas com FKs válidas)
# fk_errors: [
#     "Linha 15: FK inválida - id_cliente='CLI_999' não existe em clientes.id_cliente",
#     "Linha 42: FK inválida - id_produto='PRD_888' não existe em produtos.id_produto"
# ]
```

**Benefícios**:
- ✅ Evita FK constraint violations
- ✅ Identificar exatamente qual registro foi rejeitado
- ✅ Cache de IDs para performance
- ✅ Sincronização idempotente (remove dados órfãos)

---

### **Camada 6: IMPORTAÇÃO (Load)**

**Função**: `import_with_validation(sheet_name, table_name)`

**Fluxo completo** com 5 etapas internas:

```
📖 ETAPA 1: Lendo dados do Google Sheets
  └─ read_sheet_safe() → headers + raw_records

🧹 ETAPA 2: Validando e limpando dados
  └─ validate_and_clean_row() × N → cleaned_data + validation_errors

🔗 ETAPA 3: Validando Foreign Keys
  └─ validate_foreign_keys() → valid_data + fk_errors

📋 ETAPA 4: Exemplo do primeiro registro
  └─ Mostra estrutura completa para debug

🗑️  ETAPA 5: Limpando tabela
  └─ DELETE WHERE pk != '___impossible___' (equiv. TRUNCATE)

💾 ETAPA 6: Inserindo dados
  └─ Lotes de 50 + retry individual se falhar
```

**Retorna estatísticas**:
```python
{
    'total_rows': 250,           # Linhas lidas do Sheets
    'empty_rows': 0,             # Linhas em branco
    'valid_rows': 245,           # Passou em todas validações
    'invalid_rows': 5,           # Falhou validação de schema
    'fk_errors': 0,              # FK inválidas
    'inserted': 245,             # Inseridos com sucesso
    'insert_errors': 0           # Erros na inserção
}
```

---

## 🎯 Ordem de Execução Obrigatória

Respeita dependências Foreign Key:

```
1. clientes    (sem dependências)
   └─ Seu próprio schema
   
2. produtos    (sem dependências)
   └─ Seu próprio schema
   
3. preco_competidores  (depende de produtos)
   └─ FK: id_produto → produtos
   
4. vendas      (depende de clientes + produtos)
   └─ FK: id_cliente → clientes
   └─ FK: id_produto → produtos
```

**Se executado fora de ordem**: Camada 5 (Validação FK) rejeitará registros com FKs inválidas automaticamente.

---

## 🚀 Scripts Principais

### 1. `validate_and_import.py` - ETL Principal ⭐

**Propósito**: Importar dados do Google Sheets com validação em 6 camadas

**Comando**:
```bash
python src/validate_and_import.py
```

**O que faz**:
1. ✅ Valida estrutura de cada tabela (schema)
2. ✅ Limpa valores conforme tipo
3. ✅ Lê Google Sheets células por célula
4. ✅ Valida campos obrigatórios
5. ✅ Valida Foreign Keys
6. ✅ Importa com retry e logging detalhado

**Tempo típico**: 2-3 minutos (11.000+ registros)

**Output esperado**:
```
🚀 SISTEMA DE IMPORTAÇÃO COM VALIDAÇÃO
📅 2026-01-16 10:30:45
📊 Planilha: Dados do ecommerce

================================================================================
📥 IMPORTANDO: clientes → clientes
================================================================================

📖 ETAPA 1: Lendo dados do Google Sheets...
  ✓ Colunas: ['id_cliente', 'nome_cliente', 'estado', 'pais', 'data_cadastro']
  ✓ Total de linhas (não-vazias): 250

🧹 ETAPA 2: Validando e limpando dados...
  ✓ Registros válidos: 250
  ✗ Registros inválidos: 0

💾 ETAPA 5: Inserindo dados no Supabase...
  ✓ Lote 1: 50 registros inseridos
  ✓ Lote 2: 50 registros inseridos
  ...

────────────────────────────────────────────────────────────────────────────────
✅ IMPORTAÇÃO CONCLUÍDA
────────────────────────────────────────────────────────────────────────────────
  Total de linhas lidas:        250
  Registros válidos:            250
  Registros inválidos:          0
  Erros de FK:                  0
  Inseridos com sucesso:        250
  Erros de inserção:            0
────────────────────────────────────────────────────────────────────────────────

📊 RESUMO GERAL DA IMPORTAÇÃO
  Total de registros inseridos: 11,378
  Total de erros:               0
```

---

### 2. `generate_daily_sales.py` - Gerador de Vendas Diárias

**Propósito**: Simular e popular vendas diárias no Google Sheets com dados realistas

**Características**:
- Gera 500 vendas por dia (configurável por versão)
- Insere em batches de 100 no Google Sheets
- Respeita apenas IDs **válidos** de clientes e produtos (queries live ao Supabase)
- Canal: "Loja Física" ou "Ecommerce" (aleatório 50/50)
- Preço unitário: baseado em `preco_atual` do produto ± 0-20% variação
- Quantidades: 1-5 unidades por venda

**Versões disponíveis**:
| Arquivo | Volume | Uso |
|---------|--------|-----|
| `generate_daily_sales_20salesday.py` | 20 vendas/dia | Testes rápidos, CI/CD |
| `generate_daily_sales.py` | 500 vendas/dia | Produção, relatórios realistas |
| `generate_daily_sales500salesday.py` | 500 vendas/dia | Alias/backup |

Todas as versões consultam **dados reais** do Supabase para garantir IDs válidos.

**Comando**:
```bash
python src/generate_daily_sales.py
```

---

### 3. `test_connection.py` - Teste de Conectividade

**Propósito**: Verificar se as credenciais estão corretas

**Comando**:
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

---

## 🔐 Autenticação & Credenciais

### Google Sheets (OAuth2 Service Account)

**Arquivo**: `credentials.json` (⚠️ NÃO commitar)

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
5. GitHub Actions executa `validate_and_import.py` automaticamente

**Segredos do GitHub** (necesários):
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GOOGLE_CREDENTIALS` (credentials.json em base64)

---

## 📊 Performance & Benchmarks

| Operação | Registros | Tempo |
|----------|-----------|-------|
| Leitura Google Sheets | 11.378+ | 45-60 seg |
| Validação & limpeza (camadas 2-4) | 11.378+ | 30-45 seg |
| Validação FK (camada 5) | 11.378+ | 20-30 seg |
| Limpeza de tabela (DELETE) | - | < 5 seg |
| Inserção em batches (camada 6) | 11.378+ | 60-90 seg |
| **Total (pipeline completo)** | **11.378+** | **2-3 min** |

**Notas**:
- Batch size: 50 registros (otimizado para timeout da API)
- FK cache: carregado uma vez por tabela (performance one-time)
- Retry individual: só ocorre se batch falhar (raro)
- Validação de schema: ~O(n) onde n = número de registros

---

## 🎯 Padrões de Design

### 1. **Separação de Responsabilidades**
Cada camada faz UMA coisa bem:
- Camada 1: Define schema
- Camada 2: Converte tipos
- Camada 3: Lê dados
- Camada 4: Valida registros
- Camada 5: Valida FKs
- Camada 6: Insere dados

### 2. **Idempotência**
Executar script múltiplas vezes = mesmo resultado:
- DELETE tudo antes de INSERT
- Não há duplicatas ou dados órfãos
- Seguro para execução repetida

### 3. **Validação Progressiva**
Filtrar dados "ruins" o mais cedo possível:
- Camada 4: remove schema inválido (~0.2% de overhead)
- Camada 5: remove FKs inválidas (~1-2% de overhead)
- Camada 6: só insere dados garantidamente válidos

### 4. **Logging Detalhado**
Cada erro mostra:
- Número da linha
- Campo específico
- Valor recebido
- Valor esperado

### 5. **Graceful Degradation**
Erros em registros não interrompem sync:
- Batch falha → retry individual
- Registros individuais falham → continua próximo
- Log de cada falha → auditoria completa

---

## 🔍 Troubleshooting

### Erro: "Arquivo credentials.json não encontrado"
→ Coloque em `credentials/credentials.json`

### Erro: "SUPABASE_URL not found"
→ Crie `.env` na raiz com `SUPABASE_URL` e `SUPABASE_KEY`

### Erro: "Foreign key constraint violated (erro 23503)"
→ Verifique se clientes/produtos foram inseridos antes de vendas

### Erro: "Planilha não encontrada"
→ Confirme nome em `.env` e compartilhe sheet com service account email

### Script demora muito (> 5 min)
→ Verifique conexão de rede e quota da API Google Sheets

---

## 📞 Contato & Documentação

- **Google Cloud Console**: https://console.cloud.google.com
- **Supabase Dashboard**: https://supabase.com/dashboard
- **gspread Docs**: https://docs.gspread.org
- **Supabase Python SDK**: https://supabase.com/docs/reference/python

---

**Última atualização**: Janeiro 2026
**Versão**: 3.0 (6 Camadas ETL com validate_and_import.py)
