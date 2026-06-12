"""
Módulo de Ingesta Inicial - Data Pipeline
Captura y auditoría de fuentes de datos en bruto (CSV).
"""

import logging
from pathlib import Path
import pandas as pd

# Configuración de rutas del entorno
DIRECTORIO_RAIZ = Path(__file__).resolve().parent
ORIGEN_RAW = DIRECTORIO_RAIZ / "data" / "raw"
CARPETA_LOGS = DIRECTORIO_RAIZ / "logs"
CARPETA_LOGS.mkdir(parents=True, exist_ok=True)

# Registro de operaciones dedicado para ingesta
logging.basicConfig(
    filename=CARPETA_LOGS / "ingesta.log",
    level=logging.INFO,
    format="%(asctime)s [I] %(levelname)s: %(message)s",
)

COMPONENTES_DATASET = ["productos", "clientes", "pedidos"]

def auditoria_fuente(identificador: str) -> pd.DataFrame:
    """Carga el archivo CSV correspondiente y genera un diagnóstico inicial en consola."""
    ubicacion_archivo = ORIGEN_RAW / f"{identificador}.csv"
    dataset = pd.read_csv(ubicacion_archivo)

    print(f"\n>>> DIAGNÓSTICO DE COMPONENTE: {identificador.upper()} <<<\n" + "-"*50)
    print(f"Dimensiones de matriz: {dataset.shape[0]} registros x {dataset.shape[1]} columnas")
    print(f"\nEstructura de tipos (dtypes):\n{dataset.dtypes}")
    print(f"\nMuestra de cabecera:\n{dataset.head(3).to_string()}")
    print(f"\nRecuento de valores nulos:\n{dataset.isna().sum()}")
    print(f"Registros idénticos duplicados: {dataset.duplicated().sum()}")
    print("-"*50)

    logging.info(
        "Lectura exitosa -> origen: %s | registros: %d | dimensiones: %d | total_nulos: %d",
        identificador, len(dataset), dataset.shape[1], int(dataset.isna().sum().sum())
    )
    return dataset

def iniciar_ingesta() -> dict[str, pd.DataFrame]:
    """Punto de entrada para la recolección y lectura de los datos crudos."""
    logging.info("Iniciando proceso general de Ingesta (Etapa 1)")
    mapa_datasets = {}
    
    for componente in COMPONENTES_DATASET:
        try:
            mapa_datasets[componente] = auditoria_fuente(componente)
        except FileNotFoundError:
            logging.error("Falta crítico de archivo: %s.csv no localizado en %s", componente, ORIGEN_RAW)
            raise

    volumen_total = sum(len(df) for df in mapa_datasets.values())
    logging.info("Fase 1 finalizada | Componentes: %d | Suma registros: %d", len(mapa_datasets), volumen_total)
    
    print(f"\n[OK] Fase de ingesta finalizada con éxito. Tablas: {len(mapa_datasets)}. Registros procesados: {volumen_total}.")
    return mapa_datasets

if __name__ == "__main__":
    iniciar_ingesta()