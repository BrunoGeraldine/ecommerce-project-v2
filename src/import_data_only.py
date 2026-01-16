import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client
import re

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

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

spreadsheet_name = os.getenv('SPREADSHEET_NAME', 'Dados do ecommerce')


def normalize_header(header):
    """Normaliza o nome do header removendo espaços extras"""
    return header.strip().lower().replace(' ', '_')


def clean_value(value, field_name):
    """Limpa e converte o valor baseado no tipo esperado"""
    if value == '' or value is None:
        return None
    
    # Converter para string e remover espaços
    value = str(value).strip()
    
    if not value:
        return None
    
    # Campos numéricos decimais
    if any(x in field_name.lower() for x in ['preco', 'valor']):
        try:
            # Remove tudo exceto números, ponto e vírgula
            clean = re.sub(r'[^\d,.]', '', value)
            clean = clean.replace(',', '.')
            return float(clean)
        except:
            return None
    
    # Campos numéricos inteiros
    if 'quantidade' in field_name.lower() or 'qtd' in field_name.lower():
        try:
            clean = re.sub(r'[^\d]', '', value)
            return int(clean) if clean else None
        except:
            return None
    
    # Retorna string limpa
    return value


def clean_row(row_dict, expected_fields):
    """
    Limpa uma linha de dados, garantindo que apenas os campos esperados sejam incluídos
    """
    clean = {}
    
    for field in expected_fields:
        # Buscar o valor usando diferentes variações do nome
        value = None
        
        # Tentar com o nome exato
        if field in row_dict:
            value = row_dict[field]
        else:
            # Tentar com variações (com/sem espaços, maiúsculas, etc)
            for key in row_dict.keys():
                if normalize_header(key) == normalize_header(field):
                    value = row_dict[key]
                    break
        
        # Limpar e adicionar o valor
        cleaned_value = clean_value(value, field)
        if cleaned_value is not None:
            clean[field] = cleaned_value
    
    return clean if clean else None


def import_sheet(sheet_name, table_name, expected_fields):
    """Importa dados de uma aba do Google Sheets"""
    print(f"\n{'='*70}")
    print(f"📥 Importando: {sheet_name} → {table_name}")
    print(f"{'='*70}")
    
    try:
        # Abrir planilha
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Pegar dados raw primeiro para debug
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            print(f"⚠️  Nenhum dado encontrado em {sheet_name}")
            return 0
        
        headers = all_values[0]
        data_rows = all_values[1:]
        
        print(f"✓ Headers: {headers}")
        print(f"✓ Linhas: {len(data_rows)}")
        
        # Converter para dicionários manualmente
        data = []
        for row in data_rows:
            if not any(row):  # Pular linhas completamente vazias
                continue
            
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    row_dict[header.strip()] = row[i]
            
            data.append(row_dict)
        
        print(f"✓ Registros encontrados: {len(data)}")
        
        # Limpar dados
        cleaned = []
        for row_dict in data:
            clean = clean_row(row_dict, expected_fields)
            if clean:
                cleaned.append(clean)
        
        print(f"✓ Registros válidos: {len(cleaned)}")
        
        if not cleaned:
            print(f"⚠️  Nenhum registro válido após limpeza")
            return 0
        
        # Mostrar exemplo do primeiro registro
        print(f"\n📋 Exemplo do primeiro registro:")
        for key, value in cleaned[0].items():
            print(f"  {key}: {value} ({type(value).__name__})")
        
        # Limpar tabela antes de inserir
        try:
            # Usar uma condição sempre verdadeira para deletar tudo
            supabase.table(table_name).delete().gte('id', 0).execute()
            print(f"\n✓ Tabela {table_name} limpa")
        except Exception as e:
            print(f"⚠️  Aviso ao limpar tabela: {e}")
        
        # Inserir em lotes menores
        batch_size = 10
        total = 0
        errors = 0
        
        for i in range(0, len(cleaned), batch_size):
            batch = cleaned[i:i + batch_size]
            try:
                result = supabase.table(table_name).insert(batch).execute()
                total += len(batch)
                print(f"  ✓ Lote {i//batch_size + 1}: {len(batch)} registros")
            except Exception as e:
                print(f"  ⚠️  Erro no lote {i//batch_size + 1}: {str(e)[:100]}")
                # Tentar um por um
                for idx, row in enumerate(batch):
                    try:
                        supabase.table(table_name).insert(row).execute()
                        total += 1
                    except Exception as row_err:
                        errors += 1
                        print(f"    ✗ Registro {i + idx + 1}: {str(row_err)[:100]}")
                        print(f"       Dados: {row}")
        
        print(f"\n✅ Importados: {total}/{len(cleaned)} | Erros: {errors}")
        return total
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    print("\n" + "="*70)
    print("📊 IMPORTAÇÃO DE DADOS DO GOOGLE SHEETS")
    print("="*70)
    
    # Definir campos esperados para cada tabela
    tables = [
        ('clientes', 'clientes', ['id_cliente', 'nome_cliente', 'estado', 'pais', 'data_cadastro']),
        ('produtos', 'produtos', ['id_produto', 'nome_produto', 'categoria', 'marca', 'preco_atual', 'data_criacao']),
        ('preco_competidores', 'preco_competidores', ['id_produto', 'nome_concorrente', 'preco_concorrente', 'data_coleta']),
        ('vendas', 'vendas', ['id_venda', 'data_venda', 'id_cliente', 'id_produto', 'canal_venda', 'quantidade', 'preco_unitario'])
    ]
    
    total_geral = 0
    
    for sheet, table, fields in tables:
        total = import_sheet(sheet, table, fields)
        total_geral += total
    
    print("\n" + "="*70)
    print(f"✅ CONCLUÍDO - Total: {total_geral} registros importados")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()