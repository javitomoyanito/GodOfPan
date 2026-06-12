"""
Módulo de Persistencia y Carga en Base de Datos Relacional
Inserción ordenada y validación final de integridad sobre SQLite.
"""

import logging
import sqlite3
from pathlib import Path
import pandas as pd

DIRECTORIO_RAIZ = Path(__file__).resolve().parent
RUTA_VALIDATED = DIRECTORIO_RAIZ / "data" / "validated"
RUTA_DB = DIRECTORIO_RAIZ / "data" / "database"
RUTA_LOGS = DIRECTORIO_RAIZ / "logs"

RUTA_DB.mkdir(parents=True, exist_ok=True)
RUTA_LOGS.mkdir(parents=True, exist_ok=True)

SITIO_DB = RUTA_DB / "GodOfPan.db"

logging.basicConfig(
    filename=RUTA_LOGS / "carga.log",
    level=logging.INFO,
    format="%(asctime)s [C] %(levelname)s: %(message)s",
)

# Definición semántica del Esquema Relacional
DDL_TABLAS = """
CREATE TABLE IF NOT EXISTS clientes (
    id_cliente INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    rut TEXT NOT NULL UNIQUE,
    email TEXT,
    telefono TEXT,
    comuna TEXT,
    fecha_registro TEXT,
    edad INTEGER,
    rango_etario TEXT
);

CREATE TABLE IF NOT EXISTS productos (
    id_producto INTEGER PRIMARY KEY,
    nombre_producto TEXT NOT NULL,
    categoria TEXT,
    precio_unitario_clp INTEGER NOT NULL,
    stock INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pedidos (
    id_pedido INTEGER PRIMARY KEY,
    id_cliente INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad REAL NOT NULL,
    monto_total_clp REAL NOT NULL,
    fecha_pedido TEXT,
    fecha_despacho TEXT,
    estado TEXT,
    metodo_pago TEXT,
    dias_despacho REAL,
    monto_normalizado REAL,
    pago_debito INTEGER,
    pago_credito INTEGER,
    pago_transferencia INTEGER,
    pago_webpay INTEGER,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente),
    FOREIGN KEY (id_producto) REFERENCES productos(id_producto)
);
"""

DDL_INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_cli_ref ON pedidos(id_cliente);",
    "CREATE INDEX IF NOT EXISTS idx_prod_ref ON pedidos(id_producto);",
    "CREATE INDEX IF NOT EXISTS idx_fecha_ref ON pedidos(fecha_pedido);",
    "CREATE INDEX IF NOT EXISTS idx_comuna_cli ON clientes(comuna);",
    "CREATE INDEX IF NOT EXISTS idx_cat_prod ON productos(categoria);",
]

def inicializar_infraestructura_db(conexion_activa):
    """Aplica las sentencias SQL de creación de tablas e índices en el motor destino."""
    manejador = conexion_activa.cursor()
    manejador.executescript(DDL_TABLAS)
    for sentencia_idx in DDL_INDICES:
        manejador.execute(sentencia_idx)
    conexion_activa.commit()
    logging.info("Infraestructura de Tablas e Índices creada/verificada.")
    print(" -> Esquema de base de datos inicializado.")

def persistir_bloque_datos(conexion_activa, dataframe, nombre_tabla, modo_insercion="replace"):
    """Inserta el contenido de un DataFrame en una tabla física aplicando truncado previo si corresponde."""
    if dataframe.empty:
        print(f" [Aviso] Tabla {nombre_tabla}: DataFrame vacío.")
        logging.warning("Tabla %s sin registros para insertar.", nombre_tabla)
        return 0
    
    recuento_filas = len(dataframe)
    
    if modo_insercion == "replace":
        manejador = conexion_activa.cursor()
        manejador.execute(f"DELETE FROM {nombre_tabla};")
        conexion_activa.commit()
        logging.info("Truncado previo realizado sobre tabla: %s", nombre_tabla)
    
    dataframe.to_sql(nombre_tabla, conexion_activa, if_exists="append", index=False)
    logging.info("Escritura Completa: tabla=%s | total_filas=%d", nombre_tabla, recuento_filas)
    print(f"    * {nombre_tabla}: {recuento_filas} registros insertados.")
    return recuento_filas

