import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client
from datetime import datetime
import requests

# Adicionar diretório raiz ao path para imports
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Carregar variáveis de ambiente
load_dotenv(ROOT_DIR / '.env')

# Caminhos
CREDENTIALS_PATH = ROOT_DIR / 'credentials' / 'credentials.json'
OUTPUT_SQL_PATH = ROOT_DIR / 'create_tables.sql'

# Configuração Google Sheets
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

# Verificar se credentials.json existe
if not CREDENTIALS_PATH.exists():
    print(f"❌ Erro: Arquivo {CREDENTIALS_PATH} não encontrado!")
    sys.exit(1)

creds = ServiceAccountCredentials.from_json_keyfile_name(str(CREDENTIALS_PATH), scope)
gc = gspread.authorize(creds)

# Configuração Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

spreadsheet_name = os.getenv('SPREADSHEET_NAME', 'Dados do ecommerce')


def get_pg_type(column_name, sample_values):
    """
    Determina o tipo PostgreSQL baseado no nome da coluna e valores de amostra
    """
    # Remove valores vazios
    sample_values = [str(v).strip() for v in sample_values if v and str(v).strip()]
    
    column_lower = column_name.lower()
    
    # Regras baseadas no nome da coluna
    if 'id_' in column_lower:
        return 'TEXT'
    
    if 'data_' in column_lower or 'date' in column_lower or column_lower.endswith('_data'):
        return 'DATE'
    
    if 'preco' in column_lower or 'valor' in column_lower:
        return 'DECIMAL(10,2)'
    
    if 'quantidade' in column_lower or 'qtd' in column_lower or column_lower == 'quantidade':
        return 'INTEGER'
    
    # Tenta inferir dos valores
    if sample_values:
        # Testa se é número decimal
        try:
            for v in sample_values[:5]:
                float(str(v).replace(',', '.'))
            # Se tem ponto ou vírgula, é decimal
            if any('.' in str(v) or ',' in str(v) for v in sample_values[:5]):
                return 'DECIMAL(10,2)'
        except:
            pass
        
        # Testa se é inteiro
        try:
            for v in sample_values[:5]:
                int(v)
            return 'INTEGER'
        except:
            pass
    
    return 'TEXT'


def create_table_from_sheet(sheet_name, table_name, primary_key=None, foreign_keys=None):
    """
    Cria SQL para tabela baseado na estrutura do Google Sheets
    
    Args:
        sheet_name: Nome da aba no Google Sheets
        table_name: Nome da tabela a ser criada no Supabase
        primary_key: Nome da coluna que será primary key
        foreign_keys: Dict com foreign keys {coluna: 'tabela_referencia(coluna_referencia)'}
    """
    try:
        print(f"\n{'='*70}")
        print(f"📊 Processando: {sheet_name} → {table_name}")
        print(f"{'='*70}")
        
        # Abrir planilha
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Pegar cabeçalhos e dados de amostra
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 1:
            print(f"❌ Aba {sheet_name} está vazia!")
            return None
        
        headers = all_values[0]
        data_rows = all_values[1:] if len(all_values) > 1 else []
        
        print(f"✓ Colunas encontradas: {len(headers)}")
        print(f"  └─ {', '.join(headers)}")
        print(f"✓ Linhas de dados: {len(data_rows)}")
        
        # Construir definições de colunas
        columns_def = []
        
        for i, header in enumerate(headers):
            # Pegar valores de amostra dessa coluna
            column_values = [row[i] for row in data_rows[:10] if i < len(row)]
            
            # Determinar tipo
            pg_type = get_pg_type(header, column_values)
            
            # Montar definição da coluna
            col_def = f"    {header} {pg_type}"
            
            # Adicionar PRIMARY KEY
            if primary_key and header == primary_key:
                col_def += " PRIMARY KEY"
            
            # Adicionar FOREIGN KEY
            if foreign_keys and header in foreign_keys:
                col_def += f" REFERENCES {foreign_keys[header]}"
            
            columns_def.append(col_def)
            
            # Log do tipo identificado
            type_info = pg_type
            if primary_key and header == primary_key:
                type_info += " [PK]"
            if foreign_keys and header in foreign_keys:
                type_info += f" [FK→{foreign_keys[header]}]"
            
            print(f"  └─ {header}: {type_info}")
        
        # Montar query CREATE TABLE
        create_query = f"""-- Tabela: {table_name}
CREATE TABLE IF NOT EXISTS {table_name} (
{',\n'.join(columns_def)}
);"""
        
        print(f"\n📝 SQL Gerado:")
        print(create_query)
        
        return create_query
        
    except gspread.exceptions.WorksheetNotFound:
        print(f"❌ Aba '{sheet_name}' não encontrada na planilha!")
        return None
    except Exception as e:
        print(f"❌ Erro ao processar {sheet_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def execute_sql_on_supabase(sql_query):
    """
    Tenta executar SQL diretamente no Supabase
    """
    try:
        # Método 1: Via Supabase Management API (requer service_role key)
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }
        
        # Tentar via endpoint de query
        response = requests.post(
            f"{supabase_url}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"query": sql_query}
        )
        
        if response.status_code in [200, 201, 204]:
            return True, "Executado com sucesso via API"
        else:
            return False, f"API retornou status {response.status_code}"
            
    except Exception as e:
        return False, str(e)


