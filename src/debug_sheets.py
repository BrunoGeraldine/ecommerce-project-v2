import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
load_dotenv(ROOT_DIR / '.env')

CREDENTIALS_PATH = ROOT_DIR / 'credentials' / 'credentials.json'

scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

creds = ServiceAccountCredentials.from_json_keyfile_name(str(CREDENTIALS_PATH), scope)
gc = gspread.authorize(creds)

spreadsheet_name = os.getenv('SPREADSHEET_NAME', 'Dados do ecommerce')

def debug_sheet(sheet_name):
    """Debug: mostra como os dados estão sendo lidos"""
    print(f"\n{'='*70}")
    print(f"🔍 DEBUG: {sheet_name}")
    print(f"{'='*70}")
    
    try:
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Método 1: get_all_values (raw)
        print("\n📊 Método 1: get_all_values() - Primeiras 3 linhas:")
        all_values = worksheet.get_all_values()
        for i, row in enumerate(all_values[:3]):
            print(f"  Linha {i}: {row}")
        
        # Método 2: get_all_records (com headers)
        print("\n📊 Método 2: get_all_records() - Primeiros 2 registros:")
        records = worksheet.get_all_records()
        for i, record in enumerate(records[:2]):
            print(f"\n  Registro {i+1}:")
            for key, value in record.items():
                print(f"    {key}: '{value}' (tipo: {type(value).__name__})")
        
        # Verificar headers
        print("\n📋 Headers encontrados:")
        headers = all_values[0] if all_values else []
        for i, header in enumerate(headers):
            print(f"  Coluna {i}: '{header}' (len: {len(header)})")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    sheets = ['clientes', 'produtos', 'preco_competidores', 'vendas']
    
    for sheet in sheets:
        debug_sheet(sheet)
    
    print("\n" + "="*70)
    print("✅ DEBUG CONCLUÍDO")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()