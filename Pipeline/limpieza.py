"""
Módulo de Depuración, Normalización y Enriquecimiento
Transformación de datos crudos hacia el almacenamiento limpio.
"""

import logging
from pathlib import Path
import pandas as pd

DIRECTORIO_RAIZ = Path(__file__).resolve().parent
FMT_RAW = DIRECTORIO_RAIZ / "data" / "raw"
FMT_CLEAN = DIRECTORIO_RAIZ / "data" / "clean"
RUTA_LOGS = DIRECTORIO_RAIZ / "logs"

RUTA_LOGS.mkdir(parents=True, exist_ok=True)
FMT_CLEAN.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=RUTA_LOGS / "limpieza.log",
    level=logging.INFO,
    format="%(asctime)s [L] %(levelname)s: %(message)s",
)

# Diccionarios de homologación semántica
DICC_COMUNAS = {
    "Maipu": "Maipú",
    "Nunoa": "Ñuñoa",
    "Penalolen": "Peñalolén",
    "Estacion Central": "Estación Central",
    "Santiago Centro": "Santiago",
}
DICC_MODOS_PAGO = {"débito": "debito", "crédito": "credito"}

def homogeneizar_fechas(columna):
    """Convierte múltiples variantes de fechas string al formato estándar ISO AAAA-MM-DD."""
    vector_fechas = pd.to_datetime(columna, format="%Y-%m-%d", errors="coerce")
    for mascara in ["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
        vector_fechas = vector_fechas.fillna(pd.to_datetime(columna, format=mascara, errors="coerce"))
    return vector_fechas.dt.strftime("%Y-%m-%d")

def procesar_clientes(df_crudo):
    """Depuración y cálculo de métricas derivadas para la entidad Clientes."""
    print(f"\n--- PROCESANDO ENTIDAD: CLIENTES ---")
    conteo_original = len(df_crudo)

    # Quitar duplicados por clave primaria
    df_trabajo = df_crudo.drop_duplicates(subset=["id_cliente"], keep="first")
    removidos_dup = conteo_original - len(df_trabajo)

    # Validar campos de obligatoriedad estructural
    antes_nulos = len(df_trabajo)
    df_trabajo = df_trabajo.dropna(subset=["id_cliente", "nombre", "rut"])
    removidos_nul = antes_nulos - len(df_trabajo)

    # Imputación controlada de valores ausentes
    df_trabajo["edad"] = df_trabajo["edad"].fillna(df_trabajo["edad"].median())
    df_trabajo["comuna"] = df_trabajo["comuna"].fillna("Desconocida")

    # Limpieza de strings y formateo estandarizado
    for c in ["nombre", "email", "telefono", "comuna", "rut"]:
        df_trabajo[c] = df_trabajo[c].str.strip().str.replace(r'\s+', ' ', regex=True)

    df_trabajo["nombre"] = df_trabajo["nombre"].str.title()
    df_trabajo["email"] = df_trabajo["email"].str.lower()
    df_trabajo["comuna"] = df_trabajo["comuna"].str.title().replace(DICC_COMUNAS)
    df_trabajo["rut"] = df_trabajo["rut"].str.upper()
    df_trabajo["fecha_registro"] = homogeneizar_fechas(df_trabajo["fecha_registro"])

    # Transformación 1: Segmentación etaria
    df_trabajo["rango_etario"] = pd.cut(df_trabajo["edad"], bins=[0, 30, 50, 200], labels=["18-30", "31-50", "51+"])

    print(f" > Registros Base: {conteo_original} | Duplicados: {removidos_dup} | Nulos Críticos: {removidos_nul} | Final: {len(df_trabajo)}")
    logging.info("Limpieza Clientes finalizada. Original: %d -> Depurado: %d", conteo_original, len(df_trabajo))
    return df_trabajo

def procesar_productos(df_crudo):
    """Ajuste de textos y remoción de registros rotos en el catálogo de Productos."""
    print(f"\n--- PROCESANDO ENTIDAD: PRODUCTOS ---")
    conteo_original = len(df_crudo)

    df_trabajo = df_crudo.drop_duplicates(subset=["id_producto"], keep="first")
    removidos_dup = conteo_original - len(df_trabajo)

    antes_nulos = len(df_trabajo)
    df_trabajo = df_trabajo.dropna(subset=["id_producto", "nombre_producto", "precio_unitario_clp", "stock"])
    removidos_nul = antes_nulos - len(df_trabajo)

    df_trabajo["nombre_producto"] = df_trabajo["nombre_producto"].str.strip()
    df_trabajo["categoria"] = df_trabajo["categoria"].str.strip().str.title()

    print(f" > Registros Base: {conteo_original} | Duplicados: {removidos_dup} | Nulos Críticos: {removidos_nul} | Final: {len(df_trabajo)}")
    logging.info("Limpieza Productos finalizada. Original: %d -> Depurado: %d", conteo_original, len(df_trabajo))
    return df_trabajo

def procesar_pedidos(df_crudo, df_productos_limpios):
    """Depura Pedidos y efectúa ingeniería de variables (Monto calculado, Escalamiento, One-Hot)."""
    print(f"\n--- PROCESANDO ENTIDAD: PEDIDOS ---")
    conteo_original = len(df_crudo)

    df_trabajo = df_crudo.drop_duplicates(subset=["id_pedido"], keep="first")
    removidos_dup = conteo_original - len(df_trabajo)

    antes_nulos = len(df_trabajo)
    df_trabajo = df_trabajo.dropna(subset=["id_pedido", "id_cliente", "id_producto"])
    removidos_nul = antes_nulos - len(df_trabajo)

    df_trabajo["estado"] = df_trabajo["estado"].str.strip().str.lower().str.replace(" ", "_")
    df_trabajo["metodo_pago"] = df_trabajo["metodo_pago"].str.strip().str.lower().replace(DICC_MODOS_PAGO)
    df_trabajo["fecha_pedido"] = homogeneizar_fechas(df_trabajo["fecha_pedido"])
    df_trabajo["fecha_despacho"] = homogeneizar_fechas(df_trabajo["fecha_despacho"])

    # Re-cálculo inteligente de montos nulos basándose en el catálogo maestro
    nulos_en_monto = int(df_trabajo["monto_total_clp"].isna().sum())
    df_unificado = df_trabajo.merge(df_productos_limpios[["id_producto", "precio_unitario_clp"]], on="id_producto", how="left")
    valores_cantidad = pd.to_numeric(df_unificado["cantidad"], errors="coerce")
    
    df_trabajo["monto_total_clp"] = df_trabajo["monto_total_clp"].fillna(
        df_unificado["precio_unitario_clp"] * valores_cantidad
    )

    # Transformación 2: Ventana temporal de entrega
    df_trabajo["dias_despacho"] = (pd.to_datetime(df_trabajo["fecha_despacho"]) - pd.to_datetime(df_trabajo["fecha_pedido"])).dt.days

    # Transformación 3: Normalización Min-Max de transacciones
    minimo_monto = df_trabajo["monto_total_clp"].min()
    maximo_monto = df_trabajo["monto_total_clp"].max()
    df_trabajo["monto_normalizado"] = ((df_trabajo["monto_total_clp"] - minimo_monto) / (maximo_monto - minimo_monto)).round(4)

    # Transformación 4: Codificación One-Hot de la variable categórica pago
    matriz_one_hot = pd.get_dummies(df_trabajo["metodo_pago"], prefix="pago", dtype=int)
    df_trabajo = pd.concat([df_trabajo, matriz_one_hot], axis=1)

    print(f" > Registros Base: {conteo_original} | Duplicados: {removidos_dup} | Montos Re-calculados: {nulos_en_monto} | Final: {len(df_trabajo)}")
    logging.info("Limpieza Pedidos finalizada. Original: %d -> Depurado: %d", conteo_original, len(df_trabajo))
    return df_trabajo

def ejecutar_transformaciones():
    """Coordina secuencialmente la limpieza de las colecciones cargadas."""
    logging.info("Ejecutando la Etapa 2 del Pipeline")
    
    try:
        ds_productos = procesar_productos(pd.read_csv(FMT_RAW / "productos.csv"))
        ds_clientes = procesar_clientes(pd.read_csv(FMT_RAW / "clientes.csv"))
        ds_pedidos = procesar_pedidos(pd.read_csv(FMT_RAW / "pedidos.csv"), ds_productos)

        diccionario_salida = {"productos": ds_productos, "clientes": ds_clientes, "pedidos": ds_pedidos}

        for clave, dataframe in diccionario_salida.items():
            dataframe.to_csv(FMT_CLEAN / f"{clave}.csv", index=False, encoding="utf-8")

        print(f"\n[OK] Datos depurados y almacenados en el directorio: {FMT_CLEAN}")
        return diccionario_salida

    except FileNotFoundError as err:
        logging.error("Fallo de E/S al leer archivos base: %s", err)
        raise
    except Exception as e:
        logging.error("Excepción general en fase de limpieza: %s", e)
        raise

if __name__ == "__main__":
    ejecutar_transformaciones()