import pandas as pd
from datetime import datetime
import os

def ejecutar_ingesta():
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    df = pd.read_csv("data/ventas_datamart.csv")

    print("Shape:", df.shape)
    print("\nTipos de datos:")
    print(df.dtypes)
    print("\nNulos por columna:")
    print(df.isnull().sum())
    print("\nInformación general:")
    print(df.info())

    df.to_csv("data/raw/ventas_raw.csv", index=False)

    with open("logs/ingesta.log", "w", encoding="utf-8") as log:
        log.write("ETAPA 1: INGESTA\n")
        log.write(f"Fecha de carga: {datetime.now()}\n")
        log.write(f"Archivo cargado: ventas_datamart.csv\n")
        log.write(f"Registros: {df.shape[0]}\n")
        log.write(f"Columnas: {df.shape[1]}\n")
        log.write(f"Nulos por columna:\n{df.isnull().sum()}\n")

    return df