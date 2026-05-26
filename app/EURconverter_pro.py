
# EURconverter_pro.py
# -*- coding: utf-8 -*-

from anyio import Path
import pandas as pd
import requests
from datetime import datetime
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from functools import wraps
from Core import ARCHIVO_ENTRADA, format_float_output, normalizar_activo

def retry_api_call(max_retries=3, delay=30):
    """Decorador para gestionar reintentos en llamadas a la API de Kraken"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            retries = 0
            while retries < max_retries:
                result = func(self, *args, **kwargs)
                if result is not None:
                    return result
                
                retries += 1
                if retries < max_retries:
                    print(f"⏳ Reintento {retries}/{max_retries} tras error o límite. Esperando {delay}s...")
                    time.sleep(delay)
            
            print(f"❌ Fallo definitivo tras {max_retries} intentos.")
            return None
        return wrapper
    return decorator

class KrakenConverter:
    def __init__(self):
        self.base_url = "https://api.kraken.com/0/public/"
        self.session = self._setup_session()
        self.mapping_eur = self._obtener_mapeo_pares()

    def _setup_session(self):
        """Configura una sesión con reintentos automáticos para errores HTTP"""
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session

    def _obtener_mapeo_pares(self):
        """Punto 1: Almacena pair_id indexado por altname para una búsqueda precisa"""
        print("🔍 Cargando pares dinámicos desde Kraken...")
        try:
            url = f"{self.base_url}AssetPairs"
            response = self.session.get(url)
            datos = response.json()
            
            if datos.get('error'):
                raise Exception(f"Error API Kraken: {datos['error']}")
            
            pares = datos['result']
            # Mapa: Altname -> pair_id (ID interno)
            # Filtramos solo los que tienen EUR como moneda de cotización
            mapa = {}
            for par_id, detalles in pares.items():
                if detalles['quote'].endswith('EUR'):
                    # Guardamos el pair_id usando el altname como clave para la búsqueda posterior
                    mapa[detalles['altname']] = par_id
            
            return mapa
        except Exception as e:
            print(f"❌ Error crítico obteniendo pares: {e}")
            return {}

    @retry_api_call(max_retries=3, delay=30)
    def _consultar_precio_api(self, pair_id, altname, timestamp):
        """Realiza la consulta técnica a la API pública de Kraken (OHLC)"""
        try:
            url = f"{self.base_url}OHLC?pair={pair_id}&interval=1440&since={timestamp}"
            respuesta = self.session.get(url, timeout=10) # Añadido timeout por seguridad
            datos = respuesta.json()
            
            # Validación de errores de la API
            if datos.get('error'):
                error_msg = str(datos['error'])
                if "EGeneral:Too many requests" in error_msg:
                    # Retornamos None para que el decorador actúe y reintente
                    return None
                print(f"⚠️ Error en par {altname}: {error_msg}")
                return None
                
            # Extracción del precio de cierre (índice 4 del primer registro OHLC)
            ohlc_data = datos['result'].get(pair_id)
            if ohlc_data and len(ohlc_data) > 0:
                tasa = float(ohlc_data[0][4])
                return tasa if tasa > 0 else None
                
            return None
            
        except Exception as e:
            print(f"❌ Error de conexión para {altname}: {e}")
            return None


    def obtener_tasa_conversion(self, asset, fecha):
        """Lógica con fallback y búsqueda exacta por altname/pair_id"""
        # Cortocircuito EUR a EUR
        #asset_base = asset.split('.')[0].upper()

        #asset_base = normalizar_activo(asset)
        asset_base = asset

        # Traducción de MATIC a POL por la migración
        #if asset_base == 'MATIC':
        #   asset_base = 'POL'
        
        if asset_base == 'EUR': return 1.0
        # Fallback por colapso del activo LUNA (Si el activo es LUNA2, devolvemos 0.0 directamente)
        if asset_base == 'LUNA2': return 0.0

        timestamp = int(datetime.strptime(fecha, "%Y-%m-%d").timestamp())
        
        # Lista de candidatos a probar (incluye lógica de fallback para USD)
        candidatos = []
        if asset_base == 'USD':
            candidatos = ['USDTEUR']
        elif asset_base == 'BTC':
            candidatos = ['XXBTZEUR', 'XBTEUR', 'BTCEUR']
        elif asset_base == 'ETHW':
            candidatos = ['ETHEUR']
        else:
            candidatos = [f"{asset_base}EUR"]

        for altname_buscado in candidatos:
            # Buscamos el pair_id real en nuestro mapa dinámico
            pair_id = self.mapping_eur.get(altname_buscado)
            
            if pair_id:
                tasa = self._consultar_precio_api(pair_id, altname_buscado, timestamp)
                if tasa:
                    return tasa
            
        return None

def procesar_ledger(archivo_entrada, archivo_salida):
    converter = KrakenConverter()
    df = pd.read_csv(archivo_entrada)
    df['asset'] = df['asset'].apply(normalizar_activo)

    # CREACIÓN DEL ÍNDICE DE ORDEN ORIGINAL
    # Usamos el índice actual (que es el orden del archivo) como una columna fija
    df['orden_original'] = range(len(df))
    
    # Aseguramos formato datetime para preservar hora
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df = df.dropna(subset=['time'])

    df['amount_eur'] = 0.0
    df['fee_eur'] = 0.0
    df['tasa'] = 0.0
    df['EUR_conversion'] = ''
    if 'legs_subclasses' not in df.columns:
        df['legs_subclasses'] = ''

    print(f"🚀 Procesando {len(df)} filas...")

    # Agrupamos por refid para detectar la "pata" EUR en la misma operación
    grupos = df.groupby('refid', sort=False)

    for refid, grupo in grupos:
        # 1. Identificar activos únicos (excluyendo EUR)
        activos_crypto = [a for a in grupo['asset'].unique() if a != 'EUR']
        
        # 2. Determinar si es una operación multi-pata compleja
        # Si hay más de 2 activos cryptos diferentes, el valor EUR de la pata fiat 
        # no se puede asignar directamente por simple oposición.
        es_operacion_compleja = len(activos_crypto) > 2        
        
        # 3. Localizar la pata de EUR si existe
        pata_fiat = grupo[grupo['asset'] == 'EUR']
        valor_fiat_real = None
        usa_api = False
        
        if not pata_fiat.empty:
            # El valor real es el valor absoluto de lo que entró o salió en EUR
            valor_fiat_real = abs(pata_fiat['amount'].iloc[0])

        subclass_values = grupo['subclass'].fillna('').astype(str).tolist()
        subclass_values = [v for v in subclass_values if v != '']
        legs_subclasses = ' '.join(subclass_values)

        for indice in grupo.index:
            fila = df.loc[indice]
            asset = fila['asset']

            legs_subclasses_actual = fila.get('legs_subclasses')
            if pd.isna(legs_subclasses_actual) or str(legs_subclasses_actual).strip().lower() in ('', 'nan'):
                df.at[indice, 'legs_subclasses'] = legs_subclasses
            # Caso 1: La fila es el propio EUR
            if asset == 'EUR':
                df.at[indice, 'amount_eur'] = fila['amount']
                df.at[indice, 'fee_eur'] = fila['fee']
                df.at[indice, 'tasa'] = 1.0
                df.at[indice, 'EUR_conversion'] = 'Direct EUR assignment'
                continue

            # CASO 2: Operación compleja (3+ patas) -> Consultar API obligatoriamente
            if es_operacion_compleja:
                usa_api = True
                fecha_api = fila['time'].strftime('%Y-%m-%d')
                tasa_api = converter.obtener_tasa_conversion(asset, fecha_api)                
                if tasa_api is not None:
                    df.at[indice, 'tasa'] = tasa_api
                    df.at[indice, 'amount_eur'] = fila['amount'] * tasa_api
                    df.at[indice, 'fee_eur'] = fila['fee'] * tasa_api
                    df.at[indice, 'EUR_conversion'] = 'API conversion for multi-leg operation'
                    print(f"🌐 [API KRAKEN - MULTIPATA] {fila['time']} | {asset}: {tasa_api} EUR | Ref: {refid} | Type: {fila['type']}")
                else:
                    df.at[indice, 'EUR_conversion'] = 'Error: No rate available for multi-leg operation'
                    print(f"❌ [{fila['time']}] {asset}: Sin tasa disponible")

            # Caso 3: Es un activo cripto y hay sólo 2 patas (1 cripto + 1 EUR) -> Podemos usar el valor real de EUR para calcular la tasa
            elif valor_fiat_real is not None and fila['amount'] != 0:
                # --- LÓGICA DE CORTOCIRCUITO (No API) ---
                # La tasa es el resultado de dividir los EUR reales entre las unidades cripto
                tasa_real = valor_fiat_real / abs(fila['amount'])
                
                df.at[indice, 'tasa'] = tasa_real
                df.at[indice, 'amount_eur'] = fila['amount'] * tasa_real
                df.at[indice, 'fee_eur'] = fila['fee'] * tasa_real
                df.at[indice, 'EUR_conversion'] = 'Calculated from real EUR value in 2-leg operation'
                
                print(f"✅ [FIAT REAL - 2 PATAS] {fila['time']} | {asset}: Tasa calculada {tasa_real:.4f} EUR (Ref: {refid})")
            # Caso 4: Permutas o staking sin pata EUR -> Consultar API para obtener la tasa de ese día
            else:
                # --- LÓGICA DE API (Para permutas o staking) ---
                usa_api = True
                fecha_api = fila['time'].strftime('%Y-%m-%d')
                tasa_api = converter.obtener_tasa_conversion(asset, fecha_api)
                
                if tasa_api is not None:
                    df.at[indice, 'tasa'] = tasa_api
                    df.at[indice, 'amount_eur'] = fila['amount'] * tasa_api
                    df.at[indice, 'fee_eur'] = fila['fee'] * tasa_api
                    df.at[indice, 'EUR_conversion'] = 'API conversion for trade/staking'
                    print(f"🌐 [API KRAKEN - PERMUTAS/STAKING] {fila['time']} | {asset}: {tasa_api} EUR | Ref: {refid} | Type: {fila['type']}")
                else:
                    df.at[indice, 'EUR_conversion'] = 'Error: No rate available for trade/staking'
                    print(f"❌ [{fila['time']}] {asset}: Sin tasa disponible")

        # Pausa para evitar Rate Limit en las filas que sí usan API
        if usa_api:
            time.sleep(0.2)

    # C. RE-ORDENAR antes de guardar (Garantía final)
    #df = df.sort_values('time')
    
    # Al guardar, NO ordenes por tiempo, guarda según el orden_original
    df = df.sort_values('orden_original')
    df.to_csv(archivo_salida, index=False, float_format=format_float_output)
    print(f"\n✨ Proceso finalizado. Archivo guardado: {archivo_salida}")

if __name__ == "__main__":
    archivo_original = ARCHIVO_ENTRADA
    archivo_salida = ''
    if "BittyTax" in archivo_original:
        archivo_intermedio = archivo_original.replace('inputs', 'temp').replace('.csv', '_converted_from_bittytax.csv')
        archivo_salida = archivo_intermedio.replace('.csv', '_converted_pro.csv')
    else:
        archivo_intermedio = archivo_original
        archivo_salida = archivo_original.replace('inputs', 'temp').replace('.csv', '_converted_pro.csv')
    procesar_ledger(archivo_intermedio, archivo_salida)
