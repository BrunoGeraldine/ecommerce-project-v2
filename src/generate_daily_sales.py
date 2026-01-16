"""
Script Gerador de Vendas Diárias - Simulador de ERP
====================================================

Gera vendas realistas e escreve diretamente no Google Sheets
para simular um sistema ERP real.

Características:
- Gera vendas com padrões realistas (mais vendas em horários de pico)
- Usa produtos e clientes existentes
- Calcula preços com variação de mercado
- Simula diferentes canais de venda
- Adiciona preços de competidores
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import random
from typing import List, Dict, Tuple

# Setup
#ROOT_DIR = Path(__file__).parent.parent
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
load_dotenv(ROOT_DIR / '.env')

CREDENTIALS_PATH = ROOT_DIR / 'credentials' / 'credentials.json'

# Configuração Google Sheets
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
print("ROOT_DIR:", ROOT_DIR)
print("CREDENTIALS_PATH:", CREDENTIALS_PATH)

if not CREDENTIALS_PATH.exists():
    print(f"❌ Erro: Arquivo {CREDENTIALS_PATH} não encontrado!")
    sys.exit(1)

creds = ServiceAccountCredentials.from_json_keyfile_name(str(CREDENTIALS_PATH), scope)
gc = gspread.authorize(creds)

spreadsheet_name = os.getenv('SPREADSHEET_NAME', 'Dados do ecommerce')


# ============================================================
# DADOS REALISTAS PARA SIMULAÇÃO
# ============================================================

# Canais de venda com probabilidades
CANAIS_VENDA = [
    ('Site', 0.45),          # 45% das vendas
    ('App Mobile', 0.30),     # 30% das vendas
    ('Marketplace', 0.20),    # 20% das vendas
    ('Loja Física', 0.05)     # 5% das vendas
]

# Competidores para monitoramento de preços
COMPETIDORES = [
    'Mercado Livre',
    'Amazon',
    'Magalu',
    'Americanas',
    'Shopee',
    'AliExpress'
]

# Horários com mais probabilidade de venda (peso maior)
HORARIOS_PICO = {
    range(8, 12): 1.2,   # Manhã
    range(12, 14): 1.5,  # Almoço (pico)
    range(14, 18): 1.3,  # Tarde
    range(19, 23): 1.8,  # Noite (maior pico)
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def get_peso_horario(hora: int) -> float:
    """Retorna o peso de probabilidade baseado na hora do dia"""
    for horario_range, peso in HORARIOS_PICO.items():
        if hora in horario_range:
            return peso
    return 0.5  # Madrugada (baixa probabilidade)


def escolher_canal() -> str:
    """Escolhe um canal de venda baseado nas probabilidades"""
    canais, pesos = zip(*CANAIS_VENDA)
    return random.choices(canais, weights=pesos)[0]


def gerar_id_venda() -> str:
    """Gera um ID único para venda"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = random.randint(1000, 9999)
    return f"sal_{timestamp}_{random_suffix}"


def formatar_data_br(data: datetime) -> str:
    """Formata data no padrão brasileiro DD/MM/YYYY"""
    return data.strftime('%d/%m/%Y')


def calcular_preco_com_variacao(preco_base: float, variacao_percentual: float = 0.10) -> float:
    """Calcula preço com variação de mercado (+/- X%)"""
    variacao = preco_base * variacao_percentual
    return round(preco_base + random.uniform(-variacao, variacao), 2)


# ============================================================
# LEITURA DE DADOS EXISTENTES
# ============================================================

def carregar_clientes() -> List[Dict]:
    """Carrega clientes existentes do Google Sheets"""
    try:
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet('clientes')
        
        records = worksheet.get_all_records()
        
        if not records:
            print("⚠️  Nenhum cliente encontrado. Criando clientes de exemplo...")
            return criar_clientes_exemplo()
        
        return records
    except Exception as e:
        print(f"⚠️  Erro ao carregar clientes: {str(e)}")
        return criar_clientes_exemplo()


def carregar_produtos() -> List[Dict]:
    """Carrega produtos existentes do Google Sheets"""
    try:
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet('produtos')
        
        records = worksheet.get_all_records()
        
        if not records:
            print("⚠️  Nenhum produto encontrado. Criando produtos de exemplo...")
            return criar_produtos_exemplo()
        
        return records
    except Exception as e:
        print(f"⚠️  Erro ao carregar produtos: {str(e)}")
        return criar_produtos_exemplo()


