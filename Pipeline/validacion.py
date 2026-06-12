"""
Módulo de Verificación Estructural y Semántica (Calidad de Datos)
Filtra registros aptos e inválidos aplicando reglas de negocio estrictas.
"""

import logging
import re
from pathlib import Path
import pandas as pd
import pandera.pandas as pa
from pandera import Check, Column

DIRECTORIO_RAIZ = Path(__file__).resolve().parent
CONTEXTO_CLEAN = DIRECTORIO_RAIZ / "data" / "clean"
CONTEXTO_VALIDO = DIRECTORIO_RAIZ / "data" / "validated"
CONTEXTO_ERROR = DIRECTORIO_RAIZ / "data" / "errors"
CARPETA_LOGS = DIRECTORIO_RAIZ / "logs"

for path_dir in [CONTEXTO_VALIDO, CONTEXTO_ERROR, CARPETA_LOGS]:
    path_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=CARPETA_LOGS / "validacion.log",
    level=logging.INFO,
    format="%(asctime)s [V] %(levelname)s: %(message)s",
)

# Catálogo centralizado de infracciones de negocio
REGLAS_FALLIDAS = {
    "edad": "Infracción: Edad fuera del rango permitido (18 a 110 años)",
    "rut": "Infracción: Formato o dígito verificador RUT chileno no válido",
    "email": "Infracción: Estructura de correo electrónico incorrecta",
    "telefono": "Infracción: Teléfono móvil fuera del patrón (+569XXXXXXXX)",
    "cantidad": "Infracción: Volumen menor que uno o tipo de dato erróneo",
    "monto_total_clp": "Infracción: Valor monetario menor o igual a cero",
    "precio_unitario_clp": "Infracción: Precio de lista no positivo",
    "stock": "Infracción: Existencia de almacén en negativo",
}

def validador_identidad_cl(rut_str):
    """Algoritmo de validación de RUT mediante módulo 11 chileno."""
    string_limpio = str(rut_str).strip()
    if not re.match(r"^\d{7,8}-[\dkK]$", string_limpio):
        return False
    
    bloque_numerico, digito_control = string_limpio.split("-")
    acumulado, multiplicador = 0, 2
    
    for caracter in reversed(bloque_numerico):
        acumulado += int(caracter) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
        
    resultado_modulo = 11 - (acumulado % 11)
    dv_esperado = "0" if resultado_modulo == 11 else "K" if resultado_modulo == 10 else str(resultado_modulo)
    return dv_esperado == digito_control.upper()

# Modelos de control de Pandera (Validaciones Estructurales)
MODELO_CLIENTES = pa.DataFrameSchema({
    "edad": Column(float, Check.in_range(18, 110), coerce=True),
    "rut": Column(str, Check(lambda serie: serie.map(validador_identidad_cl), element_wise=False)),
    "email": Column(str, Check.str_matches(r"^[\w\.\-]+@[\w\-]+\.\w{2,}$"), nullable=True),
    "telefono": Column(str, Check.str_matches(r"^\+569\d{8}$"), nullable=True),
})

MODELO_PEDIDOS = pa.DataFrameSchema({
    "cantidad": Column(float, Check.ge(1), nullable=False),
    "monto_total_clp": Column(float, Check.gt(0), nullable=False),
})

MODELO_PRODUCTOS = pa.DataFrameSchema({
    "precio_unitario_clp": Column(int, Check.gt(0), coerce=True),
    "stock": Column(int, Check.ge(0), coerce=True),
})

def verificar_esquema_pandera(dataframe, modelo_schema, nombre_tabla):
    """Evalúa las restricciones físicas del dataframe usando análisis perezoso (lazy)."""
    registro_errores = {}
    try:
        modelo_schema.validate(dataframe, lazy=True)
        logging.info("Validación estructural exitosa para: %s", nombre_tabla)
    except pa.errors.SchemaErrors as error_context:
        tabla_fallas = error_context.failure_cases
        for columna_afectada in tabla_fallas["column"].dropna().unique():
            indices_afectados = tabla_fallas.loc[tabla_fallas["column"] == columna_afectada, "index"].dropna().unique()
            causa = REGLAS_FALLIDAS.get(columna_afectada, f"Falla en campo: {columna_afectada}")
            for fila_idx in indices_afectados:
                registro_errores.setdefault(int(fila_idx), []).append(causa)
            print(f"  [Estructural] {causa} -> Filas afectadas: {len(indices_afectados)}")
    return registro_errores

def registrar_falla_logica(registro_errores, serie_booleana, etiqueta_error):
    """Inserta una infracción lógica/semántica en las filas mapeadas por la máscara."""
    filas_con_falla = serie_booleana[serie_booleana].index
    for idx in filas_con_falla:
        registro_errores.setdefault(int(idx), []).append(etiqueta_error)
    print(f"  [Semántica] {etiqueta_error} -> Filas afectadas: {len(filas_con_falla)}")
    return registro_errores

