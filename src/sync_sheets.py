import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client
from datetime import datetime
import re
from typing import Dict, List, Any, Optional

# Setup
ROOT_DIR = Path(__file__).parent
sys.path.append(str(ROOT_DIR))
load_dotenv(ROOT_DIR / '.env')

CREDENTIALS_PATH = ROOT_DIR / 'credentials' / 'credentials.json'

# Configuração Google Sheets
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

if not CREDENTIALS_PATH.exists():
    print(f"❌ Erro: Arquivo {CREDENTIALS_PATH} não encontrado!")
    sys.exit(1)

creds = ServiceAccountCredentials.from_json_keyfile_name(str(CREDENTIALS_PATH), scope)
gc = gspread.authorize(creds)

# Configuração Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

spreadsheet_name = os.getenv('SPREADSHEET_NAME', 'Dados do ecommerce')


# ============================================================
# CONFIGURAÇÃO DE TABELAS
# ============================================================

TABLES_CONFIG = {
    'clientes': {
        'columns': ['id_cliente', 'nome_cliente', 'estado', 'pais', 'data_cadastro'],
        'required': ['id_cliente'],
        'pk': 'id_cliente'
    },
    'produtos': {
        'columns': ['id_produto', 'nome_produto', 'categoria', 'marca', 'preco_atual', 'data_criacao'],
        'required': ['id_produto'],
        'pk': 'id_produto'
    },
    'preco_competidores': {
        'columns': ['id_produto', 'nome_concorrente', 'preco_concorrente', 'data_coleta'],
        'required': ['id_produto'],
        'pk': None
    },
    'vendas': {
        'columns': ['id_venda', 'data_venda', 'id_cliente', 'id_produto', 'canal_venda', 'quantidade', 'preco_unitario'],
        'required': ['id_venda'],
        'pk': 'id_venda'
    }
}


# ============================================================
# FUNÇÕES DE LIMPEZA RÁPIDA
# ============================================================

def clean_value(value: Any, column_name: str) -> Any:
    """Limpa um valor baseado no nome da coluna"""
    if value is None or value == '':
        return None
    
    # Limpar string
    value_str = str(value).strip()
    if not value_str:
        return None
    
    column_lower = column_name.lower()
    
    # IDs e textos
    if 'id_' in column_lower or 'nome' in column_lower or 'estado' in column_lower or 'pais' in column_lower or 'canal' in column_lower or 'marca' in column_lower or 'categoria' in column_lower or 'concorrente' in column_lower:
        return re.sub(r'\s+', ' ', value_str)  # Remover espaços duplos
    
    # Preços/valores decimais
    if 'preco' in column_lower or 'valor' in column_lower:
        try:
            clean = re.sub(r'[^\d,.\-]', '', value_str)
            clean = clean.replace(',', '.')
            return float(clean)
        except:
            return None
    
    # Quantidade (inteiro)
    if 'quantidade' in column_lower or 'qtd' in column_lower:
        try:
            clean = re.sub(r'[^\d]', '', value_str)
            return int(clean) if clean else None
        except:
            return None
    
    # Datas
    if 'data' in column_lower or 'date' in column_lower:
        # YYYY-MM-DD
        if re.match(r'^\d{4}-\d{2}-\d{2}$', value_str):
            return value_str
        # DD/MM/YYYY
        if re.match(r'^\d{2}/\d{2}/\d{4}$', value_str):
            day, month, year = value_str.split('/')
            return f"{year}-{month}-{day}"
        # DD-MM-YYYY
        if re.match(r'^\d{2}-\d{2}-\d{4}$', value_str):
            day, month, year = value_str.split('-')
            return f"{year}-{month}-{day}"
        return None
    
    return value_str


# ============================================================
# SINCRONIZAÇÃO
# ============================================================

