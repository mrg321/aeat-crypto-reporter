
# FIFO_calculator.py
# -*- coding: utf-8 -*-

import pandas as pd
import pickle

from collections import deque

# Configuración de precisión
from Core import PRECISION_CRIPTOS, TOLERANCIA_DUST, ARCHIVO_ENTRADA

def normalizar_activo(asset):
    if pd.isna(asset): return asset
    sufijos = ['.S', '.M', '.P', '.2']
    for sufijo in sufijos:
        if asset.endswith(sufijo):
            return asset.replace(sufijo, '')
    return asset

def obtener_balance_total_colas(colas):
    """
    Calcula el balance actual de todos los activos basándose 
    exclusivamente en los lotes pendientes en las colas FIFO.
    
    Args:
        colas (dict): El diccionario que contiene todas las colas { 'BTC': deque([...]), 'ETH': ... }
        
    Returns:
        dict: Un diccionario con { 'ASSET': balance_total }
    """
    balances = {}
    
    for asset, cola in colas.items():
        # Sumamos las cantidades de cada lote en la deque de este activo
        balance_activo = sum(lote['cantidad'] for lote in cola)
        
        # Solo lo incluimos si el balance es significativo (evitar residuos de redondeo)
        if balance_activo > TOLERANCIA_DUST:
            balances[asset] = round(balance_activo, PRECISION_CRIPTOS)
            
    return balances

def obtener_balance_cola(colas, asset):
    return sum(lote['cantidad'] for lote in colas.get(asset, []))

def debug_fiat_balance(colas, divisa='USD'):
    saldo = sum(lote['cantidad'] for lote in colas.get(divisa, []))
    return round(saldo, 2)

def realizar_validacion_final(colas, balances_referencia_kraken):
    print("\n" + "="*50)
    print("RECONCILIACIÓN FINAL DE BALANCES (Normalizados)")
    print("="*50)
    
    # Obtenemos todos los activos únicos normalizados que hay en las colas
    activos_en_cola = set(colas.keys())
    
    # Obtenemos todos los activos normalizados que hay en los balances de Kraken
    activos_en_referencia = set(normalizar_activo(a) for a in balances_referencia_kraken.keys())
    
    todos_los_activos = activos_en_cola.union(activos_en_referencia)
    errores_encontrados = 0

    for asset_norm in sorted(todos_los_activos):
        # 1. Sumar lo que hay en nuestra cola FIFO (ya está normalizado)
        saldo_fifo = sum(lote['cantidad'] for lote in colas.get(asset_norm, []))
        
        # 2. Sumar todos los balances de Kraken que coincidan con este activo normalizado
        # Ejemplo: suma el balance de 'ETH' + balance de 'ETH.S'
        saldo_kraken_total = sum(
            bal for etiqueta, bal in balances_referencia_kraken.items() 
            if normalizar_activo(etiqueta) == asset_norm
        )
        
        discrepancia = abs(saldo_fifo - saldo_kraken_total)
        
        status = "✅ OK"
        if discrepancia > 1e-7: # Tolerancia para errores de redondeo
            status = "❌ ERROR"
            errores_encontrados += 1
        
        print(f"{asset_norm:<10} | FIFO: {saldo_fifo:>12.8f} | Kraken: {saldo_kraken_total:>12.8f} | Dif: {discrepancia:>12.8f} | {status}")

    print("="*50)
    if errores_encontrados == 0:
        print("🎉 Validación exitosa: Todos los balances coinciden.")
    else:
        print(f"⚠️ Alerta: Se han encontrado {errores_encontrados} discrepancias.")
    print("="*50 + "\n")