def bifurcar_datos(dataframe, registro_errores, nombre_tabla):
    """Segmenta los datos limpios en archivos aprobados y rechazados."""
    indices_rechazados = sorted(registro_errores.keys())
    
    df_invalidos = dataframe.loc[indices_rechazados].copy()
    df_invalidos["motivo_rechazo"] = ["; ".join(registro_errores[i]) for i in indices_rechazados]
    
    df_validos = dataframe.drop(index=indices_rechazados)
    
    df_validos.to_csv(CONTEXTO_VALIDO / f"{nombre_tabla}.csv", index=False, encoding="utf-8")
    df_invalidos.to_csv(CONTEXTO_ERROR / f"{nombre_tabla}_errores.csv", index=False, encoding="utf-8")
    
    ratio_aprobacion = (len(df_validos) / len(dataframe)) * 100
    print(f" >> Resultados [{nombre_tabla.upper()}] Aprobados: {len(df_validos)} | Rechazados: {len(df_invalidos)} | Tasa Eficiencia: {ratio_aprobacion:.2f}%")
    return df_validos, df_invalidos

def ejecutar_auditoria():
    """Orquesta el control total de calidad sobre las entidades lógicas."""
    logging.info("Dando inicio a la Etapa 3 (Control de Calidad)")
    
    try:
        df_prod = pd.read_csv(CONTEXTO_CLEAN / "productos.csv")
        df_clie = pd.read_csv(CONTEXTO_CLEAN / "clientes.csv")
        df_pedi = pd.read_csv(CONTEXTO_CLEAN / "pedidos.csv")

        # 1. Auditoría Productos
        print(f"\n--- AUDITANDO CALIDAD: PRODUCTOS ---")
        fallas_prod = verificar_esquema_pandera(df_prod, MODELO_PRODUCTOS, "productos")
        prod_ok, _ = bifurcar_datos(df_prod, fallas_prod, "productos")

        # 2. Auditoría Clientes
        print(f"\n--- AUDITANDO CALIDAD: CLIENTES ---")
        fallas_clie = verificar_esquema_pandera(df_clie, MODELO_CLIENTES, "clientes")
        clie_ok, _ = bifurcar_datos(df_clie, fallas_clie, "clientes")

        # 3. Auditoría Pedidos (Estructural + Semántica Cruzada)
        print(f"\n--- AUDITANDO CALIDAD: PEDIDOS ---")
        df_pedi["cantidad"] = pd.to_numeric(df_pedi["cantidad"], errors="coerce")
        fallas_pedi = verificar_esquema_pandera(df_pedi, MODELO_PEDIDOS, "pedidos")

        ts_pedido = pd.to_datetime(df_pedi["fecha_pedido"], errors="coerce")
        ts_despacho = pd.to_datetime(df_pedi["fecha_despacho"], errors="coerce")

        fallas_pedi = registrar_falla_logica(fallas_pedi, (df_pedi["estado"] == "entregado") & ts_despacho.isna(), "Orden entregada sin fecha de despacho")
        fallas_pedi = registrar_falla_logica(fallas_pedi, ts_despacho < ts_pedido, "Fecha de despacho cronológicamente previa al pedido")
        fallas_pedi = registrar_falla_logica(fallas_pedi, (df_pedi["estado"] == "cancelado") & ts_despacho.notna(), "Orden cancelada registra fecha de despacho")

        # Control de coherencia matemática de totales financieros
        df_cruzado = df_pedi.merge(df_prod[["id_producto", "precio_unitario_clp"]], on="id_producto", how="left")
        monto_calculado = df_cruzado["precio_unitario_clp"] * df_cruzado["cantidad"]
        fallas_pedi = registrar_falla_logica(fallas_pedi, (df_pedi["monto_total_clp"] - monto_calculado).abs() > 1, "Incoherencia: Monto total difiere de cantidad x precio")

        # Reglas preventivas de Integridad Referencial
        fallas_pedi = registrar_falla_logica(fallas_pedi, ~df_pedi["id_cliente"].isin(df_clie["id_cliente"]), "Clave foránea inexistente: id_cliente no figura en maestros")
        fallas_pedi = registrar_falla_logica(fallas_pedi, ~df_pedi["id_producto"].isin(df_prod["id_producto"]), "Clave foránea inexistente: id_producto no figura en maestros")

        pedi_ok, _ = bifurcar_datos(df_pedi, fallas_pedi, "pedidos")

        total_procesados = len(prod_ok) + len(clie_ok) + len(pedi_ok)
        logging.info("Validación concluida. Registros aprobados totales: %d", total_procesados)
        return {"productos": prod_ok, "clientes": clie_ok, "pedidos": pedi_ok}

    except FileNotFoundError:
        logging.error("Fallo grave: Archivos limpios no localizados. Ejecute primero limpieza.py.")
        raise

if __name__ == "__main__":
    ejecutar_auditoria()