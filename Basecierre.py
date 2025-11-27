import pandas as pd
import numpy as np
import streamlit as st
from pandasql import sqldf

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Procesador de Base Cierre",
    layout="wide",
)
## 💻 Funciones de Procesamiento

def limpiar_y_filtrar_datos(df: pd.DataFrame, no_mes: float) -> pd.DataFrame:
    """Limpia los datos, calcula el número de mes y filtra por el mes de corte."""
    df_limpio = df.dropna(subset=['MES']).copy()
    # Usamos .dt.month para extraer el mes de la columna 'MES' (asumiendo que es datetime)
    df_limpio['Mes_Numero'] = df_limpio['MES'].dt.month

    # Convertir a entero para la comparación
    no_mes_int = int(no_mes)
    df_corte = df_limpio.query(f'Mes_Numero <= {no_mes_int}')
    return df_corte

def generar_bases_ingresos(df_corte: pd.DataFrame) -> dict:
    """Calcula y agrupa los montos para cada código de ingreso."""
    
    # --- Ingresos (con correcciones para entorno local) ---

    # 1,1,1,3,1,0,0
    df_ventas_internas = df_corte[df_corte ['PARTIDA_DESCRIPCION'].str.contains('COBRANZA|COSTALERA', regex=True)]
    df_113100 = df_ventas_internas.groupby('Mes_Numero')['IMPORTE'].sum().abs().round()

    # 1,1,7,1,50,0,0
    df_otrosp = df_corte[
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IID INTERESES DEVENGADOS EN CUENTAS DE INVERSION') &
        df_corte['FUENTEFIN'].str.contains('Rec. Propios') &
        ~df_corte['CONCEPTO'].str.contains('FISCAL|FISCALES', regex=True)
    ]
    df_11715000 = df_otrosp.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,1,7,5,0,9,0,0
    otros_i_cond1 = df_corte['PARTIDA_DESCRIPCION'].str.contains('IID PENALIZACION ACEPTADA POR PROVEEDOR|IID RECUPERACION DE SINIESTROS|IID SERVICIOS POR USO DE SISTEMAS', regex=True)
    
    iar_cond = df_corte['PARTIDA_DESCRIPCION'].str.contains('IAR OTROS INGRESOS RECUPERABLES')
    conc_cond = df_corte['CONCEPTO'].str.contains('INGRESOS RECUPERALBES|RECUPERABLE|INGRESO RECIBIDO|RREINTEGRO QUE HACE LA EMPRESA', regex=True)
    neg_conc_cond = ~df_corte['CONCEPTO'].str.contains('FISCAL|FISCALES|VIATICOS|VIÁTICOS', regex=True)
    
    df_otrosi = df_corte[otros_i_cond1 | (iar_cond & conc_cond & neg_conc_cond)]
    df_11750900 = df_otrosi.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,1,9,1,1,0,0 (IVA)
    df_iva = df_corte[
        (df_corte['CAPITULO'] == 7000000) &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IAT') &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IVA')
    ]
    df_1191100 = df_iva.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,1,9,1,3,0,0 (IMPUESTOS Y NOMINA - sin IYD)
    df_impuestos = df_corte[
        (df_corte['CAPITULO'] == 7000000) &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IMPUESTOS|NOMINA', regex=True) &
        ~df_corte['PARTIDA_DESCRIPCION'].str.contains('IMPUESTOS Y DERECHOS')
    ]
    df_1191300 = df_impuestos.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,1,9,1,4,0,0 (ISR HONORARIOS)
    df_isr = df_corte[
        (df_corte['CAPITULO'] == 7000000) &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IAT') &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('ISR') &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('HONORARIOS')
    ]
    df_1191400 = df_isr.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,1,9,1,5,0,0 (ISR ARRENDAMIENTOS)
    df_isra = df_corte[
        (df_corte['CAPITULO'] == 7000000) &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IAT') &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('ISR') &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('ARRENDAMIENTOS')
    ]
    df_1191500 = df_isra.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,1,9,1,50,0,0 (Otros impuestos - IYD)
    df_otrosimp = df_corte[
        (df_corte['CAPITULO'] == 7000000) &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IAT') &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IMPUESTOS Y DERECHOS')
    ]
    df_11915000 = df_otrosimp.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,1,9,2,1,0,0 (IMSS/ISSSTE)
    df_imss = df_corte[
        (df_corte['CAPITULO'] == 7000000) &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IAT') &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IMSS|ISSSTE', regex=True)
    ]
    df_1192100 = df_imss.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,1,9,2,2,0,0 (INFONAVIT/FOVISSSTE)
    df_inf = df_corte[
        (df_corte['CAPITULO'] == 7000000) &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IAT') &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('INFONAVIT|FOVISSSTE', regex=True)
    ]
    df_1192200 = df_inf.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,1,9,3,2,0,0 (SEGUROS - Partidas específicas)
    partidas_seguros = [7211014, 7211015, 7211018]
    df_seguros = df_corte[
        (df_corte['CAPITULO'] == 7000000) &
        (df_corte['PARTIDA'].isin(partidas_seguros))
    ]
    df_1193200 = df_seguros.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,1,9,3,4,0,0 (PENAL ALIMENTICIA)
    df_penal = df_corte[
        (df_corte['CAPITULO'] == 7000000) &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IAT') &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('ALIMENTICIA')
    ]
    df_1193400 = df_penal.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,1,9,5,1,0,0 (INTERES FISCAL)
    df_intfis = df_corte[
        df_corte['PARTIDA_DESCRIPCION'].str.contains('INTERES') &
        (df_corte['CAPITULO'] == 7000000) &
        df_corte['CONCEPTO'].str.contains('FISCAL')
    ]
    df_1195100 = df_intfis.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,2,3,50,0,0,0 (IAR OTRAS RECUPERACIONES - sin los 'otros ingresos' ya clasificados)
    dfg = df_corte[
        (df_corte['CAPITULO'] == 7000000) &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('IAR|IID OTRAS RECUPERACIONES', regex=True)
    ]
    # Se replica la lógica de exclusión del dataframe df_otrosi
    # Generamos una columna de identificación para los registros de df_otrosi en dfg
    # Es más simple identificar el índice de los registros a excluir si df_otrosi fue creado con .copy()
    indices_a_excluir = df_otrosi.index
    df_iar = dfg[~dfg.index.isin(indices_a_excluir)]
    
    df_12350000 = df_iar.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,3,1,3,1,1,0 (SUBSIDIO 43101001)
    df_subsidio = df_corte[df_corte['PARTIDA'] == 43101001]
    df_1313110 = df_subsidio.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 1,3,1,3,1,6,50 (SUBSIDIO OTROS 34701101)
    df_subsidio_otros = df_corte[df_corte['PARTIDA'] == 34701101]
    df_13131650 = df_subsidio_otros.groupby('Mes_Numero')['IMPORTE'].sum().abs()
    
    # DataFrames de base de ingresos para el reporte consolidado
    df_7000_iat = pd.concat([df_iva, df_impuestos, df_isr, df_isra, df_otrosimp, df_imss, df_inf, df_seguros, df_penal, df_intfis], axis=0)
    ministracion = pd.concat([df_subsidio, df_subsidio_otros], axis=0)

    ingresos = {
        '1113100':df_113100, '11715000': df_11715000, '11750900': df_11750900, '1191100': df_1191100, '1191300': df_1191300,
        '1191400': df_1191400, '1191500':df_1191500, '11915000': df_11915000, '1192100': df_1192100, '1192200': df_1192200,
        '1193200': df_1193200, '1193400':df_1193400,'1195100': df_1195100, '12350000': df_12350000, '1313110': df_1313110,
        '13131650': df_13131650
    }
    
    df_ingresos = (pd.DataFrame(ingresos)).T
    df_ingresos.columns.name = 'Mes'
    df_ingresos.index.name = 'Clave_Ingreso'
    
    bases_ingreso = {
        'ventas_internas': df_ventas_internas,
        'interes_propio': df_otrosp,
        'otros_ingresos': df_otrosi,
        '7000_IAT': df_7000_iat,
        '7000_IAR': df_iar,
        'ministración': ministracion
    }
    
    return df_ingresos, bases_ingreso


