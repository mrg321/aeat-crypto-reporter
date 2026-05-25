
# Fiscal_Reporter_ES.py
# -*- coding: utf-8 -*-

import pandas as pd
import json
from datetime import datetime

from Core import AIRDROP_SUBTYPES_KRAKEN, ARCHIVO_ENTRADA, RENDIMIENTOS_REPORT_TYPES_KRAKEN
from Core import RENDIMIENTOS_REPORT_TYPES_KRAKEN, TOLERANCIA_DUST, TRADING_REPORT_TYPES_KRAKEN
from Core import TRADING_REPORT_TYPES_BITTYTAX, AIRDROP_TYPES_BITTYTAX, RENDIMIENTOS_REPORT_TYPES_BITTYTAX

def generar_informe_fiscal(archivo_fifo, anio_fiscal=None, informe_fiscal=None):
    if anio_fiscal is None:
        anio_fiscal = datetime.now().year - 1
    
    print(f"📊 Generando informe fiscal para el año {anio_fiscal}...")
    
    df = pd.read_csv(archivo_fifo)
    df['time'] = pd.to_datetime(df['time'])

    # Excel does not support datetimes with timezones. 
    # Ensure all datetime columns are timezone-unaware.
    for col in df.select_dtypes(include=['datetime64[ns, UTC]', 'datetimetz']).columns:
        df[col] = df[col].dt.tz_localize(None)
    
    
    # Filtrar datos del año solicitado
    df_year = df[df['time'].dt.year == anio_fiscal].copy()
    
    # --- 1. TRADING (Transmisión/Permuta) ---
    # Solo ventas/trades con ganancia/pérdida calculada
    trading = df_year[
        (df_year['type'].isin(TRADING_REPORT_TYPES_KRAKEN) | df_year['type'].isin(TRADING_REPORT_TYPES_BITTYTAX)) & 
        (df_year['amount'] < 0)
    ].copy()
    
    trading['Fecha de transmisión'] = trading['time'].dt.normalize()
    trading['Fecha de adquisición'] = pd.to_datetime(
        trading['FIFO_calculation'].str.extract(r'fecha\s+(\d{4}-\d{2}-\d{2})')[0],
        errors='coerce'
    )
    #trading['Valor de adquisicion bruto'] = trading['Valor de adquisicion']
    #trading['Valor de adquisicion'] = trading['Valor de adquisicion'] - trading['fee_eur']
    trading['Gastos de transmision'] = trading['fee_eur']
    #trading['legs_subclasses'] = trading['legs_subclasses'].str.replace('stable_coin', 'crypto')
    trading['legs_subclasses'] = trading['legs_subclasses']
    
    reporte_trading = trading[['time', 'asset', 'amount', 'amount_eur', 'fee_eur', 
                               'ganancia_fifo', 'FIFO_calculation', 'Fecha de transmisión', 
                               'Fecha de adquisición', 'Valor de transmision', 
                               #'Valor de adquisicion bruto', 
                               'Valor de adquisicion', 'Gastos de transmision', 'legs_subclasses', 
                               'refid', 'fee_eur_compras']]
    reporte_trading.rename(columns={
        'fee_eur_compras': 'Gastos de adquisicion (ya incluidos)',
        'Gastos de transmision': 'Gastos de transmision (ya incluidos)'
    }, inplace=True)
    
    # --- 2. AIRDROPS / REGALOS (Sin transmisión) ---
    # Ganancias que no derivan de una venta previa
    airdrops = df_year[
        (df_year['asset'] != 'EUR') & 
        ((df_year['type'] == 'earn') & (df_year['subtype'].isin(AIRDROP_SUBTYPES_KRAKEN)) |
         (df_year['type'].isin(AIRDROP_TYPES_BITTYTAX))) &
        (~df_year['FIFO_calculation'].str.contains('Neutral movement', na=False))
    ].copy()
    reporte_airdrops = airdrops[['time', 'asset', 'amount', 'amount_eur', 'fee', 'fee_eur', 'refid']]

    # --- 3. RENDIMIENTOS CAPITAL MOBILIARIO (Staking, Intereses) ---
    # Rentas del ahorro
    rendimientos = df_year[
        (df_year['type'].isin(RENDIMIENTOS_REPORT_TYPES_KRAKEN) |
         df_year['type'].isin(RENDIMIENTOS_REPORT_TYPES_BITTYTAX)) &
        (~df_year['FIFO_calculation'].str.contains('Neutral movement', na=False)) &
        (~df_year['subtype'].isin(AIRDROP_SUBTYPES_KRAKEN))  # Excluir airdrops que ya se cuentan en el punto 2
    ].copy()
    reporte_rendimientos = rendimientos[['time', 'asset', 'amount', 'amount_eur', 'fee', 'fee_eur', 'type', 'refid']]

    # --- 4. BALANCES (1 Ene y 31 Dic) ---
    archivo_inventarios = archivo_fifo.replace('_converted_pro_FIFO.csv', '_inventarios_fifo.json')
    try:
        with open(archivo_inventarios, 'r') as f:
            inventarios = json.load(f)

        def procesar_inventario(anio):
            datos = []
            # Convertimos el año a string para asegurar la compatibilidad con las claves de JSON
            anio_str = str(anio)
            
            if anio_str in inventarios:
                for asset, lotes in inventarios[anio_str].items():
                    # Usamos .get() por seguridad y aseguramos que cantidad y coste sean floats
                    cant_total = sum(float(l.get('cantidad', 0)) for l in lotes)
                    valor_eur = sum(float(l.get('cantidad', 0)) * float(l.get('coste_unitario', 0)) for l in lotes)
                    
                    if cant_total > TOLERANCIA_DUST:  # Solo incluir activos con cantidad significativa
                        datos.append({
                            'Asset': asset, 
                            'Cantidad': cant_total, 
                            'Valor_Euros': valor_eur
                        })
            
            return pd.DataFrame(datos)
        
        balance_inicio = procesar_inventario(anio_fiscal - 1)
        balance_cierre = procesar_inventario(anio_fiscal)
    except FileNotFoundError:
        print(f"⚠️ No se encontró el archivo de inventarios {archivo_inventarios}. Ejecuta FIFO_calculator actualizado.")
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
            #'Valor de adquisicion bruto': 'sum',
            'Valor de adquisicion': 'sum',
            'fee_eur_compras': 'sum',
            'Fecha de transmisión': 'max',
            'Fecha de adquisición': 'min'
        }).reset_index()
        resumen_trading.columns = ['Asset', 'Legs_Subclasses', 'Cantidad_Total', 'Valor_EUR', 
                                   'Gastos de transmision (ya incluidos)', 'Ganancia_FIFO', 'Valor_Transmision', 
                                   #'Valor_Adquisicion_Bruto', 
                                   'Valor_Adquisicion', 'Gastos de adquisicion (ya incluidos)', 'Fecha_transmision', 
                                   'Fecha_adquisicion']
    else:
        resumen_trading = pd.DataFrame()
    
    # Airdrops por activo
    if not airdrops.empty:
        resumen_airdrops = airdrops.groupby('asset').agg({
            'amount': 'sum',
            'amount_eur': 'sum',
            'fee': 'sum',
            'fee_eur': 'sum'
        }).reset_index()
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
        }).reset_index()
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
        #workbook = writer.book
        #fmt_money = workbook.add_format({'num_format': '#,##0.00€'})
        #for sheet in writer.sheets.values():
        #    sheet.set_column('D:G', 15, fmt_money)

    print(f"✅ Informe Excel guardado como: {nombre_excel}")

if __name__ == "__main__":
    # Ajustar nombres de ficheros según tu configuración
    archivo_original = ARCHIVO_ENTRADA
    if "BittyTax" in archivo_original:
        archivo_entrada = archivo_original.replace('inputs', 'temp').replace('.csv', '_converted_from_bittytax_converted_pro_FIFO.csv')
    else:
        archivo_entrada = archivo_original.replace('inputs', 'temp').replace('.csv', '_converted_pro_FIFO.csv')
    generar_informe_fiscal(archivo_entrada, 
                           anio_fiscal=2025, 
                           informe_fiscal=archivo_original.replace('inputs', 'outputs').replace('.csv', '_Informe_Fiscal'))
