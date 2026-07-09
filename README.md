## Integrantes

Martin Torres
Alvaro Prieto
Javier Moyano

## Descripción

Este proyecto implementa un pipeline ETL para un DataMart de ventas.

El proceso incluye:

- Ingesta
- Limpieza
- Validación
- Carga
- Consultas SQL

## Librerías

- pandas
- sqlite3

## Estructura

main.py
ingesta.py
limpieza.py
validacion.py
carga.py

## Ejecución

python main.py

## Resultados

Se procesaron 316 registros.

Se eliminaron 15 duplicados.

Los registros válidos fueron cargados en SQLite.

Se generaron logs y archivos CSV.