def generar_bases_egresos(df_corte: pd.DataFrame) -> dict:
    """Calcula y agrupa los montos para cada código de egreso."""

    # --- Egresos (con correcciones para entorno local) ---

    # Concentrado para capítulos 10000000, 20000000 y 30000000 (sin exclusiones)
    exclusiones_partidaof = [39401, 39501, 39101, 39908, 39909]
    exclusion_partida = 34701101

    concentrado = df_corte[
        (df_corte['CAPITULO'] == 10000000) |
        (df_corte['CAPITULO'] == 20000000) |
        ((df_corte['CAPITULO'] == 30000000) & ~df_corte['PARTIDAOF'].isin(exclusiones_partidaof) & ~df_corte['PARTIDA'] == exclusion_partida)
    ].copy()
    
    # Creación de la columna 'CONC'
    concentrado['CONC'] = concentrado['PARTIDA'].astype(str).str.slice(0, 2)

    # MIL
    df_2111100 = (concentrado[concentrado['CONC'] == '11']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2111200 = (concentrado[concentrado['CONC'] == '12']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2111300 = (concentrado[concentrado['CONC'] == '13']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2111400 = (concentrado[concentrado['CONC'] == '14']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2111500 = (concentrado[concentrado['CONC'] == '15']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2111600 = (concentrado[concentrado['CONC'] == '16']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2111700 = (concentrado[concentrado['CONC'] == '17']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2111800 = (concentrado[concentrado['CONC'] == '18']).groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # DOS MIL
    df_2121000 = (concentrado[concentrado['CONC'] == '21']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2122000 = (concentrado[concentrado['CONC'] == '22']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2123000 = (concentrado[concentrado['CONC'] == '23']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2124000 = (concentrado[concentrado['CONC'] == '24']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2125000 = (concentrado[concentrado['CONC'] == '25']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2126000 = (concentrado[concentrado['CONC'] == '26']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2127000 = (concentrado[concentrado['CONC'] == '27']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2128000 = (concentrado[concentrado['CONC'] == '28']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2129000 = (concentrado[concentrado['CONC'] == '29']).groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # TRES MIL
    df_2131000 = (concentrado[concentrado['CONC'] == '31']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2132000 = (concentrado[concentrado['CONC'] == '32']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2133000 = (concentrado[concentrado['CONC'] == '33']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2134000 = (concentrado[concentrado['CONC'] == '34']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2135000 = (concentrado[concentrado['CONC'] == '35']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2136000 = (concentrado[concentrado['CONC'] == '36']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2137000 = (concentrado[concentrado['CONC'] == '37']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2138000 = (concentrado[concentrado['CONC'] == '38']).groupby('Mes_Numero')['IMPORTE'].sum().abs()
    df_2139000 = (concentrado[concentrado['CONC'] == '39']).groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,2,14,0,0,0,0 (Otras Erogaciones)
    df_oe = df_corte[df_corte['PARTIDAOF'].isin([39401, 39501, 39101])]
    df_22140000 = df_oe.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,3,3,1,1,0,0 (CUATROMIL - sin el subsidio 43101001)
    df_cuatromil = df_corte[(df_corte['CAPITULO'] == 40000000) & (df_corte['PARTIDA'] != 43101001)]
    df_2331100 = df_cuatromil.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,3,3,1,8,50,0 (SUBSIDIO CORRIENTES - Rec. Fiscales, sin 34701101)
    df_subcorrientes = df_corte[
        (df_corte['PARTIDAOF'] == 34701) &
        (df_corte['PARTIDA'] != 34701101) &
        df_corte['FUENTEFIN'].str.contains('Rec. Fiscales')
    ]
    df_23318500 = df_subcorrientes.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # Partidas Ajenas (EAT)
    # 2,1,8,1,1,0,0 (IVA EGRE)
    df_iva_egre = df_corte[(df_corte['CAPITULO'] == 30000000) & df_corte['PARTIDA_DESCRIPCION'].str.contains('EAT') & df_corte['PARTIDA_DESCRIPCION'].str.contains('IVA')]
    df_2181100 = df_iva_egre.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,1,8,1,3,0,0 (IMPUESTOS EGRE - sin IYD)
    df_impuestos_egre = df_corte[(df_corte['CAPITULO'] == 30000000) & df_corte['PARTIDA_DESCRIPCION'].str.contains('EAT') & df_corte['PARTIDA_DESCRIPCION'].str.contains('IMPUESTOS') & ~df_corte['PARTIDA_DESCRIPCION'].str.contains('IMPUESTOS Y DERECHOS')]
    df_2181300 = df_impuestos_egre.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,1,8,1,4,0,0 (ISR EGRE - sin ARRENDAMIENTO)
    df_isr_egre = df_corte[(df_corte['CAPITULO'] == 30000000) & df_corte['PARTIDA_DESCRIPCION'].str.contains('EAT') & df_corte['PARTIDA_DESCRIPCION'].str.contains('ISR') & ~df_corte['PARTIDA_DESCRIPCION'].str.contains('ARRENDAMIENTO')]
    df_2181400 = df_isr_egre.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,1,8,1,5,0,0 (ISR ARRENDAMIENTO EGRE)
    df_israr_egre = df_corte[(df_corte['CAPITULO'] == 30000000) & df_corte['PARTIDA_DESCRIPCION'].str.contains('EAT') & df_corte['PARTIDA_DESCRIPCION'].str.contains('ISR') & df_corte['PARTIDA_DESCRIPCION'].str.contains('ARRENDAMIENTO')]
    df_2181500 = df_israr_egre.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,1,8,1,6,0,0 (Otros Impuestos - IYD)
    df_otrosimp_egr = df_corte[(df_corte['CAPITULO'] == 30000000) & df_corte['PARTIDA_DESCRIPCION'].str.contains('EAT') & df_corte['PARTIDA_DESCRIPCION'].str.contains('IMPUESTOS Y DERECHOS')]
    df_2181600 = df_otrosimp_egr.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,1,8,2,1,0,0 (IMSS/ISSSTE EGRE)
    df_imss_egr = df_corte[(df_corte['CAPITULO'] == 30000000) & df_corte['PARTIDA_DESCRIPCION'].str.contains('EAT') & df_corte['PARTIDA_DESCRIPCION'].str.contains('IMSS|ISSSTE', regex=True)]
    df_2182100 = df_imss_egr.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,1,8,2,2,0,0 (INFONAVIT/FOVISSSTE EGRE)
    df_inf_egr = df_corte[(df_corte['CAPITULO'] == 30000000) & df_corte['PARTIDA_DESCRIPCION'].str.contains('EAT') & df_corte['PARTIDA_DESCRIPCION'].str.contains('INFONAVIT|FOVISSSTE', regex=True)]
    df_2182200 = df_inf_egr.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,1,8,2,3,0,0 (Otras Aportaciones - CESANTIA Y VEJEZ)
    df_otras_apor = df_corte[(df_corte['CAPITULO'] == 30000000) & df_corte['PARTIDA_DESCRIPCION'].str.contains('EAT') & df_corte['PARTIDA_DESCRIPCION'].str.contains('CESANTIA Y VEJEZ')]
    df_2182300 = df_otras_apor.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,1,8,3,2,0,0 (SEGUROS/MEDICO COMPLEMENTARIO EGRE)
    df_seguros_egr = df_corte[(df_corte['CAPITULO'] == 30000000) & df_corte['PARTIDA_DESCRIPCION'].str.contains('EAT') & df_corte['PARTIDA_DESCRIPCION'].str.contains('SEGURO|MEDICO COMPLEMENTARIO', regex=True)]
    df_2183200 = df_seguros_egr.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,1,8,3,4,0,0 (PENAL ALIMENTICIA EGRE)
    df_penal_egre = df_corte[(df_corte['CAPITULO'] == 30000000) & df_corte['PARTIDA_DESCRIPCION'].str.contains('EAT') & df_corte['PARTIDA_DESCRIPCION'].str.contains('ALIMENTICIA')]
    df_2183400 = df_penal_egre.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # 2,1,8,5,1,0,0 (INTERES FISCAL EGRE - sin manejo de recursos fiscales)
    df_intfis_egre = df_corte[
        df_corte['PARTIDA_DESCRIPCION'].str.contains('FISCALES') &
        (df_corte['CAPITULO'] == 30000000) &
        ~df_corte['PARTIDA_DESCRIPCION'].str.contains('MANEJO DE RECURSOS FISCALES')
    ]
    df_2185100 = df_intfis_egre.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # TESOFE (Manejo de Recursos Fiscales)
    df_tesofe = df_corte[
        df_corte['PARTIDA_DESCRIPCION'].str.contains('FISCALES') &
        (df_corte['CAPITULO'] == 30000000) &
        df_corte['PARTIDA_DESCRIPCION'].str.contains('MANEJO DE RECURSOS FISCALES')
    ]
    # No se calculó el df_tesofe_ en el original, así que se omite la variable.

    # 2,2,9,6,0,0,0 (EAR)
    df_ear = df_corte[df_corte['PARTIDA_DESCRIPCION'].str.contains('EAR')]
    df_2296000 = df_ear.groupby('Mes_Numero')['IMPORTE'].sum().abs()

    # DataFrames de base de egresos para el reporte consolidado
    ejercidoo = pd.concat([df_cuatromil, concentrado, df_subcorrientes], axis=0)
    ajenas = pd.concat([df_iva_egre, df_impuestos_egre, df_isr_egre, df_israr_egre, df_otrosimp_egr, df_imss_egr, df_inf_egr, df_otras_apor, df_seguros_egr, df_penal_egre, df_intfis_egre, df_ear], axis=0)

    egresos = {
        '2111100': df_2111100, '2111200': df_2111200, '2111300': df_2111300, '2111400': df_2111400, '2111500': df_2111500, '2111600': df_2111600, '2111700': df_2111700, '2111800': df_2111800,
        '2121000': df_2121000, '2122000': df_2122000, '2123000': df_2123000, '2124000': df_2124000, '2125000': df_2125000, '2126000': df_2126000, '2127000': df_2127000, '2128000': df_2128000, '2129000': df_2129000,
        '2131000': df_2131000, '2132000': df_2132000, '2133000': df_2133000, '2134000': df_2134000, '2135000': df_2135000, '2136000': df_2136000, '2137000': df_2137000, '2138000': df_2138000, '2139000': df_2139000,
        '22140000': df_22140000, '2331100': df_2331100, '23318500': df_23318500, '2181100': df_2181100, '2181300': df_2181300, '2181400': df_2181400, '2181500': df_2181500, '2181600': df_2181600,
        '2182100': df_2182100, '2182200': df_2182200, '2182300': df_2182300, '2183200': df_2183200, '2183400': df_2183400, '2185100': df_2185100, '2296000': df_2296000
    }
    
    df_egresos = (pd.DataFrame(egresos)).T
    df_egresos.columns.name = 'Mes'
    df_egresos.index.name = 'Clave_Egreso'
    
    bases_egreso = {
        'concentrado': ejercidoo,
        'otras_erogaciones': df_oe,
        'ajenas': ajenas,
        'tesofe': df_tesofe
    }
    
    return df_egresos, bases_egreso

def to_excel_buffer(dfs: dict, sheet_name_map: dict):
    """Guarda múltiples DataFrames en un buffer de Bytes para descarga."""
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for key, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet_name_map.get(key, key))
    processed_data = output.getvalue()
    return processed_data


## 🚀 Interfaz de Streamlit

# 1. Cargar archivo
uploaded_file = st.file_uploader("Sube el archivo de Excel", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Cargar los datos desde el archivo subido
        datos = pd.read_excel(uploaded_file, sheet_name=0)
        df = pd.DataFrame(datos)
        
        # 2. Definir mes de corte
        max_month = df['MES'].dropna().dt.month.max() if 'MES' in df.columns else 12
        if pd.isna(max_month): # En caso de que no haya fechas válidas en 'MES'
            max_month = 13
            
        no_mes = st.text_input(
            "Inserta el número de mes al que deseas el flujo (1-12):",
            min_value=1,
            max_value=int(max_month),
            value=int(max_month)
        )
        
        if st.button("Generar Reportes"):
            st.info(f"Procesando datos hasta el mes **{int(no_mes)}**...")
            
            # --- Procesamiento ---
            df_corte = limpiar_y_filtrar_datos(df, no_mes)
            df_ingresos, bases_ingreso = generar_bases_ingresos(df_corte)
            df_egresos, bases_egreso = generar_bases_egresos(df_corte)
            
            st.success("¡Reportes generados con éxito! 🎉")
            
            # --- Resultados en Streamlit ---
            tab1, tab2, tab3 = st.tabs(["Entradas (Ingresos)", "Salidas (Egresos)", "Descarga de Bases de Datos"])
            
            with tab1:
                st.header("Entradas (Ingresos)")
                st.dataframe(df_ingresos.fillna(0).style.format("{:,.2f}"))
                
                # Descarga de Flujo de Efectivo (Ingresos y Egresos)
                flujo_dfs = {'entradas': df_ingresos.fillna(0), 'salidas': df_egresos.fillna(0)}
                flujo_excel_data = to_excel_buffer(flujo_dfs, {})
                st.download_button(
                    label="Descargar Flujo de Efectivo (Excel)",
                    data=flujo_excel_data,
                    file_name='flujo_de_efectivo.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            
            with tab2:
                st.header("Salidas (Egresos)")
                st.dataframe(df_egresos.fillna(0).style.format("{:,.2f}"))
                
            with tab3:
                st.header("Bases de Datos por Clasificación")
                st.write("Contiene todos los DataFrames intermedios generados por el script original.")
                
                all_bases = {**bases_egreso, **bases_ingreso}
                sheet_map = {
                    'concentrado': 'concentrado', 'otras_erogaciones': 'otras erogaciones',
                    'ajenas': 'ajenas', 'tesofe': 'tesofe', '7000_IAR': '7000_IAR',
                    '7000_IAT': '7000_IAT', 'ventas_internas': 'costalera y cobranza',
                    'interes_propio': 'interes propio', 'otros_ingresos': 'otros ingresos',
                    'ministración': 'ministración'
                }
                
                # Descarga de Bases Consolidadas
                bases_excel_data = to_excel_buffer(all_bases, sheet_map)
                st.download_button(
                    label="Descargar Bases CEGAPS (Excel)",
                    data=bases_excel_data,
                    file_name='Base_CEGAPS.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")
        st.caption("Asegúrate de que el archivo es un Excel válido y contiene las columnas esperadas (`MES`, `IMPORTE`, `PARTIDA_DESCRIPCION`, `CAPITULO`, etc.).")

 #Para actualizar
 # git add .  
 # git commit -m "Descripción concisa de mis actualizaciones" 
 #git push
 #vericar con git status