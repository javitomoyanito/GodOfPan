import pandas as pd
import os
from datetime import datetime

import pandas as pd

def limpiar_fecha(fecha):
    if pd.isna(fecha):
        return pd.NaT

    formatos = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y"
    ]

    for formato in formatos:
        try:
            return pd.to_datetime(fecha, format=formato)
        except:
            pass

    return pd.NaT

def ejecutar_limpieza(df):
    os.makedirs("data/clean", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    registros_iniciales = len(df)
    
    duplicados = df.duplicated(subset="id_pedido").sum()

    df = df.drop_duplicates(subset="id_pedido")

    print(f"Duplicados eliminados: {duplicados}")

    df["fecha_pedido"] = df["fecha_pedido"].apply(limpiar_fecha)
    df["fecha_despacho"] = df["fecha_despacho"].apply(limpiar_fecha)

    df["fecha_pedido"] = df["fecha_pedido"].dt.strftime("%Y-%m-%d")
    df["fecha_despacho"] = df["fecha_despacho"].dt.strftime("%Y-%m-%d")

    df["precio_unitario"] = (
        df["precio_unitario"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    df["precio_unitario"] = pd.to_numeric(df["precio_unitario"], errors="coerce")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")
    df["descuento_pct"] = pd.to_numeric(df["descuento_pct"], errors="coerce")

    df["categoria"] = (
        df["categoria"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    mapa_categorias = {
        "tech": "Tecnologia",
        "technology": "Tecnologia",
        "tecnología": "Tecnologia",
        "tecnologia": "Tecnologia",
        "hogar": "Hogar",
        "moda": "Moda"
    }

    df["categoria"] = df["categoria"].replace(mapa_categorias)

    df["producto"] = df["producto"].astype(str).str.strip()
    df["nombre_cliente"] = df["nombre_cliente"].astype(str).str.title()
    df["estado_pedido"] = df["estado_pedido"].astype(str).str.lower().str.strip()
    df["region"] = df["region"].astype(str).str.title().str.strip()

    df["total_venta"] = df["cantidad"] * df["precio_unitario"] * (1 - df["descuento_pct"] / 100)

    def segmento(precio):
        if pd.isna(precio):
            return "desconocido"
        elif precio < 10000:
            return "bajo"
        elif precio < 50000:
            return "medio"
        else:
            return "alto"

    df["segmento_precio"] = df["precio_unitario"].apply(segmento)

    df.to_csv("data/clean/ventas_clean.csv", index=False)

    with open("logs/limpieza.log", "w", encoding="utf-8") as log:
        log.write("ETAPA 2: LIMPIEZA Y TRANSFORMACIÓN\n")
        log.write(f"Fecha: {datetime.now()}\n")
        log.write(f"Registros iniciales: {registros_iniciales}\n")
        log.write(f"Registros después de eliminar duplicados: {len(df)}\n")
        log.write("Columnas creadas: total_venta, segmento_precio\n")

    return df