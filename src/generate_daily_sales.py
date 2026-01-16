"""
Script Gerador de Vendas Diárias - Simulador de ERP
====================================================

- 500 vendas/dia
- Inserção em pacotes de 100
- Preços como valores NUMÉRICOS (float) para Supabase
- Datas no formato "YYYY-MM-DD HH:MM:SS"
- Preço de competidores: 1 linha por dia por concorrente
- id_cliente e id_produto respeitam dados existentes
- canal_venda apenas "Loja Física" ou "Ecommerce"
"""

import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

# ============================================================
# SETUP
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

CREDENTIALS_PATH = ROOT_DIR / "credentials" / "credentials.json"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

if not CREDENTIALS_PATH.exists():
    raise FileNotFoundError(f"Credenciais não encontradas: {CREDENTIALS_PATH}")

creds = ServiceAccountCredentials.from_json_keyfile_name(
    str(CREDENTIALS_PATH), scope
)
gc = gspread.authorize(creds)

SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "Dados do ecommerce")

# ============================================================
# CONSTANTES
# ============================================================

TOTAL_VENDAS_DIA = 500
BATCH_SIZE = 100

HORARIO_INICIO = 8
HORARIO_FIM = 23

CANAIS_VALIDOS = ["loja_fisica", "ecommerce"]

COMPETIDORES = [
    "Mercado Livre",
    "Amazon",
    "Magalu",
    "Americanas",
    "Shopee",
    "AliExpress",
]

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def escolher_canal() -> str:
    return random.choice(CANAIS_VALIDOS)


def gerar_id_venda() -> str:
    return f"sal_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000,9999)}"


def formatar_data_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def gerar_preco_numerico(base: float, variacao: float) -> float:
    valor = base + random.uniform(-base * variacao, base * variacao)
    return round(valor, 2)


def gerar_timestamps_dia(data_base: datetime, quantidade: int) -> List[datetime]:
    inicio = data_base.replace(hour=HORARIO_INICIO, minute=0, second=0)
    fim = data_base.replace(hour=HORARIO_FIM, minute=0, second=0)

    delta_total = (fim - inicio).total_seconds()
    intervalo = delta_total / quantidade

    return [
        inicio + timedelta(seconds=i * intervalo + random.randint(0, 120))
        for i in range(quantidade)
    ]

# ============================================================
# LEITURA DE DADOS
# ============================================================

def carregar_clientes() -> List[Dict]:
    try:
        return gc.open(SPREADSHEET_NAME).worksheet("clientes").get_all_records()
    except Exception:
        # fallback com IDs fictícios
        return [
            {"id_cliente": "cli_001"},
            {"id_cliente": "cli_002"},
            {"id_cliente": "cli_003"},
        ]


def carregar_produtos() -> List[Dict]:
    try:
        return gc.open(SPREADSHEET_NAME).worksheet("produtos").get_all_records()
    except Exception:
        # fallback com produtos fictícios
        return [
            {"id_produto": "prd_001", "preco_atual": 3500.00},
            {"id_produto": "prd_002", "preco_atual": 89.90},
            {"id_produto": "prd_003", "preco_atual": 450.00},
        ]

# ============================================================
# GERAÇÃO + INSERÇÃO DE VENDAS (BATCHES)
# ============================================================

def gerar_e_inserir_vendas():
    clientes = carregar_clientes()
    produtos = carregar_produtos()
    worksheet = gc.open(SPREADSHEET_NAME).worksheet("vendas")

    data_base = datetime.now()
    timestamps = gerar_timestamps_dia(data_base, TOTAL_VENDAS_DIA)

    for batch_inicio in range(0, TOTAL_VENDAS_DIA, BATCH_SIZE):
        batch = []

        for i in range(batch_inicio, min(batch_inicio + BATCH_SIZE, TOTAL_VENDAS_DIA)):
            produto = random.choice(produtos)
            cliente = random.choice(clientes)

            batch.append([
                gerar_id_venda(),
                formatar_data_iso(timestamps[i]),
                cliente["id_cliente"],
                produto["id_produto"],
                escolher_canal(),
                random.randint(1, 5),
                gerar_preco_numerico(float(produto["preco_atual"]), 0.05),
            ])

        worksheet.append_rows(batch, value_input_option="RAW")
        print(f"✅ Inserido lote de vendas {batch_inicio + 1}–{min(batch_inicio + BATCH_SIZE, TOTAL_VENDAS_DIA)}")
        time.sleep(2)

# ============================================================
# PREÇOS DE COMPETIDORES (1 POR DIA / CONCORRENTE)
# ============================================================

def gerar_e_inserir_precos_competidores():
    produtos = carregar_produtos()
    worksheet = gc.open(SPREADSHEET_NAME).worksheet("preco_competidores")

    # Apenas 1 produto de referência para o dia
    produto_referencia = random.choice(produtos)
    base = float(produto_referencia["preco_atual"])
    data_coleta = formatar_data_iso(datetime.now())

    linhas = []

    for concorrente in COMPETIDORES:
        linhas.append([
            produto_referencia["id_produto"],
            concorrente,
            gerar_preco_numerico(base, 0.20),
            data_coleta,
        ])

    worksheet.append_rows(linhas, value_input_option="RAW")
    print(f"✅ Inseridos {len(linhas)} preços diários de competidores")

# ============================================================
# MAIN
# ============================================================

def main():
    print("🚀 Iniciando geração de dados\n")
    gerar_e_inserir_vendas()
    gerar_e_inserir_precos_competidores()
    print("\n✅ Processo finalizado com sucesso")

if __name__ == "__main__":
    main()
