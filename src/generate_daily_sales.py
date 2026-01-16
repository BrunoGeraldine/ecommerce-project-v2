"""
Script Gerador de Vendas - Simulador de ERP (3 vendas por ciclo)
===============================================================

- 3 vendas a cada execução (ideal para rodar a cada 5 minutos)
- ~864 vendas/dia (3 × 288 ciclos)
- Preços como float (compatível com Supabase/PostgreSQL)
- Datas no formato "YYYY-MM-DD HH:MM:SS"
- id_cliente e id_produto de planilha ou fallback
- canal_venda: "loja_fisica" ou "ecommerce"
- Preços de competidores: apenas 1 execução por dia
"""

import os
import sys
import random
import time
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

creds = ServiceAccountCredentials.from_json_keyfile_name(str(CREDENTIALS_PATH), scope)
gc = gspread.authorize(creds)

SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "Dados do ecommerce")

# ============================================================
# CONFIGURAÇÃO
# ============================================================

VENDAS_POR_CICLO = 3
BATCH_SIZE = VENDAS_POR_CICLO   # pequeno batch, já que são poucas linhas

HORARIO_INICIO = 8
HORARIO_FIM   = 23

CANAIS_VALIDOS = ["loja_fisica", "ecommerce"]

COMPETIDORES = [
    "Mercado Livre", "Amazon", "Magalu",
    "Americanas", "Shopee", "AliExpress",
]

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def escolher_canal() -> str:
    return random.choice(CANAIS_VALIDOS)


def gerar_id_venda() -> str:
    agora = datetime.now()
    return f"sal_{agora.strftime('%Y%m%d%H%M%S')}_{random.randint(10000,99999)}"


def formatar_data_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def gerar_preco_numerico(base: float, variacao: float = 0.05) -> float:
    valor = base + random.uniform(-base * variacao, base * variacao)
    return round(valor, 2)


def esta_dentro_do_horario_agora() -> bool:
    agora = datetime.now()
    return HORARIO_INICIO <= agora.hour < HORARIO_FIM


def gerar_timestamp_proximo() -> datetime:
    """
    Gera um timestamp realista para o ciclo atual:
    - Se estiver dentro do horário → usa hora atual ± até ~4 min
    - Fora do horário → gera dentro do horário de funcionamento do dia
    """
    agora = datetime.now()

    if esta_dentro_do_horario_agora():
        # pequena variação em torno do momento atual
        segundos_variacao = random.randint(-240, 240)  # ±4 minutos
        return agora + timedelta(seconds=segundos_variacao)

    # Fora do horário → distribui no horário de funcionamento
    inicio = agora.replace(hour=HORARIO_INICIO, minute=0, second=0, microsecond=0)
    fim   = agora.replace(hour=HORARIO_FIM,   minute=0, second=0, microsecond=0)

    if agora.hour < HORARIO_INICIO:
        base = inicio
    else:
        base = fim - timedelta(hours=3)  # tende a colocar mais pro final do dia anterior

    segundos_no_dia = (fim - inicio).total_seconds()
    offset = random.uniform(0, segundos_no_dia)
    return inicio + timedelta(seconds=offset)


# ============================================================
# LEITURA DE DADOS (clientes e produtos)
# ============================================================

def carregar_clientes() -> List[Dict]:
    try:
        return gc.open(SPREADSHEET_NAME).worksheet("clientes").get_all_records()
    except Exception:
        return [{"id_cliente": f"cli_{i:03d}"} for i in range(1, 21)]


def carregar_produtos() -> List[Dict]:
    try:
        return gc.open(SPREADSHEET_NAME).worksheet("produtos").get_all_records()
    except Exception:
        return [
            {"id_produto": "prd_001", "preco_atual": 3499.90},
            {"id_produto": "prd_002", "preco_atual":  89.90},
            {"id_produto": "prd_003", "preco_atual": 449.00},
            {"id_produto": "prd_004", "preco_atual": 1299.00},
        ]


# ============================================================
# GERAÇÃO E INSERÇÃO DAS 3 VENDAS
# ============================================================

def gerar_e_inserir_vendas_do_ciclo():
    clientes = carregar_clientes()
    produtos = carregar_produtos()
    worksheet = gc.open(SPREADSHEET_NAME).worksheet("vendas")

    batch = []

    for _ in range(VENDAS_POR_CICLO):
        produto = random.choice(produtos)
        cliente = random.choice(clientes)

        preco_venda = gerar_preco_numerico(float(produto["preco_atual"]))

        linha = [
            gerar_id_venda(),
            formatar_data_iso(gerar_timestamp_proximo()),
            cliente["id_cliente"],
            produto["id_produto"],
            escolher_canal(),
            random.randint(1, 5),               # quantidade
            preco_venda,
        ]
        batch.append(linha)

    worksheet.append_rows(batch, value_input_option="RAW")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Inseridas {len(batch)} vendas")


# ============================================================
# PREÇOS DE COMPETIDORES — apenas 1x por dia
# ============================================================

def deve_atualizar_precos_competidores() -> bool:
    """Executa apenas na primeira hora do dia (ex: 00:xx até 00:59)"""
    return datetime.now().hour == 0


def gerar_e_inserir_precos_competidores():
    if not deve_atualizar_precos_competidores():
        return

    produtos = carregar_produtos()
    worksheet = gc.open(SPREADSHEET_NAME).worksheet("preco_competidores")

    produto_ref = random.choice(produtos)
    base = float(produto_ref["preco_atual"])
    data_coleta = formatar_data_iso(datetime.now())

    linhas = []
    for concorrente in COMPETIDORES:
        linhas.append([
            produto_ref["id_produto"],
            concorrente,
            gerar_preco_numerico(base, variacao=0.18),
            data_coleta,
        ])

    worksheet.append_rows(linhas, value_input_option="RAW")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Inseridos {len(linhas)} preços de competidores")


# ============================================================
# MAIN
# ============================================================

def main():
    print("Iniciando ciclo de geração de vendas...")
    
    gerar_e_inserir_precos_competidores()   # só roda 1x/dia
    gerar_e_inserir_vendas_do_ciclo()

    print("Ciclo concluído.\n")


if __name__ == "__main__":
    main()