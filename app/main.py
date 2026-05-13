
# core.py
# -*- coding: utf-8 -*-

import os
from datetime import datetime

# Importamos los módulos (asegúrate de que los nombres de archivo coincidan)
import EURconverter_pro as converter
import FIFO_calculator as calculator
import Fiscal_Reporter_ES as reporter
import sys
import subprocess
from Core import ARCHIVO_ENTRADA, IN_COLAB

# --- INSTALACIÓN AUTOMÁTICA EN COLAB ---
if IN_COLAB:
    print("☁️ Entorno Google Colab detectado. Instalando dependencias...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xlsxwriter", "pandas", "requests"])

from pathlib import Path

def orchestrator(archivo_entrada=ARCHIVO_ENTRADA, anio_a_reportar=None):
    # --- CONFIGURACIÓN DE RUTAS ---
    archivo_original = Path(archivo_entrada)
    #archivo_convertido = archivo_entrada.replace('inputs', 'temp').replace('.csv', '_converted_pro.csv')
    #archivo_fifo = archivo_entrada.replace('inputs', 'temp').replace('.csv', '_FIFO.csv')
    #informe_fiscal = archivo_entrada.replace('inputs', 'outputs').replace('.csv', '_Informe_Fiscal')

    archivo_convertido = str(archivo_original.parents[1] / "temp" / f"{archivo_original.stem}_converted_pro.csv")
    archivo_fifo = str(archivo_original.parents[1] / "temp" / f"{archivo_original.stem}_FIFO.csv")
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

    try:
        # --- PASO 1: CONVERSIÓN (SALTAR SI YA EXISTE) ---
        print("\n--- PASO 1: Conversión de Precios y Normalización ---")
        
        if os.path.exists(archivo_convertido):
            print(f"⏩ El archivo '{archivo_convertido}' ya existe. Saltando conversión para ahorrar tiempo.")
        else:
            if not os.path.exists(archivo_original):
                print(f"❌ Error crítico: No se encuentra el origen '{archivo_original}'.")
                return
            
            print(f"⏳ Procesando conversión (esto puede tardar por las llamadas a API)...")
            converter.procesar_ledger(archivo_original, archivo_convertido)
            print(f"✅ Conversión finalizada y guardada en '{archivo_convertido}'.")
        
        # --- PASO 2: CÁLCULO FIFO ---
        # Este paso suele ser rápido, pero si quieres saltarlo también, 
        # podrías aplicar la misma lógica de os.path.exists(archivo_fifo)
        print("\n--- PASO 2: Cálculo de Ganancias FIFO ---")
        calculator.calcular_fifo(archivo_convertido, archivo_fifo)
        
        # --- PASO 3: INFORME FISCAL ---
        print(f"\n--- PASO 3: Generación de Informe Fiscal {anio_a_reportar} ---")
        # El reporter necesita el CSV del FIFO y el archivo .pkl generado en el Paso 2
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