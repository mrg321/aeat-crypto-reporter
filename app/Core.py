
# core.py
# -*- coding: utf-8 -*-

ARCHIVO_ORIGINAL = 'data/inputs/MRGLedgers_2021-2026.csv'
ARCHIVO_CONVERTIDO = 'data/temp/MRGLedgers_2021-2026_converted_pro.csv'
ARCHIVO_FIFO = 'data/temp/MRGLedgers_2021-2026_FIFO.csv'
INVENTARIOS_FIFO = 'data/temp/inventarios_fifo.pkl'
INFORME_FISCAL = 'data/outputs/Informe_Fiscal'
PRECISION_CRIPTOS = 10
TOLERANCIA_DUST = 1e-7 # Kraken a veces tiene pequeñas discrepancias