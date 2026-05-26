
# Core.py
# -*- coding: utf-8 -*-

import os
import re
import pandas as pd

# --- CONFIGURACIÓN DE PRECISIÓN Y SALIDA ---
ARCHIVO_ENTRADA = 'data/inputs/NCCkraken_stocks_etfs_ledgers_2021-05-02-2026-04-24.csv'
PRECISION_CRIPTOS = 10
TOLERANCIA_DUST = 1e-7  # Kraken a veces tiene pequeñas discrepancias
PRECISION_SALIDA_CSV = 14  # Decimales máximos a conservar en archivos CSV de salida

# --- CLASIFICACIÓN DE TIPOS SEGÚN REGLA 3.1.4 (BittyTax) ---
TIPOS_ENTRADA_BITTYTAX = {
    "Deposit",
    "Unstake",
    "Mining",
    "Staking-Reward",
    "Staking*",
    "Interest",
    "Dividend",
    "Income",
    "Gift-Received",
    "Fork",
    "Airdrop",
    "Referral",
    "Cashback",
    "Fee-Rebate",
    "Loan",
    "Margin-Gain",
    "Margin-Fee-Rebate",
}

TIPOS_SALIDA_BITTYTAX = {
    "Withdrawal",
    "Stake",
    "Spend",
    "Gift-Sent",
    "Gift-Spouse",
    "Charity-Sent",
    "Lost",
    "Loan-Repayment",
    "Loan-Interest",
    "Margin-Loss",
    "Margin-Fee",
}

# 1. TIPOS QUE SÍ REQUIEREN CÁLCULO FIFO (Generan alteración patrimonial / enajenación)
TIPOS_REALES_BITTYTAX = {
    "Trade",          # Intercambio de activos (la pata de venta consume FIFO)
    "Spend",          # Pago de bienes o servicios con cripto
    "Gift-Sent",      # Donación enviada a un tercero
    "Gift-Spouse",    # Donación enviada al cónyuge
    "Charity-Sent",   # Donación enviada a una ONG
    "Margin-Loss",    # Pérdida por liquidación en operaciones de margen
    "Margin-Fee",     # Pago de comisiones con posición de margen
    "Loan-Repayment", # Devolución del principal de un préstamo usando cripto
    "Loan-Interest",  # Pago de intereses de un préstamo usando cripto

    # A. Entradas de flujos (Crean un lote nuevo en el inventario con coste = valor de mercado)
    "Mining",               # Rendimiento de actividades económicas / minería
    "Staking-Reward",       # Rendimiento del capital mobiliario (Staking)
    "Staking*",             # Variante de la etiqueta de recompensas de staking
    "Interest",             # Intereses generados por plataformas
    "Dividend",             # Dividendos de activos tokenizados
    "Income",               # Otros ingresos genéricos
    "Referral",             # Recompensas por programas de referidos
    "Cashback",             # Devolución de compras en formato token
    "Fee-Rebate",           # Devolución de comisiones de trading
    "Margin-Fee-Rebate",    # Devolución de comisiones de margen
    "Airdrop",              # Distribuciones gratuitas (Ganancia patrimonial base general)
    "Fork",                 # División de cadena (Ganancia patrimonial base general)
    "Gift-Received",        # Cripto recibida como donación (Sujeta a ISD)
    
    # B. Movimientos Neutros o Flujos Internos (No alteran las fechas ni costes de los lotes)
    "Deposit",              # Entrada desde otra wallet propia
    "Withdrawal",           # Salida hacia otra wallet propia
    "Loan",                 # Recepción de un capital prestado (pasivo)
    "Stake",                # Bloqueo de fondos para validación (siguen siendo tuyos)
    "Unstake",              # Desbloqueo de fondos de validación
    
    # C. Bajas Directas (Pérdidas sin contraprestación)
    "Lost"                  # Robo, estafa o pérdida de llaves (Baja directa a coste de adquisición)
}

# 2. TIPOS QUE NO REQUIEREN FIFO (Solo ajuste de inventario: Entradas, transferencias o bajas directas)
TIPOS_NEUTROS_BITTYTAX = [
    # B. Movimientos Neutros o Flujos Internos (No alteran las fechas ni costes de los lotes)
    "Stake",                # Bloqueo de fondos para validación (siguen siendo tuyos)
    "Unstake",              # Desbloqueo de fondos de validación
]

# --- TIPOS REALES (KRAKEN LEDGER FORMAT) ---
# Tipos de transacción en formato Kraken que generan movimiento real de activos
TIPOS_REALES_KRAKEN = [
    # Tradicionales e Intercambios
    'trade',             # Intercambio estándar en el mercado Spot
    'spend',             # Pata de salida al usar "Buy Crypto" / Nueva App
    'receive',           # Pata de entrada al usar "Buy Crypto" / Nueva App
    'conversion',        # Conversiones directas de activos integradas

    # Financiación (Flujos de entrada/salida)
    'deposit',           # Depósito de fondos (Fiat o Crypto)
    'withdrawal',        # Retirada de fondos (Fiat o Crypto)
    'transfer',          # Transferencias internas (ej. de cuenta Spot a Futuros)
    'custodytransfer',   # Transferencias desde/hacia billeteras de custodia

    # Rendimientos y Recompensas
    'staking',           # Recompensas de staking (histórico y transiciones)
    'earn',              # Nuevas distribuciones de rendimiento, incentivos o airdrops
    'reward',            # Recompensas generales de la plataforma
    'dividend',          # Dividendos de activos que apliquen

    # Operaciones de Margen (Apalancamiento)
    'margin',            # Apertura, cierre o ejecuciones de posiciones de margen
    'settled',           # Liquidación de una posición de margen en spot
    'rollover',          # Tarifas de renovación de posiciones de margen abiertas

    # Ajustes y Créditos
    'adjustment',        # Conversión forzada fuera de mercado (ej. delisting de un token)
    'credit',            # Créditos manuales o promocionales otorgados por Kraken
    
    # Ecosistema NFT
    'sale',              # Filtro general de ventas de la app o mercado NFT
    'nfttrade',          # Intercambio o compra/venta de NFTs
    'nftcreatorfee',     # Cobro de royalties/tarifas de creador de NFT
    'nftrebate',         # Reembolsos o devoluciones asociadas a NFTs
    
    # Control del sistema
    'none'               # Registro de control nulo o vacío
]


