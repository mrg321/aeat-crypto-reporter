import os
import pandas as pd
from Core import ARCHIVO_ENTRADA, format_float_output, normalize_number, read_csv_normalized, TIPOS_ENTRADA_BITTYTAX as TIPOS_ENTRADA
from Core import TIPOS_SALIDA_BITTYTAX as TIPOS_SALIDA


def determinar_wallet(asset):
    """Determina si el activo es Fiat o Crypto."""
    if pd.isna(asset) or str(asset).strip() == "":
        return ""
    fiats = {"EUR", "USD", "GBP", "JPY", "CAD", "AUD", "CHF"}
    return "fiat" if str(asset).upper() in fiats else "crypto"


def calcular_tasa(amount_eur, amount):
    """Calcula la tasa evitando la división por cero o nulos."""
    try:
        amount_eur = normalizar_numero(amount_eur)
        amount = normalizar_numero(amount)
        if amount == 0:
            return 0.0
        return abs(amount_eur / amount)
    except (ValueError, TypeError):
        return 0.0


def normalizar_numero(valor):
    """Convierte valores nulos o no numericos a 0.0."""
    try:
        valor_numerico = pd.to_numeric(valor, errors="coerce")
        if pd.isna(valor_numerico):
            return 0.0
        return normalize_number(valor_numerico)
    except (ValueError, TypeError):
        return 0.0


def normalizar_timestamp_bittytax(timestamp):
    """Convierte timestamps BittyTax con zona horaria al formato Kraken."""
    if pd.isna(timestamp) or str(timestamp).strip() == "":
        return ""

    fecha = pd.to_datetime(timestamp, utc=True, errors="coerce")
    if pd.isna(fecha):
        return str(timestamp).strip()

    return fecha.strftime("%Y-%m-%d %H:%M:%S")


