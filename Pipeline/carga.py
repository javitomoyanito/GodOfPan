import sqlite3
import os
from datetime import datetime

def ejecutar_carga(df):
    os.makedirs("database", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    conexion = sqlite3.connect("database/datamart.db")
    cursor = conexion.cursor()

    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id_pedido INTEGER PRIMARY KEY,
            fecha_pedido TEXT,
            rut_cliente TEXT,
            nombre_cliente TEXT,
            region TEXT NOT NULL,
            producto TEXT,
            categoria TEXT,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            descuento_pct REAL,
            estado_pedido TEXT,
            fecha_despacho TEXT,
            total_venta REAL,
            segmento_precio TEXT
        )
        """)

        conexion.commit()

        df.to_sql("pedidos", conexion, if_exists="replace", index=False)

        consulta_region = """
        SELECT region, SUM(total_venta) AS ventas_totales
        FROM pedidos
        GROUP BY region
        ORDER BY ventas_totales DESC;
        """

        consulta_categoria = """
        SELECT categoria, SUM(total_venta) AS ventas_totales
        FROM pedidos
        GROUP BY categoria
        ORDER BY ventas_totales DESC;
        """

        ventas_region = cursor.execute(consulta_region).fetchall()
        ventas_categoria = cursor.execute(consulta_categoria).fetchall()

        conexion.commit()

        with open("logs/carga.log", "w", encoding="utf-8") as log:
            log.write("ETAPA 4: CARGA A BASE DE DATOS\n")
            log.write(f"Fecha: {datetime.now()}\n")
            log.write("Base de datos: SQLite\n")
            log.write(f"Registros cargados: {len(df)}\n")
            log.write("\nVentas por región:\n")
            log.write(str(ventas_region))
            log.write("\nVentas por categoría:\n")
            log.write(str(ventas_categoria))

        print("Ventas por región:")
        print(ventas_region)

        print("\nVentas por categoría:")
        print(ventas_categoria)

    except Exception as e:
        conexion.rollback()
        print("Error en la carga. Se aplicó ROLLBACK.")
        print(e)

    finally:
        conexion.close()