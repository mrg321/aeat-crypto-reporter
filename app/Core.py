
# Core.py
# -*- coding: utf-8 -*-

ARCHIVO_ENTRADA = 'data/inputs/MRGLedgers_2021-2026.csv'
PRECISION_CRIPTOS = 10
TOLERANCIA_DUST = 1e-7 # Kraken a veces tiene pequeñas discrepancias

import os

# Detectar si estamos en Google Colab
try:
    import google.colab
    IN_COLAB = True
except:
    IN_COLAB = False

ARCHIVO_ENTRADA = 'data/inputs/MRGLedgers_2021-2026.csv'
PRECISION_CRIPTOS = 10
TOLERANCIA_DUST = 1e-7

# Función de utilidad para asegurar carpetas
def asegurar_directorios():
    for folder in ['data/inputs', 'data/temp', 'data/outputs']:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"📁 Carpeta creada: {folder}")

# Llamada automática al importar Core
asegurar_directorios()