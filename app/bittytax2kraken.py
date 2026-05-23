import os
import pandas as pd


def determinar_wallet(asset):
    """Determina si el activo es Fiat o Crypto."""
    if pd.isna(asset) or str(asset).strip() == "":
        return ""
    fiats = {"EUR", "USD", "GBP", "JPY", "CAD", "AUD", "CHF"}
    return "fiat" if str(asset).upper() in fiats else "crypto"


def calcular_tasa(amount_eur, amount):
    """Calcula la tasa evitando la división por cero o nulos."""
    try:
        if pd.isna(amount_eur) or pd.isna(amount) or float(amount) == 0:
            return 0.0
        return abs(float(amount_eur) / float(amount))
    except (ValueError, TypeError):
        return 0.0


def convertir_bittytax_a_kraken(archivo_entrada, archivo_salida):
    """Convierte un CSV exportado de BittyTax al formato de Kraken."""
    df_in = pd.read_csv(archivo_entrada)

    filas_salida = []

    txid_counter = 1
    refid_counter = 1

    # Clasificación de tipos basada en regla 3.1.4
    tipos_entrada = {
        "Deposit",
        "Unstake",
        "Mining",
        "Staking-Reward",
        "Staking*",
        "Interest",
        "Dividend",
        "Income",
        "Gift-Received",
        "Fork",
        "Airdrop",
        "Referral",
        "Cashback",
        "Fee-Rebate",
        "Loan",
        "Margin-Gain",
        "Margin-Fee-Rebate",
    }

    tipos_salida = {
        "Withdrawal",
        "Stake",
        "Spend",
        "Gift-Sent",
        "Gift-Spouse",
        "Charity-Sent",
        "Lost",
        "Loan-Repayment",
        "Loan-Interest",
        "Margin-Loss",
        "Margin-Fee",
    }

    for _, row in df_in.iterrows():
        b_type = str(row.get("Type", "")).strip()
        timestamp = row.get("Timestamp", "")

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
                    "amount": abs(float(buy_amt)) if buy_amt else 0,
                    "fee": row.get("Fee Quantity", 0)
                    if row.get("Fee Asset") == buy_asset
                    else 0,
                    "balance": "",
                    "orden_original": "",
                    "amount_eur": abs(float(buy_val_eur)) if buy_val_eur else 0,
                    "fee_eur": row.get("Fee Value", 0)
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
                    "amount": -abs(float(sell_amt)) if sell_amt else 0,
                    "fee": row.get("Fee Quantity", 0)
                    if row.get("Fee Asset") == sell_asset
                    else 0,
                    "balance": "",
                    "orden_original": "",
                    "amount_eur": -abs(float(sell_val_eur))
                    if sell_val_eur
                    else 0,
                    "fee_eur": row.get("Fee Value", 0)
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
        elif b_type in tipos_entrada:
            buy_asset = row.get("Buy Asset", "")
            if pd.notna(buy_asset) and str(buy_asset).strip() != "":
                buy_amt = row.get("Buy Quantity", 0)
                buy_val_eur = row.get("Buy Value", 0)
                w_type = determinar_wallet(buy_asset)

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
                    "amount": abs(float(buy_amt)) if buy_amt else 0,
                    "fee": row.get("Fee Quantity", 0),
                    "balance": "",
                    "orden_original": "",
                    "amount_eur": abs(float(buy_val_eur)) if buy_val_eur else 0,
                    "fee_eur": row.get("Fee Value", 0),
                    "tasa": calcular_tasa(buy_val_eur, buy_amt),
                    "EUR_conversion": "Imported from bittytax export",
                    "legs_subclasses": w_type,
                }
                filas_salida.append(pata_entrada)
                txid_counter += 1
                refid_counter += 1

        # --- REGLA 3.1.3: SALIDAS DE ACTIVOS (1 Pata Negativa - Columnas Sell) ---
        elif b_type in tipos_salida:
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
                    "amount": -abs(float(sell_amt)) if sell_amt else 0,
                    "fee": row.get("Fee Quantity", 0),
                    "balance": "",
                    "orden_original": "",
                    "amount_eur": -abs(float(sell_val_eur))
                    if sell_val_eur
                    else 0,
                    "fee_eur": row.get("Fee Value", 0),
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

    df_out.to_csv(archivo_salida, index=False)
    print(f"📊 Conversión finalizada.")
    print(f"💾 Guardado en: {archivo_salida}")


if __name__ == "__main__":
    # Nombre del archivo que debe estar dentro de /data/inputs
    archivo_original = 'data/inputs/MRG_BittyTax_Export.csv'
    archivo_salida = archivo_original.replace('inputs', 'temp').replace('.csv', '_converted_from_bittytax.csv')
    convertir_bittytax_a_kraken(archivo_original, archivo_salida)
    