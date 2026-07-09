from ingesta import ejecutar_ingesta
from limpieza import ejecutar_limpieza
from validacion import ejecutar_validacion
from carga import ejecutar_carga

def main():
    print("Iniciando pipeline DataMart Chile...")

    df_original = ejecutar_ingesta()
    df_limpio = ejecutar_limpieza(df_original)
    df_validos, df_invalidos = ejecutar_validacion(df_limpio)
    ejecutar_carga(df_validos)

    print("Pipeline finalizado correctamente.")

if __name__ == "__main__":
    main()