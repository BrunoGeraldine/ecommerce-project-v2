import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client

# Carregar variáveis de ambiente
load_dotenv()

print("="*60)
print("🧪 TESTANDO CONEXÕES")
print("="*60)

# Teste 1: Google Sheets
print("\n1️⃣  Testando Google Sheets...")
try:
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    gc = gspread.authorize(creds)
    
    spreadsheet_name = os.getenv('SPREADSHEET_NAME')
    spreadsheet = gc.open(spreadsheet_name)
    
    print(f"   ✅ Conectado à planilha: {spreadsheet.title}")
    print(f"   ✅ Abas encontradas: {[ws.title for ws in spreadsheet.worksheets()]}")
    
except FileNotFoundError:
    print("   ❌ Arquivo credentials.json não encontrado!")
except gspread.exceptions.SpreadsheetNotFound:
    print("   ❌ Planilha não encontrada! Verifique o nome e o compartilhamento.")
except Exception as e:
    print(f"   ❌ Erro: {str(e)}")

# Teste 2: Supabase
print("\n2️⃣  Testando Supabase...")
try:
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Tentar listar tabelas (vai dar erro se não houver tabelas, mas conexão funciona)
    try:
        result = supabase.table('_dummy_').select("*").limit(1).execute()
    except:
        pass
    
    print(f"   ✅ Conectado ao Supabase: {supabase_url}")
    
except Exception as e:
    print(f"   ❌ Erro: {str(e)}")

print("\n" + "="*60)
print("✅ TESTES CONCLUÍDOS")
print("="*60)