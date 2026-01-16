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
import time
from pathlib import Path
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
from typing import List, Dict

# ============================================================
# SETUP
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
load_dotenv(ROOT_DIR / '.env')

CREDENTIALS_PATH = ROOT_DIR / 'credentials' / 'credentials.json'

scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

print("ROOT_DIR:", ROOT_DIR)
print("CREDENTIALS_PATH:", CREDENTIALS_PATH)

if not CREDENTIALS_PATH.exists():
    print(f"❌ Erro: Arquivo {CREDENTIALS_PATH} não encontrado!")
    sys.exit(1)

creds = ServiceAccountCredentials.from_json_keyfile_name(
    str(CREDENTIALS_PATH), scope
)
gc = gspread.authorize(creds)

spreadsheet_name = os.getenv('SPREADSHEET_NAME', 'Dados do ecommerce')

# ============================================================
# DADOS REALISTAS PARA SIMULAÇÃO
# ============================================================

CANAIS_VENDA = [
    ('Site', 0.45),
    ('App Mobile', 0.30),
    ('Marketplace', 0.20),
    ('Loja Física', 0.05)
]

COMPETIDORES = [
    'Mercado Livre',
    'Amazon',
    'Magalu',
    'Americanas',
    'Shopee',
    'AliExpress'
]

HORARIOS_PICO = {
    range(8, 12): 1.2,
    range(12, 14): 1.5,
    range(14, 18): 1.3,
    range(19, 23): 1.8,
}

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def get_peso_horario(hora: int) -> float:
    for horario_range, peso in HORARIOS_PICO.items():
        if hora in horario_range:
            return peso
    return 0.5


def escolher_canal() -> str:
    canais, pesos = zip(*CANAIS_VENDA)
    return random.choices(canais, weights=pesos)[0]


def gerar_id_venda() -> str:
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = random.randint(1000, 9999)
    return f"sal_{timestamp}_{random_suffix}"


def formatar_data_iso(data: datetime) -> str:
    return data.strftime('%Y-%m-%d %H:%M:%S')


def calcular_preco_com_variacao(
    preco_base: float,
    variacao_percentual: float = 0.10
) -> float:
    valor = preco_base + random.uniform(
        -preco_base * variacao_percentual,
        preco_base * variacao_percentual
    )
    return float(f"{valor:.2f}")

# ============================================================
# LEITURA DE DADOS EXISTENTES
# ============================================================

def carregar_clientes() -> List[Dict]:
    try:
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet('clientes')
        records = worksheet.get_all_records()
        return records if records else criar_clientes_exemplo()
    except Exception:
        return criar_clientes_exemplo()


def carregar_produtos() -> List[Dict]:
    try:
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet('produtos')
        records = worksheet.get_all_records()
        return records if records else criar_produtos_exemplo()
    except Exception:
        return criar_produtos_exemplo()


def criar_clientes_exemplo() -> List[Dict]:
    return [
        {'id_cliente': 'cli_001', 'nome_cliente': 'João Silva', 'estado': 'SP', 'pais': 'Brasil'},
        {'id_cliente': 'cli_002', 'nome_cliente': 'Maria Santos', 'estado': 'RJ', 'pais': 'Brasil'},
        {'id_cliente': 'cli_003', 'nome_cliente': 'Pedro Oliveira', 'estado': 'MG', 'pais': 'Brasil'},
        {'id_cliente': 'cli_004', 'nome_cliente': 'Ana Costa', 'estado': 'RS', 'pais': 'Brasil'},
        {'id_cliente': 'cli_005', 'nome_cliente': 'Carlos Souza', 'estado': 'BA', 'pais': 'Brasil'},
    ]


def criar_produtos_exemplo() -> List[Dict]:
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

def gerar_vendas(clientes: List[Dict], produtos: List[Dict]) -> List[List]:
    vendas = []
    total_vendas = 500

    print(f"\n💰 Gerando {total_vendas} vendas...")

    for i in range(total_vendas):
        cliente = random.choice(clientes)
        produto = random.choice(produtos)

        quantidade = random.choices(
            [1, 2, 3, 4, 5],
            weights=[50, 25, 15, 7, 3]
        )[0]

        preco_unitario = calcular_preco_com_variacao(
            float(produto['preco_atual']), 0.05
        )

        venda = [
            gerar_id_venda(),
            formatar_data_iso(datetime.now()),
            cliente['id_cliente'],
            produto['id_produto'],
            escolher_canal(),
            quantidade,
            preco_unitario
        ]

        vendas.append(venda)

        if (i + 1) % 10 == 0:
            time.sleep(5)

    return vendas

# ============================================================
# GERAÇÃO DE PREÇOS DE COMPETIDORES
# ============================================================

def gerar_precos_competidores(produtos: List[Dict]) -> List[List]:
    precos = []

    for produto in produtos:
        preco_base = float(produto['preco_atual'])
        competidores_escolhidos = random.sample(
            COMPETIDORES,
            random.randint(2, 4)
        )

        for competidor in competidores_escolhidos:
            preco = [
                produto['id_produto'],
                competidor,
                calcular_preco_com_variacao(preco_base, 0.20),
                formatar_data_iso(datetime.now())
            ]
            precos.append(preco)

    return precos

# ============================================================
# ESCRITA NO GOOGLE SHEETS
# ============================================================

def adicionar_vendas_sheets(vendas: List[List]) -> bool:
    try:
        worksheet = gc.open(spreadsheet_name).worksheet('vendas')
        worksheet.append_rows(vendas)
        return True
    except Exception as e:
        print(f"❌ Erro ao adicionar vendas: {e}")
        return False


def adicionar_precos_sheets(precos: List[List]) -> bool:
    try:
        worksheet = gc.open(spreadsheet_name).worksheet('preco_competidores')
        worksheet.append_rows(precos)
        return True
    except Exception as e:
        print(f"❌ Erro ao adicionar preços: {e}")
        return False

# ============================================================
# MAIN
# ============================================================

def main():
    print("\n🏪 GERADOR DE VENDAS DIÁRIAS - SIMULADOR ERP\n")

    clientes = carregar_clientes()
    produtos = carregar_produtos()

    vendas = gerar_vendas(clientes, produtos)
    precos = gerar_precos_competidores(produtos)

    adicionar_vendas_sheets(vendas)
    adicionar_precos_sheets(precos)

    print("\n✅ Execução finalizada com sucesso\n")


if __name__ == '__main__':
    main()
