from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd


RUTA_VALIDOS = Path("data/validated/ventas_validas.csv")
RUTA_INVALIDOS = Path("data/errors/ventas_invalidas.csv")
RUTA_LOG = Path("logs/validacion.log")

ESTADOS_PERMITIDOS = {
    "pendiente",
    "despachado",
    "entregado",
    "cancelado"
}

CATEGORIAS_PERMITIDAS = {
    "Tecnologia",
    "Hogar",
    "Moda"
}


def configurar_logger() -> logging.Logger:
    RUTA_LOG.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("validacion")
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


def validar_registro(fila: pd.Series) -> list[str]:
    """Retorna una lista con todos los errores de una fila."""
    errores: list[str] = []

    # Validaciones estructurales.
    if pd.isna(fila["id_pedido"]):
        errores.append("id_pedido nulo o no numérico")

    if pd.isna(fila["fecha_pedido"]):
        errores.append("fecha_pedido inválida")

    if pd.isna(fila["cantidad"]) or fila["cantidad"] <= 0:
        errores.append("cantidad debe ser mayor que cero")

    if pd.isna(fila["precio_unitario"]) or fila["precio_unitario"] <= 0:
        errores.append("precio_unitario debe ser mayor que cero")

    if (
        pd.isna(fila["descuento_pct"])
        or fila["descuento_pct"] < 0
        or fila["descuento_pct"] > 100
    ):
        errores.append("descuento_pct debe estar entre 0 y 100")

    if pd.isna(fila["categoria"]) or fila["categoria"] not in CATEGORIAS_PERMITIDAS:
        errores.append("categoria fuera del dominio permitido")

    if (
        pd.isna(fila["estado_pedido"])
        or fila["estado_pedido"] not in ESTADOS_PERMITIDOS
    ):
        errores.append("estado_pedido fuera del dominio permitido")

    # Validaciones semánticas o reglas de negocio.
    if pd.isna(fila["region"]) or str(fila["region"]).strip() == "":
        errores.append("region obligatoria")

    if (
        fila["estado_pedido"] == "entregado"
        and pd.isna(fila["fecha_despacho"])
    ):
        errores.append("pedido entregado sin fecha de despacho")

    if (
        fila["estado_pedido"] == "despachado"
        and pd.isna(fila["fecha_despacho"])
    ):
        errores.append("pedido despachado sin fecha de despacho")

    if (
        fila["estado_pedido"] == "pendiente"
        and not pd.isna(fila["fecha_despacho"])
    ):
        errores.append("pedido pendiente no debería tener fecha de despacho")

    return errores


def ejecutar_validacion(
    df_limpio: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa registros válidos e inválidos."""
    logger = configurar_logger()

    RUTA_VALIDOS.parent.mkdir(parents=True, exist_ok=True)
    RUTA_INVALIDOS.parent.mkdir(parents=True, exist_ok=True)

    df = df_limpio.copy()

    df["lista_errores"] = df.apply(
        validar_registro,
        axis=1
    )

    df["es_valido"] = df["lista_errores"].apply(
        lambda errores: len(errores) == 0
    )

    df["motivos_error"] = df["lista_errores"].apply(
        lambda errores: " | ".join(errores)
    )

    validos = df[df["es_valido"]].copy()
    invalidos = df[~df["es_valido"]].copy()

    # Remover columnas auxiliares de los válidos.
    validos = validos.drop(
        columns=["lista_errores", "es_valido", "motivos_error"]
    )

    # En inválidos se conserva motivos_error para trazabilidad.
    invalidos = invalidos.drop(
        columns=["lista_errores", "es_valido"]
    )

    validos.to_csv(
        RUTA_VALIDOS,
        index=False,
        encoding="utf-8-sig"
    )

    invalidos.to_csv(
        RUTA_INVALIDOS,
        index=False,
        encoding="utf-8-sig"
    )

    contador_errores: Counter[str] = Counter()

    for lista in df.loc[~df["es_valido"], "lista_errores"]:
        contador_errores.update(lista)

    print("\n" + "=" * 60)
    print("ETAPA 3: VALIDACIÓN")
    print("=" * 60)
    print(f"Registros evaluados: {len(df)}")
    print(f"Registros válidos: {len(validos)}")
    print(f"Registros inválidos: {len(invalidos)}")

    print("\nErrores detectados por tipo:")

    if contador_errores:
        for error, cantidad in contador_errores.most_common():
            print(f"- {error}: {cantidad}")
    else:
        print("- No se detectaron errores.")

    logger.info("Inicio de la etapa de validación")
    logger.info("Fecha: %s", datetime.now())
    logger.info("Registros evaluados: %d", len(df))
    logger.info("Registros válidos: %d", len(validos))
    logger.info("Registros inválidos: %d", len(invalidos))

    for error, cantidad in contador_errores.most_common():
        logger.info("%s: %d", error, cantidad)

    logger.info("Válidos guardados en: %s", RUTA_VALIDOS)
    logger.info("Inválidos guardados en: %s", RUTA_INVALIDOS)
    logger.info("Etapa de validación finalizada correctamente")

    return validos, invalidos