def sync_table(sheet_name: str, table_name: str) -> Dict[str, int]:
    """
    Sincroniza uma tabela do Google Sheets para o Supabase
    
    Estratégia: TRUNCATE + INSERT (substituição completa)
    """
    print(f"\n{'='*70}")
    print(f"🔄 SINCRONIZANDO: {sheet_name} → {table_name}")
    print(f"{'='*70}")
    
    stats = {
        'read': 0,
        'valid': 0,
        'inserted': 0,
        'errors': 0
    }
    
    try:
        # ETAPA 1: Ler dados do Google Sheets
        print("📖 Lendo dados do Google Sheets...")
        
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            print("⚠️  Nenhum dado encontrado")
            return stats
        
        # Headers e dados
        headers = [h.strip().lower().replace(' ', '_') for h in all_values[0]]
        data_rows = all_values[1:]
        stats['read'] = len(data_rows)
        
        print(f"  ✓ Linhas encontradas: {stats['read']}")
        
        # ETAPA 2: Converter e limpar
        print("🧹 Limpando e validando dados...")
        
        config = TABLES_CONFIG.get(table_name, {})
        expected_columns = config.get('columns', headers)
        required_fields = config.get('required', [])
        
        cleaned_records = []
        
        for row_idx, row in enumerate(data_rows, start=2):
            # Pular linhas vazias
            if not any(cell.strip() for cell in row):
                continue
            
            # Criar registro
            record = {}
            is_valid = True
            
            for col_idx, header in enumerate(headers):
                if col_idx < len(row):
                    raw_value = row[col_idx]
                    cleaned_value = clean_value(raw_value, header)
                    
                    if cleaned_value is not None:
                        record[header] = cleaned_value
            
            # Validar campos obrigatórios
            for required in required_fields:
                if required not in record or record[required] is None:
                    is_valid = False
                    stats['errors'] += 1
                    break
            
            if is_valid and record:
                cleaned_records.append(record)
                stats['valid'] += 1
        
        print(f"  ✓ Registros válidos: {stats['valid']}")
        print(f"  ✗ Registros inválidos: {stats['errors']}")
        
        if not cleaned_records:
            print("❌ Nenhum registro válido para sincronizar")
            return stats
        
        # ETAPA 3: Limpar tabela (TRUNCATE)
        print(f"🗑️  Limpando tabela {table_name}...")
        
        try:
            # Deletar todos os registros
            pk = config.get('pk', 'id')
            if pk:
                supabase.table(table_name).delete().neq(pk, '___impossible___').execute()
            else:
                # Para tabelas sem PK, usar outro campo
                supabase.table(table_name).delete().neq('id_produto', '___impossible___').execute()
            
            print(f"  ✓ Tabela limpa")
        except Exception as e:
            print(f"  ⚠️  Aviso ao limpar: {str(e)}")
        
        # ETAPA 4: Inserir novos dados
        print(f"💾 Inserindo {len(cleaned_records)} registros...")
        
        batch_size = 100
        
        for i in range(0, len(cleaned_records), batch_size):
            batch = cleaned_records[i:i + batch_size]
            
            try:
                supabase.table(table_name).insert(batch).execute()
                stats['inserted'] += len(batch)
                print(f"  ✓ Lote {i//batch_size + 1}: {len(batch)} registros")
            except Exception as e:
                print(f"  ⚠️  Erro no lote, tentando individual...")
                
                for record in batch:
                    try:
                        supabase.table(table_name).insert(record).execute()
                        stats['inserted'] += 1
                    except Exception as err:
                        stats['errors'] += 1
                        print(f"    ✗ Erro: {str(err)[:80]}")
        
        # RESUMO
        print(f"\n{'─'*70}")
        print(f"✅ Sincronização concluída:")
        print(f"  • Lidos:     {stats['read']}")
        print(f"  • Válidos:   {stats['valid']}")
        print(f"  • Inseridos: {stats['inserted']}")
        print(f"  • Erros:     {stats['errors']}")
        print(f"{'─'*70}")
        
        return stats
        
    except Exception as e:
        print(f"❌ Erro fatal: {str(e)}")
        import traceback
        traceback.print_exc()
        return stats


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "="*70)
    print("🔄 SINCRONIZAÇÃO AUTOMÁTICA - GOOGLE SHEETS → SUPABASE")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Ordem: tabelas sem FK primeiro
    sync_order = [
        ('clientes', 'clientes'),
        ('produtos', 'produtos'),
        ('preco_competidores', 'preco_competidores'),
        ('vendas', 'vendas')
    ]
    
    total_inserted = 0
    total_errors = 0
    
    for sheet_name, table_name in sync_order:
        stats = sync_table(sheet_name, table_name)
        total_inserted += stats['inserted']
        total_errors += stats['errors']
    
    # RESUMO GERAL
    print("\n" + "="*70)
    print("📊 RESUMO GERAL")
    print("="*70)
    print(f"  Total inserido: {total_inserted}")
    print(f"  Total de erros: {total_errors}")
    
    if total_errors == 0:
        print("\n✅ Sincronização concluída sem erros!")
    else:
        print(f"\n⚠️  Sincronização concluída com {total_errors} erros")
    
    print("="*70 + "\n")


if __name__ == '__main__':
    main()