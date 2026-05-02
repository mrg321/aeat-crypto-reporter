# Kraken Tax & FIFO Calculator (Spain Edition)

Este proyecto es una solución integral para el procesamiento de archivos **Ledger de Kraken**, permitiendo la conversión de precios a Euros (EUR), el cálculo de ganancias/pérdidas patrimoniales mediante el método **FIFO** y la generación de un **informe fiscal** detallado para la AEAT (España).

## 🚀 Funcionalidades Principales

*   **Conversión de Divisas:** Obtención automática de precios históricos vía API de Kraken para cada operación.
*   **Tratamiento de Staking:** Detección de movimientos de staking (normalización de activos como `ETH` y `ETH.S`) para evitar rupturas en la antigüedad de los lotes FIFO.
*   **Gestión de Comisiones:** Integración de comisiones (`fees`) en el coste de adquisición y minoración del valor de transmisión, según normativa fiscal.
*   **Integridad de Datos:** Ordenación absoluta mediante `orden_original` para garantizar que el cálculo respeta la secuencia exacta del ledger.
*   **Validación de Balances:** Reconciliación final de las colas FIFO contra los balances oficiales reportados por el exchange.
*   **Informe Fiscal ES:** Exportación a Excel con pestañas específicas para Trading, Airdrops/Rendimientos y balances a inicio/cierre de año.

## 📁 Estructura del Proyecto

1.  **`main.py`**: Orquestador del pipeline. Controla el flujo y evita re-procesar la conversión si el archivo ya existe.
2.  **`EUR_Converter_pro.py`**: Traduce el ledger original a EUR. Gestiona operaciones complejas multi-pata y asigna un ID secuencial de orden.
3.  **`FIFO_calculator.py`**: El motor contable. Gestiona las colas `deque` por activo, calcula las ganancias y genera un estado de inventario histórico (`.pkl`).
4.  **`Fiscal_Reporter_ES.py`**: Generador de informes. Clasifica cada operación en su casilla fiscal correspondiente y crea el Excel final.

## 🛠️ Requisitos e Instalación

Es necesario tener instalado Python 3.8+ y las siguientes dependencias:
```bash
pip install pandas xlsxwriter requests