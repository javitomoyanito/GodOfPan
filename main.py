from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from carga import ejecutar_carga
from ingesta import ejecutar_ingesta
from limpieza import ejecutar_limpieza
from validacion import ejecutar_validacion


RUTA_RESUMEN = Path("data/reports/resumen_pipeline.csv")


def crear_carpetas() -> None:
    """Crea todas las carpetas requeridas por el pipeline."""
    carpetas = [
        Path("data/input"),
        Path("data/raw"),
        Path("data/clean"),
        Path("data/validated"),
        Path("data/errors"),
        Path("data/reports"),
        Path("database"),
        Path("logs")
    ]

    for carpeta in carpetas:
        carpeta.mkdir(parents=True, exist_ok=True)


def guardar_resumen(
    registros_originales: int,
    registros_limpios: int,
    registros_validos: int,
    registros_invalidos: int
) -> None:
    resumen = pd.DataFrame(
        {
            "metrica": [
                "Registros originales",
                "Registros después de limpieza",
                "Registros válidos",
                "Registros inválidos"
            ],
            "cantidad": [
                registros_originales,
                registros_limpios,
                registros_validos,
                registros_invalidos
            ]
        }
    )

    resumen.to_csv(
        RUTA_RESUMEN,
        index=False,
        encoding="utf-8-sig"
    )


def main() -> None:
    crear_carpetas()

    print("\n" + "=" * 60)
    print("PIPELINE DE DATOS — DATAMART CHILE S.A.")
    print("=" * 60)

    try:
        # Etapa 1: Ingesta.
        df_original = ejecutar_ingesta()

        # Etapa 2: Limpieza.
        df_limpio = ejecutar_limpieza(df_original)

        # Etapa 3: Validación.
        df_validos, df_invalidos = ejecutar_validacion(df_limpio)

        # Etapa 4: Carga.
        ejecutar_carga(df_validos)

        guardar_resumen(
            registros_originales=len(df_original),
            registros_limpios=len(df_limpio),
            registros_validos=len(df_validos),
            registros_invalidos=len(df_invalidos)
        )

        print("\n" + "=" * 60)
        print("RESUMEN FINAL")
        print("=" * 60)
        print(f"Registros originales: {len(df_original)}")
        print(f"Registros después de limpieza: {len(df_limpio)}")
        print(f"Registros válidos: {len(df_validos)}")
        print(f"Registros inválidos: {len(df_invalidos)}")
        print(f"Base de datos: database/datamart.db")
        print(f"Resumen: {RUTA_RESUMEN}")

        print("\n" + "=" * 60)
        print("PIPELINE FINALIZADO CORRECTAMENTE")
        print("=" * 60)

    except FileNotFoundError as error:
        print("\nERROR DE ARCHIVO")
        print(error)
        sys.exit(1)

    except Exception as error:
        print("\nERROR DURANTE LA EJECUCIÓN DEL PIPELINE")
        print(error)
        sys.exit(1)


if __name__ == "__main__":
    main()