
# Fiscal_Reporter_ES.py
# -*- coding: utf-8 -*-

import pandas as pd
import pickle
from datetime import datetime

from Core import ARCHIVO_ENTRADA

def generar_informe_fiscal(archivo_fifo, anio_fiscal=None, informe_fiscal=None):
    if anio_fiscal is None:
        anio_fiscal = datetime.now().year - 1
    
    print(f"📊 Generando informe fiscal para el año {anio_fiscal}...")
    
    df = pd.read_csv(archivo_fifo)
    df['time'] = pd.to_datetime(df['time'])
    
    # Filtrar datos del año solicitado
    df_year = df[df['time'].dt.year == anio_fiscal].copy()
    
    # --- 1. TRADING (Transmisión/Permuta) ---
    # Solo ventas/trades con ganancia/pérdida calculada
    trading = df_year[
        #(df_year['asset'] != 'EUR') & 
        (df_year['type'].isin(['trade', 'spend'])) & 
        (df_year['amount'] < 0)
    ].copy()
    
    trading['Fecha de transmisión'] = trading['time'].dt.date
    trading['Fecha de adquisición'] = pd.to_datetime(
        trading['FIFO_calculation'].str.extract(r'fecha\s+(\d{4}-\d{2}-\d{2})')[0],
        errors='coerce'
    ).dt.date
    trading['Valor de adquisicion bruto'] = trading['Valor de adquisicion']
    trading['Valor de adquisicion'] = trading['Valor de adquisicion'] - trading['fee_eur']
    trading['Gastos de transmision'] = trading['fee_eur']
    trading['legs_subclasses'] = trading['legs_subclasses'].str.replace('stable_coin', 'crypto')
    #trading['legs_subclasses'] = trading['legs_subclasses']
    
    reporte_trading = trading[['time', 'asset', 'amount', 'amount_eur', 'fee_eur', 'ganancia_fifo', 'FIFO_calculation', 'Fecha de transmisión', 'Fecha de adquisición', 'Valor de transmision', 'Valor de adquisicion bruto', 'Valor de adquisicion', 'Gastos de transmision', 'legs_subclasses', 'refid', 'fee_eur_compras']]
    reporte_trading.rename(columns={'fee_eur_compras': 'Gastos_adquisicion'}, inplace=True)
    
    # --- 2. AIRDROPS / REGALOS (Sin transmisión) ---
    # Ganancias que no derivan de una venta previa
    airdrops = df_year[
        (df_year['asset'] != 'EUR') & 
        (df_year['type'].isin(['airdrop', 'bonus']))
    ].copy()
    reporte_airdrops = airdrops[['time', 'asset', 'amount', 'amount_eur', 'fee', 'fee_eur', 'refid']]

    # --- 3. RENDIMIENTOS CAPITAL MOBILIARIO (Staking, Intereses) ---
    # Rentas del ahorro
    rendimientos = df_year[df_year['type'].isin(['staking', 'earn', 'dividend', 'lending'])].copy()
    reporte_rendimientos = rendimientos[['time', 'asset', 'amount', 'amount_eur', 'fee', 'fee_eur', 'type', 'refid']]

    # --- 4. BALANCES (1 Ene y 31 Dic) ---
    archivo_inventarios = ARCHIVO_ENTRADA.replace('inputs', 'temp').replace('.csv', '_inventarios_fifo.pkl')
    try:
        with open(archivo_inventarios, 'rb') as f:
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
        print("⚠️ No se encontró el archivo de inventarios {}. Ejecuta FIFO_calculator actualizado.")
        balance_inicio = balance_cierre = pd.DataFrame()

    # --- RESÚMENES POR ACTIVO ---
    # Trading por activo
    if not trading.empty:
        resumen_trading = trading.groupby(['asset', 'legs_subclasses']).agg({
            'amount': 'sum',
            'amount_eur': 'sum',
            'fee_eur': 'sum',
            'ganancia_fifo': 'sum',
            'Valor de transmision': 'sum',
            'Valor de adquisicion bruto': 'sum',
            'Valor de adquisicion': 'sum',
            'fee_eur_compras': 'sum',
            'Fecha de transmisión': 'max',
            'Fecha de adquisición': 'min'
        }).round(2).reset_index()
        resumen_trading.columns = ['Asset', 'Legs_Subclasses', 'Cantidad_Total', 'Valor_EUR', 'Gastos_transmision', 'Ganancia_FIFO', 'Valor_Transmision', 'Valor_Adquisicion_Bruto', 'Valor_Adquisicion', 'Gastos_adquisicion', 'Fecha_transmision', 'Fecha_adquisicion']
    else:
        resumen_trading = pd.DataFrame()
    
    # Airdrops por activo
    if not airdrops.empty:
        resumen_airdrops = airdrops.groupby('asset').agg({
            'amount': 'sum',
            'amount_eur': 'sum',
            'fee': 'sum',
            'fee_eur': 'sum'
        }).round(2).reset_index()
        resumen_airdrops.columns = ['Asset', 'Cantidad_Total', 'Valor_EUR', 'Fee', 'Fee_EUR']
    else:
        resumen_airdrops = pd.DataFrame()
    
    # Rendimientos por activo
    if not rendimientos.empty:
        resumen_rendimientos = rendimientos.groupby('asset').agg({
            'amount': 'sum',
            'amount_eur': 'sum',
            'fee': 'sum',
            'fee_eur': 'sum'
        }).round(2).reset_index()
        resumen_rendimientos.columns = ['Asset', 'Cantidad_Total', 'Valor_EUR', 'Fee', 'Fee_EUR']
    else:
        resumen_rendimientos = pd.DataFrame()

    # --- ESCRITURA A EXCEL ---
    #ruta_actual = os.getcwd()
    #nombre_excel = f"{ruta_actual}/{informe_fiscal}_{anio_fiscal}.xlsx"
    nombre_excel = f"{informe_fiscal}_{anio_fiscal}.xlsx"
    with pd.ExcelWriter(nombre_excel, engine='xlsxwriter') as writer:
        # Resúmenes por activo
        resumen_trading.to_excel(writer, sheet_name='1a. Trading_Resumen', index=False)
        reporte_trading.to_excel(writer, sheet_name='1b. Trading_Detalle', index=False)
        
        resumen_airdrops.to_excel(writer, sheet_name='2a. Airdrops_Resumen', index=False)
        reporte_airdrops.to_excel(writer, sheet_name='2b. Airdrops_Detalle', index=False)
        
        resumen_rendimientos.to_excel(writer, sheet_name='3a. Rendimientos_Resumen', index=False)
        reporte_rendimientos.to_excel(writer, sheet_name='3b. Rendimientos_Detalle', index=False)
        
        balance_inicio.to_excel(writer, sheet_name='4a. Balance_1-Ene', index=False)
        balance_cierre.to_excel(writer, sheet_name='4b. Balance_31-Dic', index=False)

        # --- NUEVA PESTAÑA: DATOS DE ENTRADA ---
        # Guardamos el histórico completo que se usó para este año, 
        # incluyendo las filas de EUR para que la trazabilidad sea total.
        df_year.to_excel(writer, sheet_name='5. Datos_Entrada', index=False)

        # Formatos básicos
        workbook = writer.book
        fmt_money = workbook.add_format({'num_format': '#,##0.00€'})
        for sheet in writer.sheets.values():
            sheet.set_column('C:G', 15, fmt_money)

    print(f"✅ Informe Excel guardado como: {nombre_excel}")

if __name__ == "__main__":
    # Ajustar nombres de ficheros según tu configuración
    generar_informe_fiscal(ARCHIVO_ENTRADA.replace('inputs', 'temp').replace('.csv', '_FIFO.csv'), 
                           anio_fiscal=2025, 
                           informe_fiscal=ARCHIVO_ENTRADA.replace('inputs', 'outputs').replace('.csv', '_Informe_Fiscal'))