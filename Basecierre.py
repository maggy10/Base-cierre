#git push para subir
import streamlit as st
import pandas as pd
import numpy as np
import pandasql as sqldf
import openpyxl

st.title("Clasificador y generador de flujo de efectivo")

#Funcion para obtener el df
def subir(base):
    # 'base' aquí ya se garantiza que no es None.
    datos = pd.read_excel(base, sheet_name=0)
    df = pd.DataFrame(datos) 
    return df 

archivo = st.file_uploader("Sube tu archivo (solo archivos de Excel)")


#Se asegura que la funcion solo se corra si archivo no vacio
if archivo is not None:
    try:
        #Lee el archivo y crea el DataFrame
        df = subir(archivo)

        #Quita valores vacios
        df_limpio = df.dropna(subset=['MES'])

        # Inserta columna de el numero de mes
        df_limpio['Mes_Numero'] = df_limpio['MES'].dt.month
        
        #Insertar el mes hasta el que quieres que se realice el flujo
        no_mes = st.number_input("Inserta el número de mes al que deseas el flujo: ")

        try:  
            #Filtra de acuerdo a ese mes
            df_corte = df_limpio.query(f'Mes_Numero <= {no_mes}')
            
            # 6. Muestra el DataFrame filtrado
            st.write(f"### Datos filtrados hasta el mes {no_mes}")
            st.write(df_corte)
            
        except ValueError:
            st.error("Por favor, introduce un número entero válido para el mes de corte.")

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo. Asegúrate de que es un archivo Excel válido. Detalles del error: {e}")
        
else:
    st.info("Esperando que subas un archivo de Excel para comenzar...")