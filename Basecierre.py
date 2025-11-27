import pandas as pd
import numpy as np
import streamlit as st
from pandasql import sqldf

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Procesador de Base Cierre",
    layout="wide",
)

# 1. Cargar archivo
arhivo = st.file_uploader("Sube el archivo de Excel", type=["xlsx"])
no_mes = st.text_input("Inserta el número de mes al que deseas el flujo (1-12):")


if arhivo is not None:
    # Cargar los datos desde el archivo subido
    datos = pd.read_excel(arhivo, sheet_name=0)
    df = pd.DataFrame(datos)
    df_m = df.head(5)
    st.write(df_m)

#Para actualizar
#git add .
#git push 
#git status