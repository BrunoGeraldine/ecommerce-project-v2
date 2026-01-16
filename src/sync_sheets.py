"""
Sincronização Google Sheets → Supabase
======================================
Etapa 1: Limpar tabelas com TRUNCATE CASCADE
Etapa 2: Popular tabelas com dados do Google Sheets

CORREÇÕES:
- Remove duplicatas antes de inserir
- Valida Foreign Keys antes de inserir
- Usa apenas INSERT (sem UPSERT)
- Insere registro por registro em caso de erro de FK
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Set

from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client
import requests

# ============================================================
# SETUP
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
load_dotenv(ROOT_DIR / '.env')

CREDENTIALS_PATH = ROOT_DIR / 'credentials' / 'credentials.json'

if not CREDENTIALS_PATH.exists():
    print(f"❌ Erro: {CREDENTIALS_PATH} não encontrado!")
    sys.exit(1)

# Google Sheets
creds = ServiceAccountCredentials.from_json_keyfile_name(
    str(CREDENTIALS_PATH),
    ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
)
gc = gspread.authorize(creds)

# Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'Dados do ecommerce')

# Configuração das tabelas
TABLES = {
    'clientes': {
        'sheet': 'clientes',
        'pk': 'id_cliente',
        'fk': None
    },
    'produtos': {
        'sheet': 'produtos',
        'pk': 'id_produto',
        'fk': None
    },
    'preco_competidores': {
        'sheet': 'preco_competidores',
        'pk': None,
        'fk': {'id_produto': 'produtos'}
    },
    'vendas': {
        'sheet': 'vendas',
        'pk': 'id_venda',
        'fk': {
            'id_cliente': 'clientes',
            'id_produto': 'produtos'
        }
    }
}

# Cache de IDs válidos (para validação de FK)
FK_CACHE = {}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def limpar_valor(valor: Any, nome_coluna: str) -> Any:
    """Limpa e converte valor baseado no tipo de coluna"""
    if valor is None or valor == '':
        return None
    
    valor_str = str(valor).strip()
    if not valor_str:
        return None
    
    col_lower = nome_coluna.lower()
    
    # Preços (float)
    if 'preco' in col_lower or 'valor' in col_lower:
        try:
            clean = re.sub(r'[^\d,.\-]', '', valor_str)
            clean = clean.replace(',', '.')
            return float(clean)
        except:
            return None
    
    # Quantidade (int)
    if 'quantidade' in col_lower or 'qtd' in col_lower:
        try:
            clean = re.sub(r'[^\d]', '', valor_str)
            return int(clean) if clean else None
        except:
            return None
    
    # Datas - converter para YYYY-MM-DD
    if 'data' in col_lower or 'date' in col_lower:
        if re.match(r'^\d{4}-\d{2}-\d{2}', valor_str):
            return valor_str[:10]
        if re.match(r'^\d{2}/\d{2}/\d{4}', valor_str):
            day, month, year = valor_str[:10].split('/')
            return f"{year}-{month}-{day}"
        if re.match(r'^\d{2}-\d{2}-\d{4}', valor_str):
            day, month, year = valor_str[:10].split('-')
            return f"{year}-{month}-{day}"
        return None
    
    # Texto (remover espaços múltiplos)
    return re.sub(r'\s+', ' ', valor_str)


def carregar_ids_existentes(tabela: str, coluna_id: str) -> Set[str]:
    """Carrega IDs existentes de uma tabela para validação de FK"""
    try:
        result = supabase.table(tabela).select(coluna_id).execute()
        ids = {str(row[coluna_id]).strip() for row in result.data if row.get(coluna_id)}
        return ids
    except Exception as e:
        print(f"\n      ⚠️  Erro ao carregar IDs de {tabela}.{coluna_id}: {str(e)[:60]}")
        return set()


def validar_foreign_keys(registro: Dict, config: Dict) -> bool:
    """Valida se as foreign keys do registro existem nas tabelas referenciadas"""
    fks = config.get('fk')
    if not fks:
        return True
    
    for fk_coluna, tabela_ref in fks.items():
        if fk_coluna not in registro:
            continue
        
        fk_valor = str(registro[fk_coluna]).strip()
        
        # Lazy load do cache de IDs
        cache_key = f"{tabela_ref}.{fk_coluna}"
        if cache_key not in FK_CACHE:
            FK_CACHE[cache_key] = carregar_ids_existentes(tabela_ref, fk_coluna)
        
        # Validar se existe
        if fk_valor not in FK_CACHE[cache_key]:
            return False
    
    return True


def remover_duplicatas(registros: List[Dict], pk: str) -> List[Dict]:
    """Remove registros duplicados baseado na primary key"""
    if not pk:
        return registros
    
    unicos = {}
    duplicatas = 0
    
    for registro in registros:
        if pk not in registro:
            continue
        
        registro_id = str(registro[pk]).strip()
        
        if registro_id in unicos:
            duplicatas += 1
            # Manter o último (mais recente)
            unicos[registro_id] = registro
        else:
            unicos[registro_id] = registro
    
    if duplicatas > 0:
        print(f"({duplicatas} dup removidas) ", end="")
    
    return list(unicos.values())


# ============================================================
# ETAPA 1: LIMPAR TABELAS
# ============================================================

def limpar_tabelas():
    """Limpa todas as tabelas usando TRUNCATE CASCADE"""
    print("\n" + "="*70)
    print("🗑️  ETAPA 1: LIMPANDO TABELAS")
    print("="*70)
    
    # Limpar na ordem reversa (dependências primeiro)
    ordem_reversa = ['vendas', 'preco_competidores', 'produtos', 'clientes']
    
    for tabela in ordem_reversa:
        if tabela not in TABLES:
            continue
        
        try:
            # Método 1: Via DELETE (mais compatível)
            pk = TABLES[tabela].get('pk')
            if pk:
                supabase.table(tabela).delete().neq(pk, '___impossible___').execute()
            else:
                supabase.table(tabela).delete().neq('id_produto', '___impossible___').execute()
            
            print(f"  ✓ {tabela}: limpo")
        except Exception as e:
            print(f"  ⚠️  {tabela}: {str(e)[:60]}")
    
    # Limpar cache de FKs
    global FK_CACHE
    FK_CACHE = {}
    
    print()


# ============================================================
# ETAPA 2: POPULAR TABELAS
# ============================================================

def popular_tabelas():
    """Lê dados do Google Sheets e insere no Supabase"""
    print("="*70)
    print("📥 ETAPA 2: POPULANDO TABELAS")
    print("="*70)
    
    spreadsheet = gc.open(SPREADSHEET_NAME)
    total_inserido = 0
    total_erros = 0
    
    # Ordem correta: referências antes de dependências
    ordem = ['clientes', 'produtos', 'preco_competidores', 'vendas']
    
    for tabela in ordem:
        if tabela not in TABLES:
            continue
        
        config = TABLES[tabela]
        sheet_name = config['sheet']
        pk = config.get('pk')
        
        print(f"\n🔄 {tabela}")
        print(f"  📖 Lendo {sheet_name}...", end=" ")
        
        try:
            # Ler planilha
            worksheet = spreadsheet.worksheet(sheet_name)
            all_values = worksheet.get_all_values()
            
            if len(all_values) < 2:
                print("⚠️  sem dados")
                continue
            
            # Parse headers
            headers = [h.strip().lower().replace(' ', '_') for h in all_values[0]]
            data_rows = all_values[1:]
            print(f"✓ {len(data_rows)} linhas")
            
            # Processar registros
            print(f"  🧹 Processando...", end=" ")
            registros = []
            
            for row in data_rows:
                if not any(cell.strip() for cell in row):
                    continue
                
                # Fix: se primeira célula tem múltiplos valores, fazer split
                if row and len(row[0]) > 50 and ('  ' in row[0] or '\t' in row[0]):
                    parts = [p.strip() for p in row[0].split() if p.strip()]
                    if parts:
                        row[0] = parts[0]
                
                # Montar registro
                registro = {}
                for col_idx, header in enumerate(headers):
                    if col_idx < len(row):
                        valor_limpo = limpar_valor(row[col_idx], header)
                        if valor_limpo is not None:
                            registro[header] = valor_limpo
                
                if registro:
                    registros.append(registro)
            
            # Remover duplicatas
            if pk:
                registros = remover_duplicatas(registros, pk)
            
            print(f"✓ {len(registros)} únicos")
            
            # Validar e filtrar por FK (se houver)
            if config.get('fk'):
                print(f"  🔗 Validando FKs...", end=" ")
                registros_validos = []
                erros_fk = 0
                
                for registro in registros:
                    if validar_foreign_keys(registro, config):
                        registros_validos.append(registro)
                    else:
                        erros_fk += 1
                
                registros = registros_validos
                
                if erros_fk > 0:
                    print(f"⚠️  {erros_fk} com FK inválida removidos")
                    total_erros += erros_fk
                else:
                    print(f"✓ OK")
            
            # Inserir em batches
            if registros:
                print(f"  💾 Inserindo...", end=" ")
                batch_size = 500  # Reduzido para evitar timeouts
                inseridos = 0
                erros_insert = 0
                
                for i in range(0, len(registros), batch_size):
                    batch = registros[i:i + batch_size]
                    
                    try:
                        # Sempre INSERT (já fizemos TRUNCATE antes)
                        supabase.table(tabela).insert(batch).execute()
                        inseridos += len(batch)
                        total_inserido += len(batch)
                    except Exception as e:
                        # Se batch falhar, tentar um por um
                        erro_msg = str(e)
                        
                        # Mostrar só primeiro erro
                        if erros_insert == 0:
                            print(f"\n      ⚠️  Erro no batch: {erro_msg[:80]}")
                            print(f"      🔄 Tentando inserção individual...")
                        
                        for registro in batch:
                            try:
                                supabase.table(tabela).insert([registro]).execute()
                                inseridos += 1
                                total_inserido += 1
                            except Exception as err:
                                erros_insert += 1
                                total_erros += 1
                                
                                # Mostrar apenas primeiro erro individual
                                if erros_insert == 1:
                                    print(f"      ✗ Exemplo: {str(err)[:80]}")
                
                if erros_insert > 0:
                    print(f"⚠️  {inseridos}/{len(registros)} inseridos ({erros_insert} erros)")
                else:
                    print(f"✓ {inseridos}/{len(registros)} inseridos")
        
        except Exception as e:
            print(f"❌ {str(e)[:60]}")
            total_erros += 1
    
    print()
    return total_inserido, total_erros


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "="*70)
    print("🔄 SINCRONIZAÇÃO GOOGLE SHEETS → SUPABASE")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Etapa 1: Limpar
    limpar_tabelas()
    
    # Etapa 2: Popular
    inseridos, erros = popular_tabelas()
    
    # Resumo
    print("="*70)
    print("📊 RESUMO")
    print("="*70)
    print(f"  ✅ Inseridos: {inseridos}")
    print(f"  ❌ Erros:     {erros}")
    print("="*70 + "\n")
    
    if erros == 0:
        print("✅ Sincronização concluída com sucesso!\n")
    elif erros < 100:
        print(f"⚠️  Sincronização concluída com {erros} erros (aceitável)\n")
    else:
        print(f"❌ Sincronização concluída com {erros} erros (investigar)\n")


if __name__ == '__main__':
    main()