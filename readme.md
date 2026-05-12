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

## ☑️ Requisitos SW

- Python 3.12.10 ó superior (https://www.python.org/downloads/)
- Git (p. ej. git version 2.53.0.windows.2) (https://git-scm.com/install/windows)

## 🛠️ Instalación

##  *Clonar y preparar entorno:*
    ```bash
    git clone <repositorio>
    cd <repositorio>
    python -m venv venv
    source venv/bin/activate  # venv\Scripts\activate o ó .\venv\Scripts\Activate.ps1 en Windows
    ```

##  *Instalar dependencias:*
    ```bash
    pip install -r requirements.txt
    ```

##  *Configurar Datos:*
    - Extrae tu informe ledger de Kraken y cópialo en /data/inputs

## 📋 Ejemplo de Uso

```python
python ./app/main.py
```

## 🔒 Seguridad y Git

El archivo `.gitignore` está configurado para proteger tu privacidad:
- **Ignora** los archivos `.env` con tus datos personales.
- **Ignora** el contenido de `data/inputs/` y `data/outputs/` para que tus bases de cotización reales y tus informes finales no se suban a GitHub.
- **Mantiene** la estructura de carpetas gracias a los archivos `.gitkeep`.

## ⚠️ Nota Legal

Este software es una herramienta de apoyo y consulta basada en la interpretación de la ley vigente. Los cálculos definitivos deben ser validados siempre por uno mismo y carecen de cualquier valor contractual o legal.
👉 Revisar siempre con asesor fiscal.

---

# 🧠 Próximas mejoras sugeridas

* Separar la salida de la cantidad principal y la comisión de esa salida para calcular 2 costes FIFO por separado. Además, el precio al que sale la comisión debería ser el del cálculo API, en vez del calculado comparando con la otra pata.
* Añadir texto al informe Fiscal con la ubicación en el programa Renta de los importes a rellenar.


---

# 📄 Licencia

MIT License

---