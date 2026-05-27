
# Kraken Tax & FIFO Calculator (Spain Edition)

[![Bandit](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/bandit.yml/badge.svg)](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/bandit.yml)
[![Calidad de Código](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/linting.yml/badge.svg)](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/linting.yml)
[![CodeQL Advanced](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/codeql.yml/badge.svg)](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/codeql.yml)
![Dependencies](https://img.shields.io/badge/dependencies-up--to--date-brightgreen)

Este proyecto es una solución limitada para el procesamiento de archivos **Ledger de Kraken**, permitiendo la conversión de precios a Euros (EUR), el cálculo de ganancias/pérdidas patrimoniales mediante el método **FIFO** y la generación de un **informe fiscal** detallado para la AEAT (España).
Adicionalmente se permite la entrada en el formato **export de BittyTax** [BittyTax - Github](https://github.com/BittyTax/BittyTax) que soporta una larga lista de exchanges y wallets.


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
5. **`bittytax2kraken.py`**: Transforma el formato `BittyTax --export` en un formato similar al de Kraken para permitir entradas desde otros exchanges y wallets.

## ☑️ Requisitos SW

- Python 3.12.10 ó superior (https://www.python.org/downloads/)
- Git (p. ej. git version 2.53.0.windows.2) (https://git-scm.com/install/windows)

## 🛠️ Instalación

###  *Clonar y preparar entorno:*
    ```bash
    git clone <repositorio>
    cd <repositorio>
    python -m venv venv
    source venv/bin/activate  # venv\Scripts\activate o ó .\venv\Scripts\Activate.ps1 en Windows
    ```

###  *Instalar dependencias:*
    ```bash
    pip install -r requirements.txt
    ```

###  *Configurar Datos:*
    - Extrae tu informe ledger completo (desde tu alta en la plataforma) de Kraken (o el fichero obtenido desde BittyTax --export) y cópialo en /data/inputs

## 📋 Ejemplo de Uso en Local

```python
python ./app/main.py
```

## 🚀 Ejecución en Google Colab

Si prefieres no configurar un entorno local, puedes ejecutar este proyecto en la nube usando Google Colab. Sigue estos pasos:

### 1. Preparación en Google Drive
Para mantener la persistencia de los datos, el proyecto debe estar alojado en tu Drive:
1. Sube la carpeta raíz del proyecto (`Proyecto_Crypto_Reporter`) a tu Google Drive.
2. Asegúrate de mantener la estructura:
   - `Proyecto_Crypto_Reporter/app/` (Scripts .py)
   - `Proyecto_Crypto_Reporter/data/inputs/` (Tu archivo CSV de Kraken)

### 2. Abrir en Colab
Abre el cuaderno notebook.ipynb en Colab y sigue las instrucciones.

## 🛡️ Compromiso de Seguridad Total

### Tus datos no suben a GitHub

El archivo `.gitignore` está configurado para proteger tu privacidad:
- **Ignora** el contenido de `data/inputs/`, `data/temp` y `data/outputs/` para que tus datos no se suban a GitHub.
- **Mantiene** la estructura de carpetas gracias a los archivos `.gitkeep`.

### Estatus de Auditoría

- Escaneo de Vulnerabilidades: Auditado contra inyección de código y fugas de datos.

- Análisis Estático Avanzado: Motor de seguridad de GitHub que verifica la lógica del código.

- Calidad de Software: Cumplimiento de estándares profesionales de programación en Python.

### Mitigación de vulnerabilidades conocidas

- Sin Claves Privadas (API Keys): El script NO solicita tus claves de API. Solo utiliza consultas a los endpoints públicos de Kraken para obtener precios históricos de mercado. Tus fondos nunca están en riesgo.
- Ejecución 100% Local o en la Nube Controlada: Los datos de tus transacciones (ledgers.csv) se procesan en tu propia máquina o en tu instancia privada de Google Colab, si prefieres aún más seguridad. No se envía ninguna información personal a servidores externos.
- No se usan librerías sospechosas como Pickle. Los archivos de inventario son JSON legibles por humanos y 100% seguros.
- Conexiones Protegidas: Todas las llamadas a la API incluyen timeouts y gestión de errores para evitar bloqueos y garantizar la estabilidad del sistema.
- Todas las llamadas al sistema (como la instalación de dependencias en Google Colab) se realizan sin usar el shell del sistema (shell=False) y con argumentos estáticos, evitando ataques de inyección.
- El proyecto incluye escaneos automáticos de Dependabot para asegurar que todas las librerías utilizadas (Pandas, Requests, etc.) estén actualizadas y libres de vulnerabilidades conocidas.

## ⚠️ Limitaciones y Avisos Importantes (Caveats)

Este proyecto se encuentra en una fase temprana de desarrollo (Beta). Antes de utilizar los reportes para fines oficiales, por favor ten en cuenta lo siguiente:

- Alcance de las Pruebas: El motor de cálculo ha sido validado con un conjunto de datos muy reducido (basado en los ledgers reales de sólo dos usuarios y una variedad limitada de criptoactivos). Por ello, es probable que existan escenarios o tipos de operaciones no contemplados.

- Necesidad de Testing: Se buscan voluntarios dispuestos a probar la herramienta con diferentes tipos de carteras y reportar posibles discrepancias. Si encuentras un error, abrir un Issue en este repositorio es la mejor forma de ayudar.

- Fiabilidad de los Balances en los Ledgers: Se ha detectado que la información de saldos (balance) incluida en los archivos CSV descargados de Kraken no siempre se actualiza en tiempo real o puede contener inconsistencias tras ciertas operaciones complejas (como el staking o transferencias internas).

- Reconciliación Manual Obligatoria: Debido a lo anterior, la función de reconciliación de balances puede arrojar errores frecuentes. Es fundamental que el usuario verifique los balances finales en fechas clave (como el 31 de diciembre) comparando los resultados del script directamente con la información mostrada en la interfaz web de Kraken.com.

- Exención de Responsabilidad: Esta herramienta se proporciona "tal cual", con fines informativos y de ayuda al cálculo. No constituye asesoramiento fiscal ni legal. El usuario es el único responsable de la veracidad de los datos presentados ante las autoridades tributarias.


## ⚠️ Nota Legal

Este software es una herramienta de apoyo y consulta basada en la interpretación de la ley vigente. Los cálculos definitivos deben ser validados siempre por uno mismo y carecen de cualquier valor contractual o legal.
👉 Revisar siempre con asesor fiscal.

---

# 🧠 Próximas mejoras sugeridas

* Separar la salida de la cantidad principal y la comisión de esa salida para calcular 2 costes FIFO por separado. Además, el precio al que sale la comisión debería ser el del cálculo API, en vez del calculado comparando con la otra pata.
* Añadir texto al informe Fiscal con la ubicación en el programa Renta de los importes a rellenar e instrucciones de cómo hacerlo.
* Implementar sistema híbrido de caché para no tener que consultar siempre al API de Kraken.

---

# 📄 Licencia

MIT License

---

# English Version

# Kraken Tax & FIFO Calculator (Spain Edition)

[![Bandit](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/bandit.yml/badge.svg)](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/bandit.yml)
[![Code Quality](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/linting.yml/badge.svg)](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/linting.yml)
[![CodeQL Advanced](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/codeql.yml/badge.svg)](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/codeql.yml)
![Dependencies](https://img.shields.io/badge/dependencies-up--to--date-brightgreen)

This project is a limited solution for processing **Kraken Ledger** files, enabling price conversion to euros (EUR), capital gains/losses calculation using the **FIFO** method, and generation of a detailed **tax report** for the AEAT (Spain).
Additionally, input is supported in the **BittyTax export** format [BittyTax - GitHub](https://github.com/BittyTax/BittyTax), which supports a long list of exchanges and wallets.

## 🚀 Main Features

*   **Currency Conversion:** Automatic retrieval of historical prices through the Kraken API for each transaction.
*   **Staking Handling:** Detection of staking movements (normalization of assets such as `ETH` and `ETH.S`) to avoid breaking the holding period of FIFO lots.
*   **Fee Management:** Integration of fees into the acquisition cost and reduction of the disposal value, according to tax rules.
*   **Data Integrity:** Absolute ordering through `orden_original` to ensure the calculation respects the exact ledger sequence.
*   **Balance Validation:** Final reconciliation of FIFO queues against the official balances reported by the exchange.
*   **Spanish Tax Report:** Excel export with specific tabs for Trading, Airdrops/Income, and opening/closing yearly balances.

## 📁 Project Structure

1.  **`main.py`**: Pipeline orchestrator. Controls the flow and avoids reprocessing the conversion if the file already exists.
2.  **`EUR_Converter_pro.py`**: Translates the original ledger into EUR. Handles complex multi-leg operations and assigns a sequential order ID.
3.  **`FIFO_calculator.py`**: The accounting engine. Manages `deque` queues by asset, calculates gains, and generates a historical inventory state (`.pkl`).
4.  **`Fiscal_Reporter_ES.py`**: Report generator. Classifies each operation into its corresponding tax box and creates the final Excel file.
5.  **`bittytax2kraken.py`**: Transforms the `BittyTax --export` format into a Kraken-like format to support input from other exchanges and wallets.

## ☑️ Software Requirements

- Python 3.12.10 or higher (https://www.python.org/downloads/)
- Git (for example, git version 2.53.0.windows.2) (https://git-scm.com/install/windows)

## 🛠️ Installation

###  *Clone and prepare the environment:*
    ```bash
    git clone <repository>
    cd <repository>
    python -m venv venv
    source venv/bin/activate  # venv\Scripts\activate or .\venv\Scripts\Activate.ps1 on Windows
    ```

###  *Install dependencies:*
    ```bash
    pip install -r requirements.txt
    ```

###  *Configure data:*
    - Export your complete ledger report from Kraken (from the date you joined the platform), or use the file obtained from BittyTax --export, and copy it to /data/inputs

## 📋 Local Usage Example

```python
python ./app/main.py
```

## 🚀 Running in Google Colab

If you prefer not to configure a local environment, you can run this project in the cloud using Google Colab. Follow these steps:

### 1. Preparation in Google Drive
To keep data persistent, the project must be hosted in your Drive:
1. Upload the project root folder (`Proyecto_Crypto_Reporter`) to your Google Drive.
2. Make sure the following structure is preserved:
   - `Proyecto_Crypto_Reporter/app/` (.py scripts)
   - `Proyecto_Crypto_Reporter/data/inputs/` (your Kraken CSV file)

### 2. Open in Colab
Open the notebook.ipynb notebook in Colab and follow the instructions.

## 🛡️ Full Security Commitment

### Your data is not uploaded to GitHub

The `.gitignore` file is configured to protect your privacy:
- It **ignores** the contents of `data/inputs/`, `data/temp`, and `data/outputs/` so your data is not uploaded to GitHub.
- It **preserves** the folder structure thanks to the `.gitkeep` files.

### Audit Status

- Vulnerability Scanning: Audited against code injection and data leaks.

- Advanced Static Analysis: GitHub security engine that verifies the code logic.

- Software Quality: Compliance with professional Python programming standards.

### Known vulnerability mitigation

- No Private Keys (API Keys): The script does NOT request your API keys. It only uses queries to Kraken public endpoints to obtain historical market prices. Your funds are never at risk.
- 100% Local or Controlled Cloud Execution: Your transaction data (ledgers.csv) is processed on your own machine or in your private Google Colab instance, if you prefer even more security. No personal information is sent to external servers.
- No suspicious libraries such as Pickle are used. Inventory files are human-readable JSON and 100% safe.
- Protected Connections: All API calls include timeouts and error handling to avoid hangs and ensure system stability.
- All system calls (such as dependency installation in Google Colab) are performed without using the system shell (shell=False) and with static arguments, preventing injection attacks.
- The project includes automatic Dependabot scans to ensure that all libraries used (Pandas, Requests, etc.) are up to date and free of known vulnerabilities.

## ⚠️ Limitations and Important Notices (Caveats)

This project is in an early development phase (Beta). Before using the reports for official purposes, please keep the following in mind:

- Testing Scope: The calculation engine has been validated with a very small dataset (based on the real ledgers of only two users and a limited range of cryptoassets). Therefore, there are likely scenarios or operation types that are not yet covered.

- Need for Testing: Volunteers willing to test the tool with different types of wallets and report possible discrepancies are welcome. If you find an error, opening an Issue in this repository is the best way to help.

- Reliability of Ledger Balances: The balance information included in CSV files downloaded from Kraken has been found not always to update in real time, and it may contain inconsistencies after certain complex operations (such as staking or internal transfers).

- Mandatory Manual Reconciliation: Because of the above, the balance reconciliation function may often report errors. Users must verify final balances on key dates (such as December 31) by comparing the script results directly with the information shown in the Kraken.com web interface.

- Disclaimer: This tool is provided "as is", for informational purposes and as calculation support. It does not constitute tax or legal advice. The user is solely responsible for the accuracy of the data submitted to the tax authorities.

## ⚠️ Legal Notice

This software is a support and consultation tool based on an interpretation of current law. Final calculations must always be validated by the user and have no contractual or legal value.
👉 Always review with a tax advisor.

---

# 🧠 Suggested Future Improvements

* Separate the outgoing principal amount and the fee for that disposal in order to calculate 2 FIFO costs independently. In addition, the price at which the fee leaves should be the API-calculated price, instead of the price calculated by comparison with the other leg.
* Add text to the tax report indicating where the relevant amounts should be entered in the Spanish income tax program, together with instructions on how to do it.
* Implement a hybrid cache system to avoid always querying the Kraken API.

---

# 📄 License

MIT License

---

