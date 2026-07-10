from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd


RUTA_CLEAN = Path("data/clean/ventas_clean.csv")
RUTA_LOG = Path("logs/limpieza.log")


def configurar_logger() -> logging.Logger:
    RUTA_LOG.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("limpieza")
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


def quitar_tildes(valor: object) -> object:
    """Elimina tildes sin modificar valores nulos."""
    if pd.isna(valor):
        return pd.NA

    texto = str(valor).strip()

    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )


def normalizar_fecha(valor: object) -> str | pd._libs.missing.NAType:
    """
    Convierte fechas conocidas al formato ISO YYYY-MM-DD.

    El archivo contiene fechas como:
    - 2024-12-17
    - 15-02-2024
    - 10/05/2024
    """
    if pd.isna(valor) or str(valor).strip() == "":
        return pd.NA

    texto = str(valor).strip()

    formatos = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d"
    )

    for formato in formatos:
        fecha = pd.to_datetime(
            texto,
            format=formato,
            errors="coerce"
        )

        if not pd.isna(fecha):
            return fecha.strftime("%Y-%m-%d")

    # Si no coincide con los formatos definidos, se marca como nulo.
    return pd.NA


def limpiar_precio(valor: object) -> float:
    """
    Convierte precios como:
    $149990, $39.990, 49990
    a valores numéricos.
    """
    if pd.isna(valor):
        return float("nan")

    texto = str(valor).strip()

    # Mantener solo números, signo negativo, punto y coma.
    texto = re.sub(r"[^\d,.\-]", "", texto)

    # En este dataset, los puntos son separadores de miles.
    # Ejemplo: 39.990 -> 39990
    if "." in texto and "," not in texto:
        partes = texto.split(".")

        if all(len(parte) == 3 for parte in partes[1:]):
            texto = texto.replace(".", "")

    # Si existe coma decimal, convertirla a punto.
    texto = texto.replace(",", ".")

    return pd.to_numeric(texto, errors="coerce")


def normalizar_rut(valor: object) -> object:
    """
    Elimina puntos y conserva el guion del RUT cuando existe.

    Ejemplo:
    16.595.258-9 -> 16595258-9
    """
    if pd.isna(valor):
        return pd.NA

    rut = str(valor).strip().upper()
    rut = rut.replace(".", "").replace(" ", "")

    return rut if rut else pd.NA


def normalizar_categoria(valor: object) -> object:
    if pd.isna(valor):
        return pd.NA

    categoria = str(quitar_tildes(valor)).strip().lower()

    mapa = {
        "tech": "Tecnologia",
        "tecnologia": "Tecnologia",
        "technology": "Tecnologia",
        "hogar": "Hogar",
        "moda": "Moda"
    }

    return mapa.get(categoria, categoria.title())


def normalizar_region(valor: object) -> object:
    if pd.isna(valor) or str(valor).strip() == "":
        return pd.NA

    region = str(quitar_tildes(valor)).strip().lower()

    mapa = {
        "metropolitana": "Metropolitana",
        "valparaiso": "Valparaiso",
        "biobio": "Biobio",
        "bio bio": "Biobio",
        "maule": "Maule",
        "araucania": "Araucania",
        "coquimbo": "Coquimbo",
        "ohiggins": "OHiggins",
        "o'higgins": "OHiggins",
        "o higgins": "OHiggins"
    }

    return mapa.get(region, region.title())


def asignar_segmento(precio: object) -> object:
    if pd.isna(precio):
        return pd.NA

    precio = float(precio)

    if precio < 10_000:
        return "Bajo"

    if precio < 50_000:
        return "Medio"

    return "Alto"


def ejecutar_limpieza(df_original: pd.DataFrame) -> pd.DataFrame:
    """Limpia y transforma el dataset sin ocultar errores de negocio."""
    logger = configurar_logger()

    RUTA_CLEAN.parent.mkdir(parents=True, exist_ok=True)

    df = df_original.copy()

    registros_iniciales = len(df)
    filas_vacias = int(df.isna().all(axis=1).sum())

    # Eliminar filas completamente vacías.
    df = df.dropna(how="all").copy()

    registros_antes_duplicados = len(df)

    # El ID del pedido debe representar un pedido único.
    df = df.drop_duplicates(
        subset=["id_pedido"],
        keep="first"
    ).copy()

    duplicados_eliminados = registros_antes_duplicados - len(df)

    # Conversión de tipos numéricos.
    df["id_pedido"] = pd.to_numeric(
        df["id_pedido"],
        errors="coerce"
    ).astype("Int64")

    df["cantidad"] = pd.to_numeric(
        df["cantidad"],
        errors="coerce"
    )

    df["descuento_pct"] = pd.to_numeric(
        df["descuento_pct"],
        errors="coerce"
    )

    df["precio_unitario"] = df["precio_unitario"].apply(
        limpiar_precio
    )

    # Normalización de fechas.
    df["fecha_pedido"] = df["fecha_pedido"].apply(
        normalizar_fecha
    )

    df["fecha_despacho"] = df["fecha_despacho"].apply(
        normalizar_fecha
    )

    # Estandarización de texto.
    df["rut_cliente"] = df["rut_cliente"].apply(
        normalizar_rut
    )

    df["nombre_cliente"] = (
        df["nombre_cliente"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    df["producto"] = (
        df["producto"]
        .astype("string")
        .str.strip()
    )

    df["categoria"] = df["categoria"].apply(
        normalizar_categoria
    )

    df["region"] = df["region"].apply(
        normalizar_region
    )

    df["estado_pedido"] = (
        df["estado_pedido"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    # Columnas derivadas solicitadas.
    df["total_venta"] = (
        df["cantidad"]
        * df["precio_unitario"]
        * (1 - df["descuento_pct"] / 100)
    ).round(2)

    df["segmento_precio"] = df["precio_unitario"].apply(
        asignar_segmento
    )

    df.to_csv(
        RUTA_CLEAN,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 60)
    print("ETAPA 2: LIMPIEZA Y TRANSFORMACIÓN")
    print("=" * 60)
    print(f"Registros iniciales: {registros_iniciales}")
    print(f"Filas completamente vacías eliminadas: {filas_vacias}")
    print(f"Duplicados eliminados por id_pedido: {duplicados_eliminados}")
    print(f"Registros después de limpieza: {len(df)}")
    print("Columnas creadas: total_venta y segmento_precio")

    logger.info("Inicio de limpieza y transformación")
    logger.info("Fecha: %s", datetime.now())
    logger.info("Registros iniciales: %d", registros_iniciales)
    logger.info("Filas vacías eliminadas: %d", filas_vacias)
    logger.info(
        "Duplicados eliminados por id_pedido: %d",
        duplicados_eliminados
    )
    logger.info("Registros finales de limpieza: %d", len(df))
    logger.info(
        "Columnas derivadas creadas: total_venta, segmento_precio"
    )
    logger.info("Archivo limpio guardado en: %s", RUTA_CLEAN)
    logger.info("Etapa de limpieza finalizada correctamente")

    return df