def import_initial_data(sheet_name, table_name):
    """
    Importa os dados iniciais do Google Sheets para o Supabase
    """
    try:
        print(f"\n{'='*70}")
        print(f"📥 Importando dados: {sheet_name} → {table_name}")
        print(f"{'='*70}")
        
        # Abrir planilha
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Obter dados
        data = worksheet.get_all_records()
        
        if not data:
            print(f"⚠️  Nenhum dado para importar em {sheet_name}")
            return 0
        
        print(f"✓ Total de registros encontrados: {len(data)}")
        
        # Limpar dados vazios
        cleaned_data = []
        for row in data:
            clean_row = {}
            for key, value in row.items():
                # Pular valores vazios
                if value == '' or value is None:
                    continue
                
                # Converter tipos numéricos
                if key in ['preco_concorrente', 'preco_unitario', 'preco_atual']:
                    try:
                        clean_row[key] = float(str(value).replace(',', '.'))
                    except:
                        clean_row[key] = None
                elif key in ['quantidade']:
                    try:
                        clean_row[key] = int(value)
                    except:
                        clean_row[key] = None
                else:
                    clean_row[key] = value
            
            if clean_row:
                cleaned_data.append(clean_row)
        
        print(f"✓ Registros válidos após limpeza: {len(cleaned_data)}")
        
        if not cleaned_data:
            print(f"⚠️  Nenhum registro válido para importar")
            return 0
        
        # Inserir dados em lotes
        batch_size = 100
        total_inserted = 0
        errors = 0
        
        for i in range(0, len(cleaned_data), batch_size):
            batch = cleaned_data[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            try:
                supabase.table(table_name).insert(batch).execute()
                total_inserted += len(batch)
                print(f"  ✓ Lote {batch_num}: {len(batch)} registros inseridos")
            except Exception as e:
                print(f"  ⚠️  Erro no lote {batch_num}: {str(e)}")
                # Tentar inserir um por um
                for row in batch:
                    try:
                        supabase.table(table_name).insert(row).execute()
                        total_inserted += 1
                    except Exception as row_error:
                        errors += 1
                        print(f"    ✗ Erro ao inserir registro: {row_error}")
        
        print(f"\n{'─'*70}")
        print(f"✅ Importação concluída:")
        print(f"   • Inseridos: {total_inserted}/{len(cleaned_data)}")
        print(f"   • Erros: {errors}")
        print(f"{'─'*70}")
        
        return total_inserted
        
    except Exception as e:
        print(f"❌ Erro ao importar dados de {sheet_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    print("\n" + "="*70)
    print("🚀 SETUP INICIAL - CRIAÇÃO DE TABELAS DO GOOGLE SHEETS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Planilha: {spreadsheet_name}")
    print("="*70)
    
    # Verificar conexão com Google Sheets
    try:
        spreadsheet = gc.open(spreadsheet_name)
        print(f"\n✅ Conectado à planilha: {spreadsheet.title}")
        print(f"   Abas disponíveis: {[ws.title for ws in spreadsheet.worksheets()]}")
    except Exception as e:
        print(f"\n❌ Erro ao conectar com Google Sheets: {str(e)}")
        sys.exit(1)
    
    all_queries = []
    
    # Configurar tabelas com suas constraints
    tables_config = [
        {
            'sheet': 'clientes',
            'table': 'clientes',
            'primary_key': 'id_cliente',
            'foreign_keys': None
        },
        {
            'sheet': 'produtos',
            'table': 'produtos',
            'primary_key': 'id_produto',
            'foreign_keys': None
        },
        {
            'sheet': 'preco_competidores',
            'table': 'preco_competidores',
            'primary_key': None,
            'foreign_keys': {'id_produto': 'produtos(id_produto)'}
        },
        {
            'sheet': 'vendas',
            'table': 'vendas',
            'primary_key': 'id_venda',
            'foreign_keys': {
                'id_cliente': 'clientes(id_cliente)',
                'id_produto': 'produtos(id_produto)'
            }
        }
    ]
    
    # ETAPA 1: Gerar SQLs
    print("\n" + "="*70)
    print("ETAPA 1: GERANDO ESTRUTURA DAS TABELAS")
    print("="*70)
    
    for config in tables_config:
        query = create_table_from_sheet(
            config['sheet'],
            config['table'],
            config['primary_key'],
            config['foreign_keys']
        )
        if query:
            all_queries.append(query)
    
    # Salvar queries em arquivo
    if all_queries:
        print("\n" + "="*70)
        print("💾 Salvando queries SQL...")
        print("="*70)
        
        with open(OUTPUT_SQL_PATH, 'w', encoding='utf-8') as f:
            f.write("-- ============================================================\n")
            f.write("-- QUERIES GERADAS AUTOMATICAMENTE DO GOOGLE SHEETS\n")
            f.write(f"-- Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- Planilha: {spreadsheet_name}\n")
            f.write("-- ============================================================\n\n")
            f.write('\n\n'.join(all_queries))
            
            # Adicionar índices
            f.write("\n\n-- ============================================================\n")
            f.write("-- ÍNDICES PARA PERFORMANCE\n")
            f.write("-- ============================================================\n\n")
            
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_preco_competidores_id_produto ON preco_competidores(id_produto);",
                "CREATE INDEX IF NOT EXISTS idx_preco_competidores_data_coleta ON preco_competidores(data_coleta);",
                "CREATE INDEX IF NOT EXISTS idx_vendas_data_venda ON vendas(data_venda);",
                "CREATE INDEX IF NOT EXISTS idx_vendas_id_cliente ON vendas(id_cliente);",
                "CREATE INDEX IF NOT EXISTS idx_vendas_id_produto ON vendas(id_produto);",
                "CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria);"
            ]
            
            f.write('\n'.join(indices))
        
        print(f"✅ Queries salvas em: {OUTPUT_SQL_PATH}")
        print(f"   Caminho completo: {OUTPUT_SQL_PATH.absolute()}")
    
    # ETAPA 2: Executar no Supabase
    print("\n" + "="*70)
    print("ETAPA 2: EXECUTAR NO SUPABASE")
    print("="*70)
    
    execute = input("\n❓ Deseja executar as queries no Supabase agora? (s/n): ").lower().strip()
    
    if execute == 's':
        print("\n⚙️  Executando queries...")
        full_sql = '\n\n'.join(all_queries)
        success, message = execute_sql_on_supabase(full_sql)
        
        if success:
            print(f"✅ {message}")
        else:
            print(f"\n⚠️  Não foi possível executar automaticamente: {message}")
            print(f"\n📋 Por favor, execute manualmente:")
            print(f"   1. Acesse: {supabase_url}/project/default/sql")
            print(f"   2. Copie o conteúdo de: {OUTPUT_SQL_PATH}")
            print(f"   3. Execute no SQL Editor")
    else:
        print(f"\n⏭️  Execução manual necessária:")
        print(f"   1. Acesse: {supabase_url}/project/default/sql")
        print(f"   2. Copie o conteúdo de: {OUTPUT_SQL_PATH}")
        print(f"   3. Execute no SQL Editor")
    
    # ETAPA 3: Importar dados
    print("\n" + "="*70)
    print("ETAPA 3: IMPORTAÇÃO DE DADOS INICIAIS")
    print("="*70)
    
    import_data = input("\n❓ Deseja importar os dados agora? (s/n): ").lower().strip()
    
    if import_data == 's':
        total_imported = 0
        for config in tables_config:
            imported = import_initial_data(config['sheet'], config['table'])
            total_imported += imported
        
        print(f"\n{'='*70}")
        print(f"📊 Total geral: {total_imported} registros importados")
        print(f"{'='*70}")
    else:
        print("\n⏭️  Importação de dados pulada.")
        print("   Use o script 'sync_sheets.py' depois para importar os dados.")
    
    # RESUMO FINAL
    print("\n" + "="*70)
    print("✅ SETUP CONCLUÍDO!")
    print("="*70)
    print("\n📋 Próximos passos:")
    print(f"   1. Verifique as tabelas no Supabase: {supabase_url}")
    print(f"   2. Revise o SQL gerado em: {OUTPUT_SQL_PATH}")
    print("   3. Configure o GitHub Actions para sincronização diária")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()