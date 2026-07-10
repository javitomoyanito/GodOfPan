from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

import numpy as np

RUTA_BD = Path("database/datamart.db")
RUTA_RECHAZADOS = Path("data/errors/rechazados_bd.csv")
RUTA_REGION = Path("data/reports/ventas_por_region.csv")
RUTA_CATEGORIA = Path("data/reports/ventas_por_categoria.csv")
RUTA_LOG = Path("logs/carga.log")


def configurar_logger() -> logging.Logger:
    RUTA_LOG.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("carga")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = logging.FileHandler(
        RUTA_LOG,
        mode="w",
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def convertir_nulos(valor):
    """
    Convierte tipos de pandas y NumPy a tipos nativos de Python
    compatibles con SQLite.
    """
    if pd.isna(valor):
        return None

    if isinstance(valor, np.integer):
        return int(valor)

    if isinstance(valor, np.floating):
        return float(valor)

    if isinstance(valor, np.bool_):
        return bool(valor)

    return valor


def preparar_registros(df: pd.DataFrame) -> list[tuple]:
    columnas = [
        "id_pedido",
        "fecha_pedido",
        "rut_cliente",
        "nombre_cliente",
        "region",
        "producto",
        "categoria",
        "cantidad",
        "precio_unitario",
        "descuento_pct",
        "estado_pedido",
        "fecha_despacho",
        "total_venta",
        "segmento_precio"
    ]

    registros = []

    for fila in df[columnas].itertuples(index=False, name=None):
        fila_convertida = tuple(
            convertir_nulos(valor)
            for valor in fila
        )

        registros.append(fila_convertida)

    return registros


def ejecutar_carga(
    df_validos: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carga registros válidos a SQLite usando una transacción."""
    logger = configurar_logger()

    RUTA_BD.parent.mkdir(parents=True, exist_ok=True)
    RUTA_RECHAZADOS.parent.mkdir(parents=True, exist_ok=True)
    RUTA_REGION.parent.mkdir(parents=True, exist_ok=True)

    conexion = sqlite3.connect(RUTA_BD)

    consulta_region = """
        SELECT
            region,
            ROUND(SUM(total_venta), 2) AS ventas_totales
        FROM pedidos
        GROUP BY region
        ORDER BY ventas_totales DESC;
    """

    consulta_categoria = """
        SELECT
            categoria,
            ROUND(SUM(total_venta), 2) AS ventas_totales
        FROM pedidos
        GROUP BY categoria
        ORDER BY ventas_totales DESC;
    """

    try:
        cursor = conexion.cursor()

        # Iniciar transacción explícita.
        cursor.execute("BEGIN TRANSACTION;")

        cursor.execute("DROP TABLE IF EXISTS pedidos;")

        cursor.execute(
            """
            CREATE TABLE pedidos (
                id_pedido INTEGER PRIMARY KEY,
                fecha_pedido TEXT NOT NULL,
                rut_cliente TEXT NOT NULL,
                nombre_cliente TEXT NOT NULL,
                region TEXT NOT NULL,
                producto TEXT NOT NULL,
                categoria TEXT NOT NULL
                    CHECK (categoria IN ('Tecnologia', 'Hogar', 'Moda')),
                cantidad INTEGER NOT NULL
                    CHECK (cantidad > 0),
                precio_unitario REAL NOT NULL
                    CHECK (precio_unitario > 0),
                descuento_pct REAL NOT NULL
                    CHECK (descuento_pct BETWEEN 0 AND 100),
                estado_pedido TEXT NOT NULL
                    CHECK (
                        estado_pedido IN (
                            'pendiente',
                            'despachado',
                            'entregado',
                            'cancelado'
                        )
                    ),
                fecha_despacho TEXT,
                total_venta REAL NOT NULL
                    CHECK (total_venta >= 0),
                segmento_precio TEXT NOT NULL
                    CHECK (
                        segmento_precio IN ('Bajo', 'Medio', 'Alto')
                    )
            );
            """
        )

        sentencia_insert = """
            INSERT INTO pedidos (
                id_pedido,
                fecha_pedido,
                rut_cliente,
                nombre_cliente,
                region,
                producto,
                categoria,
                cantidad,
                precio_unitario,
                descuento_pct,
                estado_pedido,
                fecha_despacho,
                total_venta,
                segmento_precio
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        registros = preparar_registros(df_validos)

        cursor.executemany(
            sentencia_insert,
            registros
        )

        conexion.commit()

        # Si la transacción termina bien, crear CSV vacío de rechazados BD.
        pd.DataFrame(
            columns=list(df_validos.columns) + ["error_bd"]
        ).to_csv(
            RUTA_RECHAZADOS,
            index=False,
            encoding="utf-8-sig"
        )

        ventas_region = pd.read_sql_query(
            consulta_region,
            conexion
        )

        ventas_categoria = pd.read_sql_query(
            consulta_categoria,
            conexion
        )

        ventas_region.to_csv(
            RUTA_REGION,
            index=False,
            encoding="utf-8-sig"
        )

        ventas_categoria.to_csv(
            RUTA_CATEGORIA,
            index=False,
            encoding="utf-8-sig"
        )

        print("\n" + "=" * 60)
        print("ETAPA 4: CARGA A BASE DE DATOS")
        print("=" * 60)
        print(f"Base de datos: {RUTA_BD}")
        print(f"Registros cargados: {len(df_validos)}")
        print("Transacción confirmada mediante COMMIT.")

        print("\nVentas por región:")
        for fila in ventas_region.itertuples(index=False):
            print(
                f"- {fila.region}: "
                f"${fila.ventas_totales:,.2f} CLP"
            )

        print("\nVentas por categoría:")
        for fila in ventas_categoria.itertuples(index=False):
            print(
                f"- {fila.categoria}: "
                f"${fila.ventas_totales:,.2f} CLP"
            )

        logger.info("Inicio de carga a base de datos")
        logger.info("Fecha: %s", datetime.now())
        logger.info("Base de datos: %s", RUTA_BD)
        logger.info("Registros cargados: %d", len(df_validos))
        logger.info("COMMIT ejecutado correctamente")
        logger.info(
            "Ventas por región:\n%s",
            ventas_region.to_string(index=False)
        )
        logger.info(
            "Ventas por categoría:\n%s",
            ventas_categoria.to_string(index=False)
        )
        logger.info("Etapa de carga finalizada correctamente")

        return ventas_region, ventas_categoria

    except Exception as error:
        conexion.rollback()

        rechazados = df_validos.copy()
        rechazados["error_bd"] = str(error)

        rechazados.to_csv(
            RUTA_RECHAZADOS,
            index=False,
            encoding="utf-8-sig"
        )

        logger.exception(
            "Error durante la carga. Se aplicó ROLLBACK: %s",
            error
        )

        raise RuntimeError(
            f"Falló la carga a SQLite. Se aplicó ROLLBACK: {error}"
        ) from error

    finally:
        conexion.close()