from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd


RUTA_ENTRADA = Path("data/input/ventas_datamart.csv")
RUTA_RAW = Path("data/raw/ventas_raw.csv")
RUTA_LOG = Path("logs/ingesta.log")


def configurar_logger() -> logging.Logger:
    """Configura el archivo de log correspondiente a la ingesta."""
    RUTA_LOG.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ingesta")
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


def ejecutar_ingesta() -> pd.DataFrame:
    """Carga el archivo original y conserva una copia sin modificaciones."""
    logger = configurar_logger()

    if not RUTA_ENTRADA.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {RUTA_ENTRADA.resolve()}"
        )

    RUTA_RAW.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(
        RUTA_ENTRADA,
        encoding="utf-8"
    )

    # Guardar copia exacta antes de transformar los datos.
    df.to_csv(
        RUTA_RAW,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 60)
    print("ETAPA 1: INGESTA")
    print("=" * 60)

    print(f"Archivo leído: {RUTA_ENTRADA}")
    print(f"Shape: {df.shape}")

    print("\nTipos de datos:")
    print(df.dtypes)

    print("\nNulos por columna:")
    print(df.isna().sum())

    print("\nInformación general:")
    df.info()

    logger.info("Inicio de la etapa de ingesta")
    logger.info("Archivo cargado: %s", RUTA_ENTRADA.name)
    logger.info("Fecha de carga: %s", datetime.now())
    logger.info("Registros iniciales: %d", len(df))
    logger.info("Cantidad de columnas: %d", len(df.columns))
    logger.info("Shape: %s", df.shape)
    logger.info("Archivo RAW guardado en: %s", RUTA_RAW)
    logger.info(
        "Nulos por columna:\n%s",
        df.isna().sum().to_string()
    )
    logger.info("Etapa de ingesta finalizada correctamente")

    return df