def format_float_output(x):
    """
    Formatea floats removiendo ceros al final pero manteniendo decimales no-cero.
    Ejemplos:
    - 1.5 -> '1.5'
    - 1.0 -> '1'
    - 0.00000001 -> '0.00000001'
    - 1.50000000 -> '1.5'
    """
    if pd.isna(x):
        return ''
    # Convertir a float por si acaso
    x = float(x)
    # Formatear con precisión máxima
    s = f'{x:.{PRECISION_SALIDA_CSV}f}'
    # Remover ceros al final pero mantener al menos el número entero
    s = s.rstrip('0').rstrip('.')
    return s


def normalizar_activo(asset):
    """Normaliza codigos de activos usados por Kraken."""
    if pd.isna(asset):
        return asset

    asset = str(asset).strip().upper()
    asset = asset.split('.')[0]  # Kraken a menudo tiene sufijos de clase (ej. DOT.2, USDT.3)
    match = re.fullmatch(r"([A-Z]+)\d{2}", asset)

    return match.group(1) if match else asset

# --- FILTROS PARA INFORME FISCAL (Fiscal_Reporter_ES) ---
# Tipos de transacción para cada categoría de reporte fiscal
TRADING_REPORT_TYPES_KRAKEN = ['trade', 'spend', 'receive', 'conversion', 
    'margin', 'settled', 'rollover', 
    'nfttrade', 'sale', 'nftcreatorfee']  # Transmisiones/Permutas (venta de activos)

TRADING_REPORT_TYPES_BITTYTAX = {
    "Trade", 
    "Margin-Loss", 
    "Margin-Fee", 
    "Spend", 
    "Gift-Sent", 
    "Gift-Spouse", 
    "Charity-Sent"
}
AIRDROP_SUBTYPES_KRAKEN = ['airdrop']   # Subtipos para identificar regalos/airdrops

AIRDROP_TYPES_BITTYTAX = [
    "Airdrop", 
    "Fork", 
    "Referral", 
    "Cashback", 
    "Gift-Received"
]

RENDIMIENTOS_REPORT_TYPES_BITTYTAX = [
    "Staking-Reward", 
    "Staking*", 
    "Interest", 
    "Dividend",
    "Mining"  # Etiqueta con tratamiento de actividad económica
]

RENDIMIENTOS_REPORT_TYPES_KRAKEN = ['staking', 'earn', 'dividend', 'lending', 'reward']  # Rendimientos del capital mobiliario

# Detectar si estamos en Google Colab
try:
    import google.colab
    IN_COLAB = True
except:
    IN_COLAB = False


def recognize_csv_format(columns):
    """
    Recognizes whether a CSV file matches BittyTax export format, 
    Kraken Ledger format, or is unknown, based on its column names.
    
    Parameters:
        columns (list or Index): List of column names from the CSV file.
        
    Returns:
        str: 'bittytax', 'kraken', or 'unknown'
    """
    # Normalize inputs to lowercase and stripped spaces for robust matching
    input_cols = {str(col).strip().lower() for col in columns}
    
    if not input_cols:
        return "unknown"
        
    # Expected standard column definitions
    bittytax_signature = {
        "type", "buy quantity", "buy asset", "buy value", 
        "sell quantity", "sell asset", "sell value", 
        "fee quantity", "fee asset", "fee value", 
        "wallet", "timestamp", "note"
    }
    
    kraken_raw_signature = {
        "txid", "refid", "time", "type", "subtype",
        "aclass", "subclass", "asset", "wallet",
        "amount", "fee", "balance"
    }

    kraken_enriched_signature = {
        "txid", "refid", "time", "type", "subtype", 
        "aclass", "subclass", "asset", "wallet", 
        "amount", "fee", "balance", "orden_original", 
        "amount_eur", "fee_eur", "tasa", "eur_conversion", 
        "legs_subclasses"
    }
    
    # Calculate matching ratios to allow flexibility with partial headers
    bittytax_match_ratio = len(input_cols.intersection(bittytax_signature)) / len(bittytax_signature)
    kraken_raw_match_ratio = len(input_cols.intersection(kraken_raw_signature)) / len(kraken_raw_signature)
    kraken_enriched_match_ratio = len(input_cols.intersection(kraken_enriched_signature)) / len(kraken_enriched_signature)
    kraken_match_ratio = max(kraken_raw_match_ratio, kraken_enriched_match_ratio)
    
    # Threshold definition (e.g., 75% of columns must match perfectly)
    match_threshold = 0.75
    
    if bittytax_match_ratio > kraken_match_ratio and bittytax_match_ratio >= match_threshold:
        return "bittytax"
    elif kraken_match_ratio > bittytax_match_ratio and kraken_match_ratio >= match_threshold:
        return "kraken"
        
    return "unknown"

# Función de utilidad para asegurar carpetas
def asegurar_directorios():
    for folder in ['data/inputs', 'data/temp', 'data/outputs']:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"📁 Carpeta creada: {folder}")

# Llamada automática al importar Core
asegurar_directorios()