def criar_clientes_exemplo() -> List[Dict]:
    """Cria lista de clientes de exemplo"""
    return [
        {'id_cliente': 'cli_001', 'nome_cliente': 'João Silva', 'estado': 'SP', 'pais': 'Brasil'},
        {'id_cliente': 'cli_002', 'nome_cliente': 'Maria Santos', 'estado': 'RJ', 'pais': 'Brasil'},
        {'id_cliente': 'cli_003', 'nome_cliente': 'Pedro Oliveira', 'estado': 'MG', 'pais': 'Brasil'},
        {'id_cliente': 'cli_004', 'nome_cliente': 'Ana Costa', 'estado': 'RS', 'pais': 'Brasil'},
        {'id_cliente': 'cli_005', 'nome_cliente': 'Carlos Souza', 'estado': 'BA', 'pais': 'Brasil'},
    ]


def criar_produtos_exemplo() -> List[Dict]:
    """Cria lista de produtos de exemplo"""
    return [
        {'id_produto': 'prd_001', 'nome_produto': 'Notebook Dell', 'categoria': 'Informática', 'preco_atual': 3500.00},
        {'id_produto': 'prd_002', 'nome_produto': 'Mouse Logitech', 'categoria': 'Periféricos', 'preco_atual': 89.90},
        {'id_produto': 'prd_003', 'nome_produto': 'Teclado Mecânico', 'categoria': 'Periféricos', 'preco_atual': 450.00},
        {'id_produto': 'prd_004', 'nome_produto': 'Monitor LG 24"', 'categoria': 'Monitores', 'preco_atual': 899.00},
        {'id_produto': 'prd_005', 'nome_produto': 'Webcam HD', 'categoria': 'Periféricos', 'preco_atual': 299.00},
    ]


# ============================================================
# GERAÇÃO DE VENDAS
# ============================================================

def gerar_vendas(
    num_vendas: int, 
    data: datetime, 
    clientes: List[Dict], 
    produtos: List[Dict]
) -> List[List]:
    """
    Gera vendas realistas para um dia específico
    
    Returns:
        Lista de linhas para adicionar no Google Sheets
    """
    vendas = []
    
    print(f"\n💰 Gerando {num_vendas} vendas para {formatar_data_br(data)}...")
    
    for i in range(num_vendas):
        # Escolher hora aleatória com peso (mais vendas em horários de pico)
        hora = random.choices(
            range(24), 
            weights=[get_peso_horario(h) for h in range(24)]
        )[0]
        
        # Cliente e produto aleatórios
        cliente = random.choice(clientes)
        produto = random.choice(produtos)
        
        # Quantidade (mais provável vender 1 unidade)
        quantidade = random.choices([1, 2, 3, 4, 5], weights=[50, 25, 15, 7, 3])[0]
        
        # Preço unitário com pequena variação
        preco_base = float(produto['preco_atual'])
        preco_unitario = calcular_preco_com_variacao(preco_base, 0.05)
        
        # Canal de venda
        canal = escolher_canal()
        
        # Criar linha de venda
        venda = [
            gerar_id_venda(),                    # id_venda
            formatar_data_br(data),              # data_venda
            cliente['id_cliente'],               # id_cliente
            produto['id_produto'],               # id_produto
            canal,                               # canal_venda
            quantidade,                          # quantidade
            preco_unitario                       # preco_unitario
        ]
        
        vendas.append(venda)
        
        print(f"  ✓ Venda {i+1}: {produto['nome_produto']} - {quantidade}x R${preco_unitario:.2f} - {canal}")
    
    return vendas


# ============================================================
# GERAÇÃO DE PREÇOS DE COMPETIDORES
# ============================================================

