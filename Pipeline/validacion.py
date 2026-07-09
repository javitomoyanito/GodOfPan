import pandas as pd
import os
from datetime import datetime

def ejecutar_validacion(df):
    os.makedirs("data/validated", exist_ok=True)
    os.makedirs("data/errors", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    errores = pd.DataFrame()

    condicion_invalida = (
        (df["cantidad"] <= 0) |
        (df["precio_unitario"] <= 0) |
        (df["descuento_pct"] < 0) |
        (df["descuento_pct"] > 100) |
        (df["region"].isna()) |
        (df["region"] == "") |
        ((df["estado_pedido"] == "entregado") & (df["fecha_despacho"].isna()))
    )

    validos = df[~condicion_invalida].copy()
    invalidos = df[condicion_invalida].copy()

    validos.to_csv("data/validated/ventas_validas.csv", index=False)
    invalidos.to_csv("data/errors/ventas_invalidas.csv", index=False)

    with open("logs/validacion.log", "w", encoding="utf-8") as log:
        log.write("ETAPA 3: VALIDACIÓN\n")
        log.write(f"Fecha: {datetime.now()}\n")
        log.write(f"Registros válidos: {len(validos)}\n")
        log.write(f"Registros inválidos: {len(invalidos)}\n")
        log.write(f"Cantidad <= 0: {(df['cantidad'] <= 0).sum()}\n")
        log.write(f"Precio <= 0: {(df['precio_unitario'] <= 0).sum()}\n")
        log.write(f"Descuento fuera de rango: {((df['descuento_pct'] < 0) | (df['descuento_pct'] > 100)).sum()}\n")
        log.write(f"Entregado sin despacho: {((df['estado_pedido'] == 'entregado') & (df['fecha_despacho'].isna())).sum()}\n")

    return validos, invalidos