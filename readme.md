
# Kraken Tax & FIFO Calculator (Spain Edition)

[![Bandit](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/bandit.yml/badge.svg)](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/bandit.yml)
[![Calidad de Código](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/linting.yml/badge.svg)](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/linting.yml)
[![CodeQL Advanced](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/codeql.yml/badge.svg)](https://github.com/mrg321/aeat-crypto-reporter/actions/workflows/codeql.yml)
![Dependencies](https://img.shields.io/badge/dependencies-up--to--date-brightgreen)

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
    - Extrae tu informe ledger completo (desde tu alta en la plataforma) de Kraken y cópialo en /data/inputs

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
Crea un nuevo cuaderno (.ipynb) en Colab y ejecuta las siguientes celdas:

**Paso A: Montar Drive y Configurar Rutas**
```python
from google.colab import drive
import os
import sys

# Esto abrirá una ventana pidiéndote permiso para acceder a tus archivos
drive.mount('/content/drive')

# Cambiamos el directorio de trabajo a tu carpeta del proyecto
# Asegúrate de que el nombre coincida exactamente con la carpeta que creaste
os.chdir('/content/drive/MyDrive/Proyecto_Crypto_Reporter')

# Verificamos que estamos en el sitio correcto
print("Directorio actual:", os.getcwd())
!ls

# Añadimos la carpeta /app a la lista de sitios donde Python busca archivos
sys.path.append(os.path.abspath('./app'))

# Ahora se ejecuta main dentro de /app
!python app/main.py
```

## 🛡️ Compromiso de Seguridad Total

### Tus datos no suben a GitHub:

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




## ⚠️ Nota Legal

Este software es una herramienta de apoyo y consulta basada en la interpretación de la ley vigente. Los cálculos definitivos deben ser validados siempre por uno mismo y carecen de cualquier valor contractual o legal.
👉 Revisar siempre con asesor fiscal.

---

# 🧠 Próximas mejoras sugeridas

* Separar la salida de la cantidad principal y la comisión de esa salida para calcular 2 costes FIFO por separado. Además, el precio al que sale la comisión debería ser el del cálculo API, en vez del calculado comparando con la otra pata.
* Añadir texto al informe Fiscal con la ubicación en el programa Renta de los importes a rellenar e instrucciones de cómo hacerlo.
* Implementar sistema híbrido de caché para no tener que consultar siempre al API de Kraken


---

# 📄 Licencia

MIT License

---

