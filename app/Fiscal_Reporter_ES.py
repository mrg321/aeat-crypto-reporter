
# core.py
# -*- coding: utf-8 -*-

import os

import pandas as pd
import pickle
from datetime import datetime

from Core import ARCHIVO_FIFO, INFORME_FISCAL, INVENTARIOS_FIFO

def generar_informe_fiscal(archivo_fifo, anio_fiscal=None, informe_fiscal= INFORME_FISCAL):
    if anio_fiscal is None:
        anio_fiscal = datetime.now().year - 1
    
    print(f"📊 Generando informe fiscal para el año {anio_fiscal}...")
    
    df = pd.read_csv(archivo_fifo)
    df['time'] = pd.to_datetime(df['time'])
    
    # Filtrar datos del año solicitado
    df_year = df[df['time'].dt.year == anio_fiscal].copy()
    
    # --- 1. TRADING (Transmisión/Permuta) ---
    # Solo ventas/trades con ganancia/pérdida calculada
    trading = df_year[(df_year['type'].isin(['trade', 'spend'])) & (df_year['amount'] < 0)].copy()
    reporte_trading = trading[['time', 'asset', 'amount', 'amount_eur', 'fee_eur', 'ganancia_fifo', 'refid']]
    
    # --- 2. AIRDROPS / REGALOS (Sin transmisión) ---
    # Ganancias que no derivan de una venta previa
    airdrops = df_year[df_year['type'].isin(['receive', 'airdrop', 'bonus'])].copy()
    reporte_airdrops = airdrops[['time', 'asset', 'amount', 'amount_eur', 'refid']]

    # --- 3. RENDIMIENTOS CAPITAL MOBILIARIO (Staking, Intereses) ---
    # Rentas del ahorro
    rendimientos = df_year[df_year['type'].isin(['staking', 'earn', 'dividend', 'lending'])].copy()
    reporte_rendimientos = rendimientos[['time', 'asset', 'amount', 'amount_eur', 'type', 'refid']]

    # --- 4. BALANCES (1 Ene y 31 Dic) ---
    try:
        with open(INVENTARIOS_FIFO, 'rb') as f:
            inventarios = pickle.load(f)
            
        def procesar_inventario(anio):
            datos = []
            if anio in inventarios:
                for asset, lotes in inventarios[anio].items():
                    cant_total = sum(l['cantidad'] for l in lotes)
                    valor_eur = sum(l['cantidad'] * l['coste_unitario'] for l in lotes)
                    if cant_total > 1e-8:
                        datos.append({'Asset': asset, 'Cantidad': cant_total, 'Valor_Euros': valor_eur})
            return pd.DataFrame(datos)

        balance_inicio = procesar_inventario(anio_fiscal - 1)
        balance_cierre = procesar_inventario(anio_fiscal)
    except FileNotFoundError:
        print("⚠️ No se encontró el archivo de inventarios. Ejecuta FIFO_calculator actualizado.")
        balance_inicio = balance_cierre = pd.DataFrame()

    # --- ESCRITURA A EXCEL ---
    ruta_actual = os.getcwd()
    nombre_excel = f"{ruta_actual}/{informe_fiscal}_{anio_fiscal}.xlsx"
    with pd.ExcelWriter(nombre_excel, engine='xlsxwriter') as writer:
        reporte_trading.to_excel(writer, sheet_name='1. Trading', index=False)
        reporte_airdrops.to_excel(writer, sheet_name='2. Airdrops_Premios', index=False)
        reporte_rendimientos.to_excel(writer, sheet_name='3. Rendimientos_Capital', index=False)
        balance_inicio.to_excel(writer, sheet_name='4a. Balance_1-Ene', index=False)
        balance_cierre.to_excel(writer, sheet_name='4b. Balance_31-Dic', index=False)
        
        # Formatos básicos
        workbook = writer.book
        fmt_money = workbook.add_format({'num_format': '#,##0.00€'})
        for sheet in writer.sheets.values():
            sheet.set_column('C:G', 15, fmt_money)

    print(f"✅ Informe Excel guardado como: {nombre_excel}")

if __name__ == "__main__":
    # Ajustar nombres de ficheros según tu configuración
    generar_informe_fiscal(ARCHIVO_FIFO, anio_fiscal=2025)