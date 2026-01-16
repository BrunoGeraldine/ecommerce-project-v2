import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client
from datetime import datetime
import re
from typing import Dict, List, Any, Optional, Tuple

# Setup
ROOT_DIR = Path(__file__).parent.parent
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
# ✅ CAMADA 1: DEFINIÇÃO DE SCHEMAS
# ============================================================

# Define estrutura esperada de cada tabela
# Define tipos de dados
# Define campos obrigatórios
# Define foreign keys

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
    'produtos': {
        'columns': ['id_produto', 'nome_produto', 'categoria', 'marca', 'preco_atual', 'data_criacao'],
        'required': ['id_produto'],
        'types': {
            'id_produto': 'text',
            'nome_produto': 'text',
            'categoria': 'text',
            'marca': 'text',
            'preco_atual': 'decimal',
            'data_criacao': 'date'
        }
    },
    'preco_competidores': {
        'columns': ['id_produto', 'nome_concorrente', 'preco_concorrente', 'data_coleta'],
        'required': ['id_produto'],
        'foreign_keys': {
            'id_produto': 'produtos'
        },
        'types': {
            'id_produto': 'text',
            'nome_concorrente': 'text',
            'preco_concorrente': 'decimal',
            'data_coleta': 'date'
        }
    },
    'vendas': {
        'columns': ['id_venda', 'data_venda', 'id_cliente', 'id_produto', 'canal_venda', 'quantidade', 'preco_unitario'],
        'required': ['id_venda'],
        'foreign_keys': {
            'id_cliente': 'clientes',
            'id_produto': 'produtos'
        },
        'types': {
            'id_venda': 'text',
            'data_venda': 'date',
            'id_cliente': 'text',
            'id_produto': 'text',
            'canal_venda': 'text',
            'quantidade': 'integer',
            'preco_unitario': 'decimal'
        }
    }
}


# ============================================================
# ✅ CAMADA 2: FUNÇÕES DE LIMPEZA E CONVERSÃO
# ============================================================

# Limpa textos (remove espaços, caracteres invisíveis)
# Converte decimais (aceita vírgula e ponto)
# Converte inteiros
# Normaliza datas (DD/MM/YYYY → YYYY-MM-DD)

def clean_text(value: Any) -> Optional[str]:
    """Limpa e normaliza texto"""
    if value is None or value == '':
        return None
    
    # Converter para string e remover espaços extras
    text = str(value).strip()
    
    # Remover múltiplos espaços
    text = re.sub(r'\s+', ' ', text)
    
    # Remover caracteres invisíveis
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    return text if text else None


def clean_decimal(value: Any) -> Optional[float]:
    """Limpa e converte valores decimais"""
    if value is None or value == '':
        return None
    
    try:
        # Converter para string
        text = str(value).strip()
        
        if not text:
            return None
        
        # Remover espaços, símbolos de moeda, etc
        text = re.sub(r'[^\d,.\-]', '', text)
        
        # Substituir vírgula por ponto
        text = text.replace(',', '.')
        
        # Remover pontos extras (exceto o último que é decimal)
        parts = text.split('.')
        if len(parts) > 2:
            text = ''.join(parts[:-1]) + '.' + parts[-1]
        
        result = float(text)
        
        # Validar range razoável
        if result < 0 or result > 1000000:
            print(f"    ⚠️  Valor decimal fora do range esperado: {result}")
        
        return result
    except (ValueError, AttributeError):
        return None


def clean_integer(value: Any) -> Optional[int]:
    """Limpa e converte valores inteiros"""
    if value is None or value == '':
        return None
    
    try:
        # Converter para string e remover não-numéricos
        text = str(value).strip()
        text = re.sub(r'[^\d\-]', '', text)
        
        if not text:
            return None
        
        return int(text)
    except (ValueError, AttributeError):
        return None


def clean_date(value: Any) -> Optional[str]:
    """Limpa e valida datas - retorna no formato YYYY-MM-DD"""
    if value is None or value == '':
        return None
    
    text = str(value).strip()
    
    if not text:
        return None
    
    # Formatos aceitos: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
    
    # Formato YYYY-MM-DD (já correto)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', text):
        return text
    
    # Formato DD/MM/YYYY
    if re.match(r'^\d{2}/\d{2}/\d{4}$', text):
        day, month, year = text.split('/')
        return f"{year}-{month}-{day}"
    
    # Formato DD-MM-YYYY
    if re.match(r'^\d{2}-\d{2}-\d{4}$', text):
        day, month, year = text.split('-')
        return f"{year}-{month}-{day}"
    
    # Formato YYYY/MM/DD
    if re.match(r'^\d{4}/\d{2}/\d{2}$', text):
        return text.replace('/', '-')
    
    return None