def calcular_fifo(archivo_entrada, archivo_salida):
    # 1. Carga de datos
    df = pd.read_csv(archivo_entrada)
    df['time'] = pd.to_datetime(df['time'])
    # Orden cronológico estricto
    #df = df.sort_values(['time', 'refid']).reset_index(drop=True)
    
    # FORZAR EL ORDEN ORIGINAL DEL ARCHIVO DE KRAKEN
    # Esto garantiza que si Kraken puso un 'spend' antes que un 'receive', 
    # se procese exactamente en ese orden.
    df = df.sort_values('orden_original').reset_index(drop=True)    
    
    # Estructuras de datos
    colas = {}

    # Este diccionario guardará: {'Asset_Tag': Ultimo_Balance_Visto}
    balances_referencia_kraken = {}

    # Este diccionario guardará los inventarios anuales para cada activo, por si queremos hacer análisis posteriores
    inventarios_anuales = {} # {año: {asset: [lista_de_lotes]}}

    # Inicializamos la columna explícitamente como float
    df['ganancia_fifo'] = 0.0
    df['FIFO_calculation'] = ''
    df['Valor de transmision'] = 0.0
    df['Valor de adquisicion'] = 0.0
    
    # 2. Agrupamos para identificar patas FIAT (ventas directas a EUR)
    grupos = df.groupby('refid', sort=False)

    print(f"🧮 Iniciando cálculo FIFO sobre {len(df)} registros...")

    # 1. Lista de tipos que SÍ generan ganancia o coste
    tipos_reales = ['trade', 'spend', 'receive', 'staking', 'earn', 'dividend', 'withdrawal', 'deposit', 'transfer']

    # 2. Lista de subtipos que son solo MOVIMIENTOS (Añadimos allocation)
    subtipos_neutros = ['transfer', 'allocation', 'deallocation', 'autoallocation', 'settled', 'migration']

    saldo_eur_tracker = 0.0  # Variable para el seguimiento de caja

    for refid, grupo in grupos:
        # Tipos que consideramos operaciones de movimiento de valor
        #tipos_validos = ['trade', 'spend', 'receive', 'staking', 'earn', 'dividend', 'transfer']
        operaciones = grupo[grupo['type'].isin(tipos_reales)]
        
        if operaciones.empty:
            continue

        # BUSQUEDA DE PATA EUR (Para valorar la operación con precisión)
        #pata_fiat = operaciones[operaciones['asset'] == 'EUR']
        #valor_fiat_real = None
        #if not pata_fiat.empty:
        #    valor_fiat_real = abs(pata_fiat['amount'].iloc[0])

        for idx in operaciones.index:
            fila = df.loc[idx]
            anio_actual = fila['time'].year
            if 'anio_previo' in locals() and anio_actual != anio_previo:
                # Guardamos el estado de las colas al cierre del año anterior
                inventarios_anuales[anio_previo] = {a: list(c) for a, c in colas.items()}
            anio_previo = anio_actual

            asset_original = fila['asset']  # Ej: 'ETH.S' o 'BTC'
            balance_actual = fila['balance']
        
            # --- ACTUALIZACIÓN AQUÍ ---
            # Sobreescribimos siempre: el último valor es el que cuenta como saldo final
            balances_referencia_kraken[asset_original] = balance_actual

            tipo = fila['type']
            if tipo == 'spend':
                print(f"🔻 [{fila['time']}] SPEND DETECTADO | {fila['asset']} | Ref: {refid}")

            subtipo = fila['subtype']
            asset = normalizar_activo(fila['asset'])
            amount = fila['amount']
            fee_eur = abs(fila['fee_eur'])

            # --- SEGUIMIENTO DE SALDO EUR ---
            # Sumamos el importe en EUR (incluyendo fees si quieres el saldo neto de caja)
            importe_operacion_eur = fila['amount_eur']
            #comision_eur = abs(fila['fee_eur'])
            
            # El saldo de caja baja con las comisiones y cambia según el amount_eur
            saldo_eur_tracker += (importe_operacion_eur - fee_eur)
            
            if amount == 0:
                df.at[idx, 'FIFO_calculation'] = 'Zero amount: no operation performed'
                continue
            
            if asset == 'EUR':
                # Aquí no hay lógica FIFO, pero sí actualización de saldo de caja
                # El trace de arriba ya lo captura, así que solo pasamos
                #df.at[idx, 'FIFO_calculation'] = 'Fiat currency: no FIFO calculation performed'
                pass
            elif asset == 'USD':
                #print(f"💵 [{fila['time']}] USD DETECTADO | Ref: {refid} | Tipo: {tipo} | Subtipo: {subtipo} | Cantidad: {amount}")
                #print(f"DEBUG | Saldo acumulado de USD: {debug_fiat_balance(colas)} $")
                pass
            elif asset == 'BTC':
                #print(f"₿ [{fila['time']}] BTC DETECTADO | Ref: {refid} | Tipo: {tipo} | Subtipo: {subtipo} | Cantidad: {amount}")
                #print(f"DEBUG | Saldo acumulado de BTC: {obtener_balance_cola(colas, 'BTC')} BTC | Ref: {refid}")
                pass

            if asset not in colas:
                colas[asset] = deque()

            # --- VALIDACIÓN PREVIA ---
            # Kraken normaliza el balance incluyendo el fee de la fila actual
            balance_esperado = fila['balance'] 

            # ---------- DETECCIÓN DE MOVIMIENTOS CIRCULARES -------------
            # Sumamos el balance neto del activo normalizado en este RefID
            balance_neto_refid = operaciones[operaciones['asset'].apply(normalizar_activo) == asset]['amount'].sum()
            
            if abs(balance_neto_refid) < TOLERANCIA_DUST and subtipo in subtipos_neutros:
                # Si el neto es 0 y es un movimiento (ej. ETH -> ETH.S), no hacemos NADA.
                # De esta forma el lote original en la cola no se toca.
                df.at[idx, 'ganancia_fifo'] = 0.0
                df.at[idx, 'FIFO_calculation'] = 'Neutral movement: no FIFO calculation performed, gain set to 0'
                if amount < 0:
                    print(f"🔄 [{fila['time']}] BYPASS (Interno) | {asset} | Conservando coste original | Ref: {refid}")
                continue

            # --- LÓGICA A: ENTRADAS (Compras, Recompensas, Recepciones) ---
            if amount > 0:
                saldo_anterior_cola = obtener_balance_cola(colas, asset)
                # Si hay EUR en el refid, ese es el coste. Si no, lo que diga la API.
                #base_coste = valor_fiat_real if valor_fiat_real is not None else abs(fila['amount_eur'])
                base_coste = abs(fila['amount_eur'])
                fee_en_este_asset = abs(fila['fee']) if fila['asset'] == asset else 0
                cantidad_neta_entrada = amount - fee_en_este_asset
                coste_total = base_coste + fee_eur
                coste_unitario = coste_total / amount
                
                colas[asset].append({
                    'cantidad': cantidad_neta_entrada,
                    'coste_unitario': coste_unitario,
                    'fecha': fila['time']
                })
                #print(f"📥 [{fila['time']}] +{amount:.6f} {asset} | Coste: {coste_total:.2f}€ | Ref: {refid}")

                df.at[idx, 'FIFO_calculation'] = f'Entry: added {cantidad_neta_entrada:.6f} {asset} to FIFO queue with unit cost {coste_unitario:.4f} EUR, no gain calculated'

                if tipo in ['staking', 'earn', 'dividend']:
                    print(f"📥 [{fila['time']}] RECOMPENSA | {asset} | +{amount:.6f} | Ref: {refid}")
                else:
                    print(f"📥 [{fila['time']}] ENTRADA    | {asset} | +{amount:.6f} | Ref: {refid} | Saldo anterior en colas: {saldo_anterior_cola}")

            # --- LÓGICA B: SALIDAS (Ventas, Permutas, Retiros) ---
            elif amount < 0:
                #cantidad_total_a_salir = round(abs(amount), PRECISION_CRIPTOS)
                fee_en_este_asset = abs(fila['fee']) if fila['asset'] == asset else 0
                cantidad_total_a_salir = round(abs(amount), PRECISION_CRIPTOS) + fee_en_este_asset
                # CASO B.1: MOVIMIENTOS NEUTROS (Allocation, Transfer)
                # Solo ajustamos inventario, ganancia siempre 0.
                if subtipo in subtipos_neutros:
                    # Ajuste de inventario sin ganancia
                    cantidad_a_procesar = cantidad_total_a_salir
                    while cantidad_a_procesar > TOLERANCIA_DUST and colas[asset]:
                        lote = colas[asset][0]
                        cant_lote = round(lote['cantidad'], PRECISION_CRIPTOS)
                        if cant_lote <= cantidad_a_procesar:
                            cantidad_a_procesar = round(cantidad_a_procesar - cant_lote, PRECISION_CRIPTOS)
                            colas[asset].popleft()
                        else:
                            lote['cantidad'] = round(lote['cantidad'] - cantidad_a_procesar, PRECISION_CRIPTOS)
                            cantidad_a_procesar = 0
                    df.at[idx, 'ganancia_fifo'] = 0.0
                    df.at[idx, 'FIFO_calculation'] = f'Neutral movement: adjusted inventory by removing {cantidad_total_a_salir:.6f} {asset} from FIFO queue, gain set to 0'
                    print(f"🔄 [{fila['time']}] MOVIMIENTO | {asset} | -{abs(amount):.6f} | Ganancia: 0.00€ | Ref: {refid}")


                # CASO B.2: VENTAS O PERMUTAS REALES
                # Aquí sí calculamos beneficio contra la cola FIFO
                else:
                    # Venta o Permuta con cálculo de ganancia
                    #base_transmision = valor_fiat_real if valor_fiat_real is not None else abs(fila['amount_eur'])
                    base_transmision = abs(fila['amount_eur'])
                    
                    # La ganancia se calcula sobre el neto recibido (EUR - fee_eur)
                    #valor_transmision_neto = base_transmision - fee_eur
                    valor_transmision_neto = base_transmision
                    cantidad_a_procesar = cantidad_total_a_salir
                    precio_venta_unitario = valor_transmision_neto / cantidad_a_procesar
                    
                    ganancia_total_fila = 0.0
                    lotes_consumidos = []
                    
                    while cantidad_a_procesar > TOLERANCIA_DUST:
                        if not colas[asset]:
                            if cantidad_a_procesar > 1e-5: # Ignorar si es una cantidad minúscula
                                df.at[idx, 'FIFO_calculation'] = f'Error: Insufficient balance in FIFO queue for {asset}, cannot process sale of {cantidad_a_procesar:.8f}'
                                print(f"❌ ERROR: Sin saldo de {asset} para vender {cantidad_a_procesar:.8f} (Ref: {refid})")
                            break
                        
                        lote = colas[asset][0]
                        cant_lote = round(lote['cantidad'], PRECISION_CRIPTOS)
                        coste_unitario_lote = lote['coste_unitario']

                        if cant_lote <= cantidad_a_procesar:
                            # Consumimos lote completo
                            ganancia_total_fila += cant_lote * (precio_venta_unitario - coste_unitario_lote)
                            lotes_consumidos.append({
                                'cantidad': cant_lote,
                                'coste_unitario': coste_unitario_lote,
                                'valor_original': round(cant_lote * coste_unitario_lote, 4)
                            })
                            cantidad_a_procesar = round(cantidad_a_procesar - cant_lote, PRECISION_CRIPTOS)
                            colas[asset].popleft()
                        else:
                            # Consumimos parte del lote
                            ganancia_total_fila += cantidad_a_procesar * (precio_venta_unitario - coste_unitario_lote)
                            lotes_consumidos.append({
                                'cantidad': cantidad_a_procesar,
                                'coste_unitario': coste_unitario_lote,
                                'valor_original': round(cantidad_a_procesar * coste_unitario_lote, 4)
                            })
                            lote['cantidad'] = round(lote['cantidad'] - cantidad_a_procesar, PRECISION_CRIPTOS)
                            cantidad_a_procesar = 0
                
                # ASIGNACIÓN CRÍTICA: Guardamos el resultado en el DataFrame original
                df.at[idx, 'ganancia_fifo'] = round(ganancia_total_fila, 4)
                
                if not df.at[idx, 'FIFO_calculation']:  # If no error was set
                    detalle_lotes = ', '.join(
                        f"{l['cantidad']:.6f}@{l['coste_unitario']:.4f}EUR (valor original {l['valor_original']:.4f}EUR)"
                        for l in lotes_consumidos
                    )
                    df.at[idx, 'FIFO_calculation'] = (
                        f'FIFO sale: sold {cantidad_total_a_salir:.6f} {asset} at unit price {precio_venta_unitario:.4f} EUR; '
                        f'gain=sum((sale_price-cost_price)*qty); consumed lots: {detalle_lotes}'
                    )
                    df.at[idx, 'Valor de transmision'] = round(valor_transmision_neto, 4)
                    df.at[idx, 'Valor de adquisicion'] = round(sum(l['valor_original'] for l in lotes_consumidos), 4)
                
                if abs(ganancia_total_fila) > 0:
                    print(f"📤 [{fila['time']}] VENTA {asset} | Ganancia: {ganancia_total_fila:+.2f}€ | Ref: {refid}")

            # --- VALIDACIÓN POST-OPERACIÓN ---
            # Comparamos lo que hay en nuestra cola contra la columna 'balance' de Kraken
            # Nota: Solo validamos si el asset no está normalizado (Kraken separa balance de ETH y ETH.S)
            saldo_cola = obtener_balance_cola(colas, asset)
            discrepancia = abs(saldo_cola - fila['balance'])
            
            if discrepancia > TOLERANCIA_DUST and fila['asset'] == asset:
                print(f"⚠️ DISCREPANCIA BALANCE | Asset: {asset} | Cola: {saldo_cola:.8f} | Ledger: {fila['balance']:.8f} | Diff: {discrepancia:.8f} | Ref: {refid}")
                if asset == 'BTC':
                    #print(f"DEBUG | Colas BTC: {[round(l['cantidad'], 8) for l in colas['BTC']]} | Ref: {refid}")
                    pass

    # Al final de calcular_fifo(...)
    resumen_inventario = obtener_balance_total_colas(colas)

    print("\n" + "="*40)
    print("ESTADO DEL INVENTARIO FIFO (Saldos restantes)")
    print("="*40)
    if not resumen_inventario:
        print("No quedan activos en el inventario.")
    else:
        for asset, saldo in resumen_inventario.items():
            print(f"🔹 {asset:10}: {saldo:>15.10f}")
    print("="*40)

    asset_eur = "SALDO EUR"
    print(f"🔹 {asset_eur:10}: {saldo_eur_tracker:>15.10f}")
    print("="*40)

    # Validación final: Reconciliar los balances que nos quedan en las colas contra el balance final que reporta Kraken
    realizar_validacion_final(colas, balances_referencia_kraken)

    # Guardar el último año procesado
    inventarios_anuales[anio_actual] = {a: list(c) for a, c in colas.items()}

    # --- EXPORTACIÓN DEL FICHERO PKL ---
    #path_pkl = os.path.join(os.path.dirname(archivo_salida), 'inventarios_fifo.pkl')
    path_pkl = ARCHIVO_ENTRADA.replace('inputs', 'temp').replace('.csv', '_inventarios_fifo.pkl')
    with open(path_pkl, 'wb') as f:
        pickle.dump(inventarios_anuales, f)
    
    print(f"📦 Inventarios anuales guardados en: {path_pkl}")

    # Guardado
    df.to_csv(archivo_salida, index=False)
    print(f"\n✅ FIFO completado con éxito. Archivo: {archivo_salida}")

if __name__ == "__main__":
    calcular_fifo(ARCHIVO_ENTRADA.replace('inputs', 'temp').replace('.csv', '_converted_pro.csv'), ARCHIVO_ENTRADA.replace('inputs', 'temp').replace('.csv', '_FIFO.csv'))