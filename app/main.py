
# core.py
# -*- coding: utf-8 -*-

import os
from datetime import datetime

# Importamos los módulos (asegúrate de que los nombres de archivo coincidan)
import EURconverter_pro as converter
import bittytax2kraken as bittytax_converter
import FIFO_calculator as calculator
import Fiscal_Reporter_ES as reporter
import sys
import subprocess  # nosec B404
import pandas as pd
from Core import ARCHIVO_ENTRADA, IN_COLAB, recognize_csv_format

# --- INSTALACIÓN AUTOMÁTICA EN COLAB ---
if IN_COLAB:
    print("☁️ Entorno Google Colab detectado. Instalando dependencias...")
    # Usamos nosec B603 porque el input está controlado y no hay shell injection posible
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "xlsxwriter", "pandas", "requests"],
        shell=False
    )  # nosec B603

from pathlib import Path


def detect_input_format(archivo_entrada):
    if not os.path.exists(archivo_entrada):
        raise FileNotFoundError(f"No se encuentra el origen '{archivo_entrada}'.")

    columns = pd.read_csv(archivo_entrada, nrows=0).columns
    csv_format = recognize_csv_format(columns)
    if csv_format == "unknown":
        raise ValueError(
            f"Formato CSV no reconocido para '{archivo_entrada}'. "
            "Se esperaba formato Kraken o BittyTax."
        )
    return csv_format


def orchestrator(archivo_entrada=ARCHIVO_ENTRADA, anio_a_reportar=None):
    # --- CONFIGURACIÓN DE RUTAS ---
    archivo_original = Path(archivo_entrada)
    archivo_convertido_1paso = str(archivo_original.parents[1] / "temp" / f"{archivo_original.stem}_converted_pro.csv")
    archivo_convertido_2pasos_paso1 = str(archivo_original.parents[1] / "temp" / f"{archivo_original.stem}_converted_from_bittytax.csv")
    archivo_convertido_2pasos_paso2 = str(archivo_original.parents[1] / "temp" / f"{archivo_original.stem}_converted_from_bittytax_converted_pro.csv")
    informe_fiscal = str(archivo_original.parents[1] / "outputs" / f"{archivo_original.stem}_Informe_Fiscal")

    # Definir año fiscal (por defecto el año pasado)
    anio_actual = datetime.now().year
    if anio_a_reportar is None:
        anio_a_reportar = anio_actual - 1
    else:
        try:
            anio_a_reportar = int(anio_a_reportar)
        except (TypeError, ValueError):
            print(f"⚠️ Año informado inválido ('{anio_a_reportar}'). Usando el año fiscal anterior {anio_actual - 1}.")
            anio_a_reportar = anio_actual - 1

    print("🚀 Iniciando Pipeline Contable de Criptoactivos...")

    formato_entrada = detect_input_format(archivo_original)
    print(f"Formato detectado: {formato_entrada}")

    try:
        # --- PASO 1: CONVERSIÓN (SALTAR SI YA EXISTE) ---
        print("\n--- PASO 1: Conversión de Precios y Normalización ---")
        sabor = None
        
        if os.path.exists(archivo_convertido_1paso):
            print(f"⏩ El archivo '{archivo_convertido_1paso}' ya existe. Saltando conversión para ahorrar tiempo.")
        elif os.path.exists(archivo_convertido_2pasos_paso2):
            print(f"⏩ El archivo '{archivo_convertido_2pasos_paso2}' ya existe. Saltando primera parte de conversión BittyTax.")
            archivo_convertido_1paso = archivo_convertido_2pasos_paso2  # Para que el siguiente paso use el resultado correcto
        elif formato_entrada == "kraken":
            if not os.path.exists(archivo_original):
                print(f"❌ Error crítico: No se encuentra el origen '{archivo_original}'.")
                return
            
            print(f"⏳ Procesando conversión (esto puede tardar por las llamadas a API)...")
            converter.procesar_ledger(archivo_original, archivo_convertido_1paso)
            print(f"Conversion Kraken finalizada y guardada en '{archivo_convertido_1paso}'.")
            sabor = 'kraken'
        elif formato_entrada == "bittytax":
            print("Convirtiendo BittyTax a formato Kraken...")
            bittytax_converter.convertir_bittytax_a_kraken(archivo_original, archivo_convertido_2pasos_paso1)
            print(f"✅ Conversión finalizada y guardada en '{archivo_convertido_2pasos_paso2}'.")
            print(f"⏳ Procesando conversión (esto puede tardar por las llamadas a API)...")
            converter.procesar_ledger(archivo_convertido_2pasos_paso1, archivo_convertido_2pasos_paso2)
            print(f"✅ Conversión finalizada y guardada en '{archivo_convertido_2pasos_paso2}'.")
            archivo_convertido_1paso = archivo_convertido_2pasos_paso2  # Para que el siguiente paso use el resultado correcto
            sabor = 'bittytax'
        archivo_fifo = archivo_convertido_1paso.replace('.csv', '_FIFO.csv')

        # --- PASO 2: CÁLCULO FIFO ---
        # Este paso suele ser rápido, pero si quieres saltarlo también, 
        # podrías aplicar la misma lógica de os.path.exists(archivo_fifo)
        print("\n--- PASO 2: Cálculo de Ganancias FIFO ---")
        calculator.calcular_fifo(archivo_convertido_1paso, archivo_fifo, sabor)
        
        # --- PASO 3: INFORME FISCAL ---
        print(f"\n--- PASO 3: Generación de Informe Fiscal {anio_a_reportar} ---")
        # El reporter necesita el CSV del FIFO y el archivo .json generado en el Paso 2
        reporter.generar_informe_fiscal(archivo_fifo, anio_fiscal=anio_a_reportar, informe_fiscal=informe_fiscal)

        print("\n" + "="*40)
        print("✅ PROCESO FINALIZADO CON ÉXITO")
        print(f"📊 Informe listo: {informe_fiscal}_{anio_a_reportar}.xlsx")
        print("="*40)

    except Exception as e:
        print(f"\n❌ SE HA PRODUCIDO UN ERROR CRÍTICO:")
        print(f"Tipo: {type(e).__name__}")
        print(f"Detalle: {str(e)}")
        # Opcional: print de la línea exacta del error
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    input_dir = Path('data/inputs')
    csv_files = sorted(input_dir.glob('*.csv'))

    for file_path in csv_files:
        print(f"Processing inputfile: {file_path}")
        orchestrator(archivo_entrada=str(file_path))
