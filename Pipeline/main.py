"""
Orquestador de Procesamiento Central - Pipeline
Flujo automatizado secuencial de datos de Extremo a Extremo.
"""

import logging
import sys
from pathlib import Path

# Importación secuencial de las interfaces del Pipeline
from ingesta import iniciar_ingesta
from limpieza import ejecutar_transformaciones
from validacion import ejecutar_auditoria
from carga import persistir_pipeline_completo

DIRECTORIO_RAIZ = Path(__file__).resolve().parent
RUTA_DATOS = DIRECTORIO_RAIZ / "data"
ARCHIVO_TRAZA = RUTA_DATOS / "pipeline.log"
ARCHIVO_TRAZA.parent.mkdir(parents=True, exist_ok=True)

# Configuración del motor de trazas e impresiones por consola en tiempo real
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (Core) %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(ARCHIVO_TRAZA, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

orquestador_log = logging.getLogger("ORQUESTADOR")

def despachar_paso(etiqueta_paso, sub_rutina):
    """Ejecutor protegido de módulos con aislamiento de trazas."""
    orquestador_log.info(f"==> Iniciando Operación: {etiqueta_paso}")
    try:
        data_retorno = sub_rutina()
        orquestador_log.info(f" Status: OK -> Operación '{etiqueta_paso}' completada.")
        return data_retorno
    except Exception as sub_error:
        orquestador_log.error(f" Status: CRITICAL -> Fallo en paso '{etiqueta_paso}': {sub_error}", exc_info=True)
        raise

def flujo_maestro():
    """Lógica principal de control secuencial del pipeline de datos."""
    orquestador_log.info("="*80)
    orquestador_log.info("ARRANQUE DE SISTEMA: PIPELINE DE DATOSuv2.0")
    orquestador_log.info("="*80)

    try:
        # Paso 1: Extracción / Ingesta
        despachar_paso("1. Extracción e Ingesta Cruda", iniciar_ingesta)

        # Paso 2: Limpieza / Transformación
        despachar_paso("2. Depuración, Normalización e Ingeniería de Atributos", ejecutar_transformaciones)

        # Paso 3: Validación de Negocio
        despachar_paso("3. Evaluación Estructural y Reglas Semánticas", ejecutar_auditoria)

        # Paso 4: Carga / Persistencia Relacional
        despachar_paso("4. Inserción Masiva y Control en Motor SQLite", persistir_pipeline_completo)

        orquestador_log.info("="*80)
        orquestador_log.info("SISTEMA: PROCESAMIENTO COMPLETADO ABSOLUTAMENTE CON ÉXITO")
        orquestador_log.info("="*80)

    except Exception:
        orquestador_log.error("="*80)
        orquestador_log.error("SISTEMA: PROCESAMIENTO DETENIDO POR ANOMALÍA EN SUBSISTEMAS")
        orquestador_log.error("="*80)
        sys.exit(1)

if __name__ == "__main__":
    flujo_maestro()