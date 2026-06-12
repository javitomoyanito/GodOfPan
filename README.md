Este ecosistema de datos implementa una arquitectura robusta de Pipeline Automatizado (ETL) modular en Python. Su propósito central es la extracción de fuentes en bruto, depuración sintáctica, auditoría multidimensional bajo reglas de negocio severas y la consolidación de la información en un motor relacional local.

---

## Requisitos e Instalación de Dependencias

El entorno está diseñado y optimizado para ejecutarse sobre Python 3.10+. 

Para inicializar las dependencias del proyecto, abra su terminal en la raíz del directorio donde se alojan los scripts y ejecute el siguiente comando:

```bash
pip install pandas pandera openpyxl
pandas: Soporta todo el procesamiento analítico, vectorización y re-cálculos de matrices.

pandera: Proporciona el motor de tipado estricto en tiempo de ejecución y auditoría perezosa (lazy validation).

🏗️ Flujo de Operación y Arquitectura
El pipeline opera de forma estrictamente secuencial dividiéndose en 4 etapas independientes. Los datos transicionan de un estado a otro mediante el aislamiento en directorios específicos que marcan el ciclo de madurez de la información:

[ data/raw/ ] ------> [ data/clean/ ] ------> [ data/validated/ ] ------> [ core_system.db ]
   (Ingesta)             (Limpieza)               (Validación)                (Base de Datos)
                                                      |
                                                      └--> [ data/errors/ ] (Rechazados)
Caja de Herramientas y Directorios Automatizados
data/raw/: Almacén de lectura inmutable para los archivos de origen (clientes.csv, productos.csv, pedidos.csv).

data/clean/: Capa intermedia con textos normalizados, fechas ISO homogeneizadas e imputaciones resueltas.

data/validated/: Set de datos puros que han cumplido el 100% de los criterios estructurales y lógicos.

data/errors/: Registros descartados enriquecidos automáticamente con una columna explicativa llamada motivo_rechazo.

data/database/: Destino analítico donde se aloja el archivo binario del motor SQLite.

logs/: Historial de trazas segregado por archivo para una auditoría minuciosa del software.

Configuración de los Componentes del Pipeline
1. Ingesta (ingesta.py)
Propósito: Ejecuta el control de acceso y lectura inicial sobre los recursos .csv.

Métricas en Pantalla: Despliega inmediatamente un reporte diagnóstico con las dimensiones de las matrices (filas x columnas), tipos internos (dtypes), previsualización de cabeceras, recuentos exactos de valores NaN/Null y sumatoria de duplicados idénticos.

Garantía: No altera un solo byte del origen. Actúa como mecanismo transparente de auditoría inicial.

2. Limpieza y Transformación (limpieza.py)
Propósito: Conversión de tipos, homogenización semántica y enriquecimiento algorítmico.

Procesamientos Clave:

Fechas Estándar: Conversión dinámica de múltiples formatos de texto (DD/MM/AAAA, DD-MM-AAAA) a cadenas estructuradas bajo norma ISO (AAAA-MM-DD).

Homologación Geográfica y Financiera: Corrección ortográfica y de caracteres especiales para localizaciones (Comunas) y tipos de transacción a través de mapeos explícitos en diccionarios de control.

Imputación de Vacíos: Relleno de datos críticos mediante el cálculo de la mediana aritmética de la distribución.

Ingeniería de Características:

Segmentación: Clasificación por intervalos de edad en rangos discretos.

Métricas de Tiempo: Generación de la columna dias_despacho evaluando deltas cronológicos.

Normalización: Escalamiento Lineal Min-Max de variables numéricas acotando el espectro financiero al rango [0, 1].

Codificación: Despliegue de variables categóricas complejas mediante codificación binaria One-Hot Encoding.

3. Validación y Calidad (validacion.py)
Propósito: Actúa como cortafuegos lógico aislando los datos viables de aquellos corruptos o inconsistentes.

Validación Estructural (pandera): Controla de manera perezosa (evaluando todas las filas antes de fallar) expresiones regulares estrictas para correos electrónicos, patrones de telefonía móvil internacional y rangos físicos absolutos para existencias y precios.

Validación Semántica de Negocio:

Módulo 11: Valida de manera algorítmica y matemática la autenticidad del identificador nacional chileno (RUT), calculando su dígito verificador.

Coherencia de Procesos: Descarta registros donde la fecha de envío sea inferior a la de compra, o donde órdenes canceladas muestren logística completada.

Validación de Totales: Evalúa mediante análisis matemático que el campo de montos finales sea idéntico al producto cruzado de cantidad × precio_unitario.

Integridad Referencial Analítica: Comprueba de forma cruzada en memoria que las claves foráneas de las transacciones existan realmente en las tablas maestras antes de pasar a la base de datos.

4. Carga y Persistencia (carga.py)
Propósito: Persistencia transaccional de los sets aprobados sobre un motor SQLite.

Modelamiento: Define el DDL relacional generando esquemas estrictos dotados de llaves primarias (PRIMARY KEY) y restricciones de integridad (FOREIGN KEY).

Rendimiento: Genera índices analíticos (CREATE INDEX) en las columnas prioritarias para acelerar las futuras consultas operativas.

Cierre de Ciclo: Efectúa un barrido final de base de datos buscando llaves huérfanas mediante consultas SQL directas y genera un sumario ejecutivo en la terminal con los volúmenes finales estables y métricas consolidadas de recaudación.

5. Orquestador Central (main.py)
Propósito: Automatiza y enlaza los componentes de inicio a fin bajo un ambiente protegido. Si una de las capas sufre un desbordamiento o error imprevisto, el orquestador captura la excepción, inyecta la traza detallada del error (exc_info) dentro de pipeline.log para el equipo de desarrollo, interrumpe el flujo de forma segura y notifica al sistema operativo finalizando con un estado de salida de alerta (sys.exit(1)).

Ejecución del Sistema
Para disparar todo el procesamiento y ver el comportamiento del pipeline en tiempo real, invoque al módulo orquestador desde su terminal:

Bash
python main.py
El estado de avance de las tareas se proyectará de forma limpia en la pantalla y se grabará un archivo acumulativo de trazas generales en data/pipeline.log 