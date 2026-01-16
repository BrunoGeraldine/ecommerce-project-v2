# Projeto E-commerce v2 - Integração Google Sheets → Supabase

## 📊 Arquitetura
- **Fonte**: Google Sheets ("Dados do ecommerce")
- **Destino**: Supabase (PostgreSQL)
- **Automação**: GitHub Actions (1x por dia)

projeto-ecommerce-v2/

┌─────────────────────────────────────────────────────────────────────────┐
│   ├── .github/                                                          |
|   │   └── workflows/                                                    |
|   │       └── (vazio por enquanto)                                      |
|   ├── venv/                      # Ambiente virtual (não commitar)      |
|   ├── src/                                                              |
|   │   └── setup_tables.py (AQUI ALOCAREMOS O ARQUIVO)                   |
|   ├── credentials/                                                      |
|   │   └── credentials.json       # Credenciais Google (não commitar)    |
|   ├── .env                       # Variáveis de ambiente (não commitar) |
|   ├── .gitignore                 # Arquivos a ignorar                   |
|   ├── requirements.txt           # Dependências Python                  |
|   ├── test_connection.py         # Script de teste                      |
└─────────────────────────────────────────────────────────────────────────┘

## 🚀 Setup Inicial

CHECKLIST DE VALIDAÇÃO
Antes de prosseguir, confirme:

 ✅ Projeto criado no Google Cloud 
 ✅ APIs ativadas (Sheets + Drive) 
 ✅ Service Account criada 
 ✅ Arquivo credentials.json baixado 
 ✅ Planilha compartilhada com service account 
 ✅ Projeto criado no Supabase 
 ✅ Credenciais do Supabase copiadas 
 ✅ Arquivo .env criado e preenchido 
 ✅ Arquivo .gitignore criado 
 ✅ Dependências Python instaladas 
 ✅ Teste de conexão executado com sucesso


1. Clone o repositório
2. Instale dependências: `pip install -r requirements.txt`
3. Configure credenciais Google Cloud e coloque em `credentials.json`
4. Crie arquivo `.env` com as chaves do Supabase
5. Execute: `python validate_and_import.py`

## 📅 Sincronização Automática

O GitHub Actions roda diariamente às 3h UTC e sincroniza:
- ✅ clientes
- ✅ produtos  
- ✅ preco_competidores
- ✅ vendas

## 🔧 Configuração GitHub Secrets

- `GOOGLE_CREDENTIALS`: JSON completo das credenciais
- `SUPABASE_URL`: URL do projeto
- `SUPABASE_KEY`: Chave anon ou service_role

📅 QUANDO USAR CADA SCRIPT
1️⃣ validate_and_import.py - SETUP INICIAL (1 VEZ)
Quando usar:

✅ Primeira vez que vai popular o banco
✅ Quando suspeitar de dados corrompidos
✅ Após fazer mudanças grandes no Google Sheets
✅ Quando precisar de debug detalhado

Características:

🐢 Mais lento (valida TUDO)
🔍 Logs super detalhados
🛡️ Validação em 5 camadas
📊 Mostra exatamente onde está o erro


2️⃣ sync_sheets.py - SINCRONIZAÇÃO DIÁRIA (SEMPRE)
Quando usar:

✅ Todo dia (via GitHub Actions)
✅ Quando adicionar novos dados no Sheets
✅ Quando atualizar dados existentes
✅ Para manter banco sempre atualizado

Características:

⚡ Rápido (validação básica)
🔄 Estratégia TRUNCATE + INSERT (substitui tudo)
📝 Logs resumidos
🤖 Perfeito para automação


🔄 ESTRATÉGIAS DE SINCRONIZAÇÃO
Opção A: TRUNCATE + INSERT (Recomendado) ✅
O que faz:

Deleta TODOS os dados da tabela
Insere TODOS os dados do Google Sheets

Vantagens:

✅ Simples
✅ Sempre sincronizado 100%
✅ Remove dados deletados no Sheets
✅ Não precisa comparar o que mudou

Desvantagens:

⚠️ Perde histórico de alterações
⚠️ IDs auto-incrementais resetam (mas você usa TEXT, então OK!)

Quando usar:

Seu caso! (dados sempre vêm do Sheets como fonte da verdade)


Opção B: UPSERT (Alternativa)
O que faz:

Para cada linha do Sheets:

Se ID existe → UPDATE
Se ID não existe → INSERT



Vantagens:

✅ Preserva histórico
✅ Mais eficiente para poucos dados novos

Desvantagens:

⚠️ Mais complexo
⚠️ Não remove dados deletados do Sheets
⚠️ Precisa comparar cada linha

Quando usar:

Se você precisar manter dados que foram deletados do Sheets