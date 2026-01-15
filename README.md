# Projeto E-commerce v2 - Integração Google Sheets → Supabase

## 📊 Arquitetura
- **Fonte**: Google Sheets ("Dados do ecommerce")
- **Destino**: Supabase (PostgreSQL)
- **Automação**: GitHub Actions (1x por dia)

projeto-ecommerce-v2/
├── .github/
│   └── workflows/
│       └── (vazio por enquanto)
├── venv/                      # Ambiente virtual (não commitar)
├── src/
│   └── setup_tables.py (AQUI ALOCAREMOS O ARQUIVO)
├── credentials/
│   └── credentials.json       # Credenciais Google (não commitar)
├── .env                       # Variáveis de ambiente (não commitar)
├── .gitignore                 # Arquivos a ignorar
├── requirements.txt           # Dependências Python
├── test_connection.py         # Script de teste


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
5. Execute: `python setup_tables.py`

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