# ============================================================
# ✅ CAMADA 3: LEITURA SEGURA DO GOOGLE SHEETS
# ============================================================

# Lê Google Sheets célula por célula
# Evita pegar linha inteira em uma célula
# Normaliza headers (lowercase, underscores)

def read_sheet_safe(sheet_name: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Lê dados do Google Sheets de forma segura
    Retorna: (headers, list_of_dicts)
    """
    try:
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Pegar TODOS os valores como matriz
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            return [], []
        
        # Primeira linha = headers (limpar)
        raw_headers = all_values[0]
        headers = [h.strip().lower().replace(' ', '_') for h in raw_headers]
        
        # Resto = dados
        data_rows = all_values[1:]
        
        # Converter para lista de dicionários manualmente
        records = []
        for row_idx, row in enumerate(data_rows, start=2):  # start=2 porque linha 1 é header
            # Pular linhas completamente vazias
            if not any(cell.strip() for cell in row):
                continue
            
            record = {}
            for col_idx, header in enumerate(headers):
                # Pegar o valor da célula específica
                if col_idx < len(row):
                    cell_value = row[col_idx].strip()
                    record[header] = cell_value
                else:
                    record[header] = ''
            
            # Adicionar metadados
            record['_row_number'] = row_idx
            records.append(record)
        
        return headers, records
        
    except gspread.exceptions.WorksheetNotFound:
        print(f"❌ Aba '{sheet_name}' não encontrada!")
        return [], []
    except Exception as e:
        print(f"❌ Erro ao ler '{sheet_name}': {str(e)}")
        import traceback
        traceback.print_exc()
        return [], []


# ============================================================
# ✅ CAMADA 4: VALIDAÇÃO E LIMPEZA DE REGISTROS
# ============================================================

# Valida cada linha individualmente
# Mostra exatamente onde está o erro
# Lista campos obrigatórios faltando

def validate_and_clean_row(
    row: Dict[str, str], 
    table_name: str, 
    row_number: int
) -> Tuple[bool, Optional[Dict], List[str]]:
    """
    Valida e limpa UMA linha de dados
    
    Returns:
        (is_valid, cleaned_row, errors)
    """
    schema = SCHEMAS.get(table_name)
    if not schema:
        return False, None, [f"Schema não encontrado para '{table_name}'"]
    
    errors = []
    cleaned = {}
    
    # Processar cada coluna esperada
    for column in schema['columns']:
        # Buscar valor (tentar variações de nome)
        value = None
        column_lower = column.lower()
        
        for key in row.keys():
            if key.lower() == column_lower:
                value = row[key]
                break
        
        # Se não encontrou, tentar sem underscores
        if value is None:
            column_no_underscore = column.replace('_', '')
            for key in row.keys():
                if key.lower().replace('_', '') == column_no_underscore:
                    value = row[key]
                    break
        
        # Limpar baseado no tipo
        col_type = schema['types'].get(column, 'text')
        cleaned_value = None
        
        if col_type == 'text':
            cleaned_value = clean_text(value)
        elif col_type == 'decimal':
            cleaned_value = clean_decimal(value)
        elif col_type == 'integer':
            cleaned_value = clean_integer(value)
        elif col_type == 'date':
            cleaned_value = clean_date(value)
        
        # Validar campos obrigatórios
        if column in schema.get('required', []):
            if cleaned_value is None or cleaned_value == '':
                errors.append(
                    f"Linha {row_number}: Campo obrigatório '{column}' vazio ou inválido. "
                    f"Valor original: '{value}'"
                )
                continue
        
        # Adicionar ao resultado (apenas se não for None)
        if cleaned_value is not None:
            cleaned[column] = cleaned_value
    
    # Verificar se tem pelo menos os campos obrigatórios
    missing_required = [
        req for req in schema.get('required', []) 
        if req not in cleaned or cleaned[req] is None
    ]
    
    if missing_required:
        errors.append(
            f"Linha {row_number}: Campos obrigatórios faltando: {', '.join(missing_required)}"
        )
        return False, None, errors
    
    is_valid = len(errors) == 0
    return is_valid, cleaned if is_valid else None, errors


# ============================================================
# ✅ CAMADA 5: VALIDAÇÃO DE FOREIGN KEYS
# ============================================================

#Carrega IDs existentes antes de inserir
#Valida se FK existe na tabela pai
#Previne erro 23503

def load_existing_ids(table_name: str, id_column: str) -> set:
    """Carrega IDs existentes de uma tabela"""
    try:
        print(f"  🔍 Carregando IDs existentes de {table_name}.{id_column}...")
        result = supabase.table(table_name).select(id_column).execute()
        
        ids = {str(row[id_column]).strip() for row in result.data if row.get(id_column)}
        print(f"  ✓ {len(ids)} IDs únicos encontrados")
        
        return ids
    except Exception as e:
        print(f"  ⚠️  Erro ao carregar IDs: {str(e)}")
        return set()


def validate_foreign_keys(
    cleaned_data: List[Dict], 
    table_name: str
) -> Tuple[List[Dict], List[str]]:
    """
    Valida foreign keys antes de inserir
    
    Returns:
        (valid_rows, fk_errors)
    """
    schema = SCHEMAS.get(table_name)
    if not schema or 'foreign_keys' not in schema:
        return cleaned_data, []
    
    print(f"\n🔗 Validando Foreign Keys para {table_name}...")
    
    fk_errors = []
    valid_rows = []
    
    # Carregar IDs existentes de tabelas referenciadas
    fk_cache = {}
    for fk_column, ref_table in schema['foreign_keys'].items():
        fk_cache[fk_column] = load_existing_ids(ref_table, fk_column)
    
    # Validar cada linha
    for i, row in enumerate(cleaned_data, 1):
        row_valid = True
        
        for fk_column, ref_table in schema['foreign_keys'].items():
            if fk_column in row:
                fk_value = str(row[fk_column]).strip()
                
                if fk_value not in fk_cache[fk_column]:
                    fk_errors.append(
                        f"Linha {i}: FK inválida - {fk_column}='{fk_value}' "
                        f"não existe em {ref_table}.{fk_column}"
                    )
                    row_valid = False
        
        if row_valid:
            valid_rows.append(row)
    
    return valid_rows, fk_errors


# ============================================================
# ✅ CAMADA 6: IMPORTAÇÃO COM LOGGING DETALHADO
# ============================================================

# Limpa tabela antes de inserir
# Insere em lotes
# Se falhar, tenta um por um
# Log detalhado de cada erro

def import_with_validation(sheet_name: str, table_name: str) -> Dict[str, int]:
    """
    Importa dados com validação completa em 5 camadas
    
    Returns:
        Estatísticas da importação
    """
    print(f"\n{'='*80}")
    print(f"📥 IMPORTANDO: {sheet_name} → {table_name}")
    print(f"{'='*80}")
    
    stats = {
        'total_rows': 0,
        'empty_rows': 0,
        'valid_rows': 0,
        'invalid_rows': 0,
        'fk_errors': 0,
        'inserted': 0,
        'insert_errors': 0
    }
    
    # ETAPA 1: Ler dados
    print("\n📖 ETAPA 1: Lendo dados do Google Sheets...")
    headers, raw_records = read_sheet_safe(sheet_name)
    
    if not headers or not raw_records:
        print("⚠️  Nenhum dado encontrado")
        return stats
    
    stats['total_rows'] = len(raw_records)
    print(f"  ✓ Colunas: {headers}")
    print(f"  ✓ Total de linhas (não-vazias): {stats['total_rows']}")
    
    # ETAPA 2: Validar e limpar
    print(f"\n🧹 ETAPA 2: Validando e limpando dados...")
    
    cleaned_data = []
    validation_errors = []
    
    for record in raw_records:
        row_num = record.get('_row_number', '?')
        
        is_valid, cleaned_row, errors = validate_and_clean_row(
            record, 
            table_name, 
            row_num
        )
        
        if is_valid and cleaned_row:
            cleaned_data.append(cleaned_row)
            stats['valid_rows'] += 1
        else:
            stats['invalid_rows'] += 1
            validation_errors.extend(errors)
    
    print(f"  ✓ Registros válidos: {stats['valid_rows']}")
    print(f"  ✗ Registros inválidos: {stats['invalid_rows']}")
    
    if validation_errors:
        print(f"\n  ⚠️  Primeiros erros de validação:")
        for error in validation_errors[:5]:
            print(f"    • {error}")
        if len(validation_errors) > 5:
            print(f"    ... e mais {len(validation_errors) - 5} erros")
    
    if not cleaned_data:
        print("\n❌ Nenhum registro válido para importar")
        return stats
    
    # ETAPA 3: Validar Foreign Keys
    if 'foreign_keys' in SCHEMAS[table_name]:
        print(f"\n🔗 ETAPA 3: Validando Foreign Keys...")
        
        valid_data, fk_errors = validate_foreign_keys(cleaned_data, table_name)
        
        stats['fk_errors'] = len(cleaned_data) - len(valid_data)
        cleaned_data = valid_data
        
        print(f"  ✓ Registros com FK válidas: {len(valid_data)}")
        print(f"  ✗ Registros com FK inválidas: {stats['fk_errors']}")
        
        if fk_errors:
            print(f"\n  ⚠️  Primeiros erros de FK:")
            for error in fk_errors[:5]:
                print(f"    • {error}")
            if len(fk_errors) > 5:
                print(f"    ... e mais {len(fk_errors) - 5} erros")
    
    if not cleaned_data:
        print("\n❌ Nenhum registro válido após validação de FK")
        return stats
    
    # ETAPA 4: Mostrar exemplo
    print(f"\n📋 EXEMPLO do primeiro registro válido:")
    first_row = cleaned_data[0]
    for key, value in sorted(first_row.items()):
        value_display = str(value)[:50]
        print(f"  • {key:20s}: {value_display:50s} ({type(value).__name__})")
    
    # ETAPA 5: Limpar tabela
    print(f"\n🗑️  ETAPA 4: Limpando tabela {table_name}...")
    try:
        # Método que funciona: delete onde primary key >= 0 (sempre verdadeiro)
        if table_name == 'clientes':
            supabase.table(table_name).delete().neq('id_cliente', '___impossible___').execute()
        elif table_name == 'produtos':
            supabase.table(table_name).delete().neq('id_produto', '___impossible___').execute()
        elif table_name == 'vendas':
            supabase.table(table_name).delete().neq('id_venda', '___impossible___').execute()
        elif table_name == 'preco_competidores':
            supabase.table(table_name).delete().neq('id_produto', '___impossible___').execute()
        
        print(f"  ✓ Tabela limpa")
    except Exception as e:
        print(f"  ⚠️  Aviso ao limpar: {str(e)}")
    
    # ETAPA 6: Inserir dados
    print(f"\n💾 ETAPA 5: Inserindo dados no Supabase...")
    
    batch_size = 50
    
    for i in range(0, len(cleaned_data), batch_size):
        batch = cleaned_data[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        try:
            supabase.table(table_name).insert(batch).execute()
            stats['inserted'] += len(batch)
            print(f"  ✓ Lote {batch_num}: {len(batch)} registros inseridos")
        except Exception as e:
            print(f"  ⚠️  Erro no lote {batch_num}, tentando inserção individual...")
            
            # Tentar um por um
            for j, row in enumerate(batch):
                try:
                    supabase.table(table_name).insert(row).execute()
                    stats['inserted'] += 1
                except Exception as row_err:
                    stats['insert_errors'] += 1
                    error_msg = str(row_err)[:100]
                    print(f"    ✗ Erro no registro {i+j+1}: {error_msg}")
                    print(f"       Dados: {row}")
    
    # RESUMO
    print(f"\n{'─'*80}")
    print(f"✅ IMPORTAÇÃO CONCLUÍDA")
    print(f"{'─'*80}")
    print(f"  Total de linhas lidas:        {stats['total_rows']}")
    print(f"  Registros válidos:            {stats['valid_rows']}")
    print(f"  Registros inválidos:          {stats['invalid_rows']}")
    print(f"  Erros de FK:                  {stats['fk_errors']}")
    print(f"  Inseridos com sucesso:        {stats['inserted']}")
    print(f"  Erros de inserção:            {stats['insert_errors']}")
    print(f"{'─'*80}")
    
    return stats


# ============================================================
# ✅ MAIN: ORQUESTRAÇÃO DA IMPORTAÇÃO
# ============================================================

def main():
    print("\n" + "="*80)
    print("🚀 SISTEMA DE IMPORTAÇÃO COM VALIDAÇÃO")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Planilha: {spreadsheet_name}")
    print("="*80)
    
    # Ordem importante: tabelas sem FK primeiro
    tables_order = [
        ('clientes', 'clientes'),
        ('produtos', 'produtos'),
        ('preco_competidores', 'preco_competidores'),
        ('vendas', 'vendas')
    ]
    
    total_stats = {
        'total_inserted': 0,
        'total_errors': 0
    }
    
    for sheet_name, table_name in tables_order:
        stats = import_with_validation(sheet_name, table_name)
        total_stats['total_inserted'] += stats['inserted']
        total_stats['total_errors'] += stats['insert_errors'] + stats['invalid_rows'] + stats['fk_errors']
    
    # RESUMO FINAL
    print("\n" + "="*80)
    print("📊 RESUMO GERAL DA IMPORTAÇÃO")
    print("="*80)
    print(f"  Total de registros inseridos: {total_stats['total_inserted']}")
    print(f"  Total de erros:               {total_stats['total_errors']}")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()