def convertir_bittytax_a_kraken(archivo_entrada, archivo_salida):
    """Convierte un CSV exportado de BittyTax al formato de Kraken."""
    df_in = read_csv_normalized(archivo_entrada)

    filas_salida = []

    txid_counter = 1
    refid_counter = 1

    for _, row in df_in.iterrows():
        b_type = str(row.get("Type", "")).strip()
        timestamp = normalizar_timestamp_bittytax(row.get("Timestamp", ""))

        # --- REGLA 3.1.1: TRADE (Doble Pata) ---
        if b_type == "Trade":
            wallet_buy = determinar_wallet(row.get("Buy Asset", ""))
            wallet_sell = determinar_wallet(row.get("Sell Asset", ""))

            # Pata 1: COMPRA
            buy_asset = row.get("Buy Asset", "")
            if pd.notna(buy_asset) and str(buy_asset).strip() != "":
                buy_amt = row.get("Buy Quantity", 0)
                buy_val_eur = row.get("Buy Value", 0)

                pata_compra = {
                    "txid": f"TX{txid_counter:06d}",
                    "refid": f"REF{refid_counter:06d}",
                    "time": timestamp,
                    "type": b_type,
                    "subtype": "",
                    "aclass": "",
                    "subclass": "",
                    "asset": buy_asset,
                    "wallet": wallet_buy,
                    "amount": abs(normalizar_numero(buy_amt)) if buy_amt else 0,
                    "fee": normalizar_numero(row.get("Fee Quantity", 0))
                    if row.get("Fee Asset") == buy_asset
                    else 0,
                    "balance": 0,
                    "orden_original": "",
                    "amount_eur": abs(normalizar_numero(buy_val_eur)) if buy_val_eur else 0,
                    "fee_eur": normalizar_numero(row.get("Fee Value", 0))
                    if row.get("Fee Asset") == buy_asset
                    else 0,
                    "tasa": calcular_tasa(buy_val_eur, buy_amt),
                    "EUR_conversion": "Imported from bittytax export",
                    "legs_subclasses": f"{wallet_buy} {wallet_sell}".strip(),
                }
                filas_salida.append(pata_compra)
                txid_counter += 1

            # Pata 2: VENTA
            sell_asset = row.get("Sell Asset", "")
            if pd.notna(sell_asset) and str(sell_asset).strip() != "":
                sell_amt = row.get("Sell Quantity", 0)
                sell_val_eur = row.get("Sell Value", 0)

                pata_venta = {
                    "txid": f"TX{txid_counter:06d}",
                    "refid": f"REF{refid_counter:06d}",
                    "time": timestamp,
                    "type": b_type,
                    "subtype": "",
                    "aclass": "",
                    "subclass": "",
                    "asset": sell_asset,
                    "wallet": wallet_sell,
                    "amount": -abs(normalizar_numero(sell_amt)) if sell_amt else 0,
                    "fee": normalizar_numero(row.get("Fee Quantity", 0))
                    if row.get("Fee Asset") == sell_asset
                    else 0,
                    "balance": 0,
                    "orden_original": "",
                    "amount_eur": -abs(normalizar_numero(sell_val_eur))
                    if sell_val_eur
                    else 0,
                    "fee_eur": normalizar_numero(row.get("Fee Value", 0))
                    if row.get("Fee Asset") == sell_asset
                    else 0,
                    "tasa": calcular_tasa(sell_val_eur, sell_amt),
                    "EUR_conversion": "Imported from bittytax export",
                    "legs_subclasses": f"{wallet_sell} {wallet_buy}".strip(),
                }
                filas_salida.append(pata_venta)
                txid_counter += 1

            refid_counter += 1

        # --- REGLA 3.1.2: ENTRADAS DE ACTIVOS (1 Pata Positiva - Columnas Buy) ---
        elif b_type in TIPOS_ENTRADA:
            buy_asset = row.get("Buy Asset", "")
            if pd.notna(buy_asset) and str(buy_asset).strip() != "":
                buy_amt = row.get("Buy Quantity", 0)
                buy_val_eur = row.get("Buy Value", 0)
                w_type = determinar_wallet(buy_asset)
                amount = abs(normalizar_numero(buy_amt)) if buy_amt else 0
                amount_eur = abs(normalizar_numero(buy_val_eur)) if buy_val_eur else 0
                tasa = calcular_tasa(buy_val_eur, buy_amt)

                if b_type == "Deposit" and str(buy_asset).strip().upper() == "EUR":
                    amount_eur = amount
                    tasa = 1.0

                pata_entrada = {
                    "txid": f"TX{txid_counter:06d}",
                    "refid": f"REF{refid_counter:06d}",
                    "time": timestamp,
                    "type": b_type,
                    "subtype": "",
                    "aclass": "",
                    "subclass": "",
                    "asset": buy_asset,
                    "wallet": w_type,
                    "amount": amount,
                    "fee": normalizar_numero(row.get("Fee Quantity", 0)),
                    "balance": 0,
                    "orden_original": "",
                    "amount_eur": amount_eur,
                    "fee_eur": normalizar_numero(row.get("Fee Value", 0)),
                    "tasa": tasa,
                    "EUR_conversion": "Imported from bittytax export",
                    "legs_subclasses": w_type,
                }
                filas_salida.append(pata_entrada)
                txid_counter += 1
                refid_counter += 1

        # --- REGLA 3.1.3: SALIDAS DE ACTIVOS (1 Pata Negativa - Columnas Sell) ---
        elif b_type in TIPOS_SALIDA:
            sell_asset = row.get("Sell Asset", "")
            if pd.notna(sell_asset) and str(sell_asset).strip() != "":
                sell_amt = row.get("Sell Quantity", 0)
                sell_val_eur = row.get("Sell Value", 0)
                w_type = determinar_wallet(sell_asset)

                pata_salida = {
                    "txid": f"TX{txid_counter:06d}",
                    "refid": f"REF{refid_counter:06d}",
                    "time": timestamp,
                    "type": b_type,
                    "subtype": "",
                    "aclass": "",
                    "subclass": "",
                    "asset": sell_asset,
                    "wallet": w_type,
                    "amount": -abs(normalizar_numero(sell_amt)) if sell_amt else 0,
                    "fee": normalizar_numero(row.get("Fee Quantity", 0)),
                    "balance": 0,
                    "orden_original": "",
                    "amount_eur": -abs(normalizar_numero(sell_val_eur))
                    if sell_val_eur
                    else 0,
                    "fee_eur": normalizar_numero(row.get("Fee Value", 0)),
                    "tasa": calcular_tasa(sell_val_eur, sell_amt),
                    "EUR_conversion": "Imported from bittytax export",
                    "legs_subclasses": w_type,
                }
                filas_salida.append(pata_salida)
                txid_counter += 1
                refid_counter += 1

    # 3. Generar DataFrame final ordenado por columnas
    columnas_salida = [
        "txid",
        "refid",
        "time",
        "type",
        "subtype",
        "aclass",
        "subclass",
        "asset",
        "wallet",
        "amount",
        "fee",
        "balance",
        "orden_original",
        "amount_eur",
        "fee_eur",
        "tasa",
        "EUR_conversion",
        "legs_subclasses",
    ]

    df_out = pd.DataFrame(filas_salida, columns=columnas_salida)

    # 4. Generar nombre de salida aplicando Regla 3.2 y Dirección de carpetas Regla 3.3
    #nombre_base, extension = os.path.splitext(nombre_archivo)
    #nombre_salida = f"{nombre_base}_converted_from_bittytax{extension}"
    #ruta_salida = nombre_salida.replace("inputs", "temp")

    # Asegurar que la carpeta destino existe antes de escribir
    #os.makedirs("/data/temp", exist_ok=True)

    df_out.to_csv(archivo_salida, index=False, float_format=format_float_output)
    print(f"📊 Conversión finalizada.")
    print(f"💾 Guardado en: {archivo_salida}")


if __name__ == "__main__":
    # Nombre del archivo que debe estar dentro de /data/inputs
    archivo_original = ARCHIVO_ENTRADA
    archivo_salida = archivo_original.replace('inputs', 'temp').replace('.csv', '_converted_from_bittytax.csv')
    convertir_bittytax_a_kraken(archivo_original, archivo_salida)
    