def gerar_precos_competidores(
    produtos: List[Dict],
    data: datetime
) -> List[List]:
    """
    Gera preços de competidores para os produtos
    
    Returns:
        Lista de linhas para adicionar no Google Sheets
    """
    precos = []
    
    print(f"\n💲 Gerando preços de competidores para {formatar_data_br(data)}...")
    
    for produto in produtos:
        preco_base = float(produto['preco_atual'])
        
        # Gerar preço para alguns competidores (não todos)
        num_competidores = random.randint(2, 4)
        competidores_escolhidos = random.sample(COMPETIDORES, num_competidores)
        
        for competidor in competidores_escolhidos:
            # Competidores têm variação maior de preço (-15% a +20%)
            preco_competidor = calcular_preco_com_variacao(preco_base, 0.20)
            
            preco = [
                produto['id_produto'],           # id_produto
                competidor,                      # nome_concorrente
                preco_competidor,                # preco_concorrente
                formatar_data_br(data)           # data_coleta
            ]
            
            precos.append(preco)
    
    print(f"  ✓ {len(precos)} preços de competidores gerados")
    
    return precos


# ============================================================
# ESCRITA NO GOOGLE SHEETS
# ============================================================

def adicionar_vendas_sheets(vendas: List[List]) -> bool:
    """Adiciona vendas na planilha Google Sheets"""
    try:
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet('vendas')
        
        # Adicionar linhas no final
        worksheet.append_rows(vendas)
        
        print(f"  ✅ {len(vendas)} vendas adicionadas à planilha 'vendas'")
        return True
        
    except Exception as e:
        print(f"  ❌ Erro ao adicionar vendas: {str(e)}")
        return False


def adicionar_precos_sheets(precos: List[List]) -> bool:
    """Adiciona preços de competidores na planilha"""
    try:
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet('preco_competidores')
        
        # Adicionar linhas no final
        worksheet.append_rows(precos)
        
        print(f"  ✅ {len(precos)} preços adicionados à planilha 'preco_competidores'")
        return True
        
    except Exception as e:
        print(f"  ❌ Erro ao adicionar preços: {str(e)}")
        return False


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "="*70)
    print("🏪 GERADOR DE VENDAS DIÁRIAS - SIMULADOR ERP")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Configurações
    data_venda = datetime.now()
    
    # Número de vendas baseado no dia da semana
    dia_semana = data_venda.weekday()
    if dia_semana in [5, 6]:  # Sábado e domingo
        num_vendas = random.randint(8, 15)
    else:  # Dias úteis
        num_vendas = random.randint(15, 30)
    
    print(f"\n📊 Configuração:")
    print(f"  • Data: {formatar_data_br(data_venda)} ({['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][dia_semana]})")
    print(f"  • Vendas a gerar: {num_vendas}")
    
    # Carregar dados existentes
    print("\n" + "="*70)
    print("📖 CARREGANDO DADOS EXISTENTES")
    print("="*70)
    
    clientes = carregar_clientes()
    produtos = carregar_produtos()
    
    print(f"  ✓ {len(clientes)} clientes carregados")
    print(f"  ✓ {len(produtos)} produtos carregados")
    
    if not clientes or not produtos:
        print("\n❌ Não foi possível carregar clientes ou produtos!")
        sys.exit(1)
    
    # Gerar dados
    print("\n" + "="*70)
    print("🎲 GERANDO DADOS SIMULADOS")
    print("="*70)
    
    vendas = gerar_vendas(num_vendas, data_venda, clientes, produtos)
    precos = gerar_precos_competidores(produtos, data_venda)
    
    # Escrever no Google Sheets
    print("\n" + "="*70)
    print("📝 ESCREVENDO NO GOOGLE SHEETS")
    print("="*70)
    
    vendas_ok = adicionar_vendas_sheets(vendas)
    precos_ok = adicionar_precos_sheets(precos)
    
    # Resumo final
    print("\n" + "="*70)
    print("📊 RESUMO DA GERAÇÃO")
    print("="*70)
    print(f"  • Vendas geradas:   {len(vendas)} {'✅' if vendas_ok else '❌'}")
    print(f"  • Preços gerados:   {len(precos)} {'✅' if precos_ok else '❌'}")
    
    if vendas_ok and precos_ok:
        print("\n✅ Dados gerados e adicionados com sucesso!")
        print("\n💡 Dica: O GitHub Actions sincronizará esses dados automaticamente")
        print("   para o Supabase nas próximas 24 horas (ou execute sync_sheets.py manualmente)")
    else:
        print("\n⚠️  Alguns dados não foram adicionados. Verifique os erros acima.")
    
    print("="*70 + "\n")


if __name__ == '__main__':
    main()