def test_integridad_referencial(conexion_activa):
    """Busca discrepancias o huérfanos relacionales directamente en el motor SQLite."""
    manejador = conexion_activa.cursor()
    manejador.execute("""
        SELECT COUNT(*) FROM pedidos p
        LEFT JOIN clientes c ON p.id_cliente = c.id_cliente
        LEFT JOIN productos pr ON p.id_producto = pr.id_producto
        WHERE c.id_cliente IS NULL OR pr.id_producto IS NULL
    """)
    conteo_huerfanos = manejador.fetchone()[0]
    
    if conteo_huerfanos > 0:
        logging.warning("Falla crítica post-carga: %d llaves foráneas rotas detected.", conteo_huerfanos)
        print(f" [Atención] Se detectaron {conteo_huerfanos} registros con FK inválidas en el motor.")
    else:
        logging.info("Verificación relacional exitosa: Cero huérfanos.")
        print(" -> Integridad relacional en motor: OK")
    return conteo_huerfanos

def compilar_metricas_carga(conexion_activa):
    """Extrae KPIs de los datos consolidados en la base de datos relacional."""
    manejador = conexion_activa.cursor()
    
    manejador.execute("SELECT COUNT(*) FROM clientes")
    num_clientes = manejador.fetchone()[0]
    
    manejador.execute("SELECT COUNT(*) FROM productos")
    num_productos = manejador.fetchone()[0]
    
    manejador.execute("SELECT COUNT(*) FROM pedidos")
    num_pedidos = manejador.fetchone()[0]
    
    manejador.execute("SELECT SUM(monto_total_clp) FROM pedidos WHERE estado = 'entregado'")
    monto_ventas = manejador.fetchone()[0] or 0
    
    print("\n" + "·"*60 + "\n--- RESUMEN CONSOLIDADO DE LA BD ---")
    print(f" Volumen Clientes:   {num_clientes:,}")
    print(f" Volumen Productos:  {num_productos:,}")
    print(f" Volumen Pedidos:    {num_pedidos:,}")
    print(f" Recaudación Neta (Entregados): ${monto_ventas:,.0f} CLP")
    print("·"*60)
    
    logging.info("Métricas BD final -> Clientes: %d | Productos: %d | Pedidos: %d | Ventas: %d", 
                num_clientes, num_productos, num_pedidos, monto_ventas)

def persistir_pipeline_completo():
    """Ejecuta la secuencia de inserción masiva a la base de datos."""
    print("\n" + "="*60 + "\nETAPA 4: PERSISTENCIA EN MOTOR RELACIONAL\n" + "="*60)
    
    try:
        print(" Lector de datos validados en marcha...")
        datos_clientes = pd.read_csv(RUTA_VALIDATED / "clientes.csv")
        datos_productos = pd.read_csv(RUTA_VALIDATED / "productos.csv")
        datos_pedidos = pd.read_csv(RUTA_VALIDATED / "pedidos.csv")
        
        logging.info("Lectura pre-carga -> Clientes: %d, Productos: %d, Pedidos: %d", 
                    len(datos_clientes), len(datos_productos), len(datos_pedidos))
        
        # Conexión nativa a base de datos local
        conexion_db = sqlite3.connect(SITIO_DB)
        inicializar_infraestructura_db(conexion_db)
        
        conexion_db.execute("PRAGMA foreign_keys = OFF;")
        
        print("\n Escribiendo registros en tablas físicas...")
        ins_cli = persistir_bloque_datos(conexion_db, datos_clientes, "clientes", modo_insercion="replace")
        ins_prod = persistir_bloque_datos(conexion_db, datos_productos, "productos", modo_insercion="replace")
        ins_ped = persistir_bloque_datos(conexion_db, datos_pedidos, "pedidos", modo_insercion="replace")
        
        conexion_db.execute("PRAGMA foreign_keys = ON;")
        
        print("\n Auditando restricciones físicas...")
        test_integridad_referencial(conexion_db)
        
        compilar_metricas_carga(conexion_db)
        conexion_db.close()
        
        total_acumulado = ins_cli + ins_prod + ins_ped
        logging.info("Fase de persistencia concluida. Registros totales en BD: %d", total_acumulado)
        print(f"\n[ÉXITO] Pipeline Finalizado. {total_acumulado} filas insertadas en {SITIO_DB}")
        
        return {"clientes": ins_cli, "productos": ins_prod, "pedidos": ins_ped, "db_path": str(SITIO_DB)}
        
    except FileNotFoundError:
        logging.error("Falta de archivos en validated. Verifique ejecuciones de etapas previas.")
        print(f"\n Error: Falta de recursos en {RUTA_VALIDATED}. Ejecute el pipeline en orden de etapas.")
        raise
    except Exception as e:
        logging.error("Falla crítica en carga relacional: %s", e)
        raise

if __name__ == "__main__":
    persistir_pipeline_completo()