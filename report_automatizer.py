#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 28 19:31:07 2024

@author: franciscotafur
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import base64

# Function to convert a DataFrame to Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

# Function to generate a download link for a DataFrame
def get_table_download_link(df, filename, link_text):
    val = to_excel(df)
    b64 = base64.b64encode(val).decode()  # Encode to base64
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

# Streamlit App Title and Description
st.title('Aplicación de Procesamiento de Transacciones Financieras')
st.write("""
Esta aplicación procesa tus archivos de portafolio y transacciones para generar reportes detallados de compras, ventas y portafolio final.
""")

st.markdown("---")

# Sidebar for Inputs
st.sidebar.header("Parámetros de Entrada")

# 1. Fecha para filtrar las transacciones
fecha_pa_filtrar = st.sidebar.date_input(
    'Fecha para filtrar las transacciones',
    value=pd.to_datetime("2024-10-24")
)
fecha_pa_filtrar_str = fecha_pa_filtrar.strftime('%m/%d/%Y')  # Convert to string in MM/DD/YYYY format

# 2. File Uploader para el portafolio (Excel)
portafolio_file = st.sidebar.file_uploader(
    'Sube el archivo del portafolio (Excel)',
    type=['xlsx'],
    help='El archivo debe ser un Excel (.xlsx) con el portafolio.'
)

# 3. File Uploader para las transacciones del día (CSV)
transacciones_file = st.sidebar.file_uploader(
    'Sube el archivo de transacciones del día (CSV)',
    type=['csv'],
    help='El archivo debe ser un CSV con las transacciones del día.'
)

# 4. Día y mes para los archivos de salida
dia_y_mes = st.sidebar.text_input(
    'Ingresa el día y mes para los archivos de salida (ejemplo: 24octubre)',
    value='24octubre'
)

st.sidebar.markdown("---")
st.sidebar.info("Asegúrate de subir los archivos correctos y de ingresar los parámetros adecuadamente.")

# Proceed only if all inputs are provided
if portafolio_file is not None and transacciones_file is not None and dia_y_mes:
    try:
        # Lectura de archivos
        portafolio = pd.read_excel(portafolio_file)
        transacciones_dia = pd.read_csv(transacciones_file)
        
        st.success("Archivos cargados exitosamente.")
        st.markdown("---")
        
        # Mostrar los primeros registros de cada archivo
        st.subheader("Portafolio Cargado")
        st.dataframe(portafolio.head())
        
        st.subheader("Transacciones del Día Cargadas")
        st.dataframe(transacciones_dia.head())
        
        st.markdown("---")
        
        # Convertir la columna 'Date' a objeto datetime
        transacciones_dia['Date'] = pd.to_datetime(transacciones_dia['Date'], errors='coerce')
        
        # Dropear las columnas inservibles
        transacciones_dia = transacciones_dia.drop(['Description', 'Amount'], axis=1, errors='ignore')
        
        # Filtrar transacciones por la fecha proporcionada
        transacciones_dia_filtradas = transacciones_dia[transacciones_dia['Date'] == pd.to_datetime(fecha_pa_filtrar_str)]
        
        st.subheader("Transacciones Filtradas por Fecha")
        st.write(f"Fecha seleccionada: {fecha_pa_filtrar_str}")
        st.dataframe(transacciones_dia_filtradas.head())
        
        # Reemplazar 'Sell Short' con 'Sell' en la columna 'Action'
        transacciones_dia_filtradas['Action'] = transacciones_dia_filtradas['Action'].replace("Sell Short", "Sell")
        
        # Crear DataFrames para acciones de compra y venta
        buys_df = transacciones_dia_filtradas[transacciones_dia_filtradas['Action'] == 'Buy'].copy()
        buys_df = buys_df.drop(["Fees & Comm"], axis=1, errors='ignore')
        
        sells_df = transacciones_dia_filtradas[transacciones_dia_filtradas['Action'] == 'Sell'].copy()
        
        # Crear el DataFrame de costo (ventas_df)
        ventas_df = sells_df.copy()
        ventas_df['costo'] = 0.0  # Inicializar con 0
        ventas_df['Quantity_compra'] = 0  # Inicializar con 0
        
        # Definir función para limpiar y convertir columnas
        def clean_and_convert(column):
            if column.dtype == 'object':
                return column.str.replace(',', '').astype(int, errors='ignore')
            elif column.dtype in ['float64', 'int64']:
                return column.astype(int)
            else:
                return column
        
        # Limpiar y convertir columnas 'Price' y 'Quantity'
        buys_df['Price'] = buys_df['Price'].astype(str).str.replace('$', '').replace('', '0').astype(float)
        ventas_df['Price'] = ventas_df['Price'].astype(str).str.replace('$', '').replace('', '0').astype(float)
        if 'precio_compra' in portafolio.columns:
            portafolio['precio_compra'] = portafolio['precio_compra'].astype(float)
        else:
            st.warning("La columna 'precio_compra' no existe en el portafolio. Asegúrate de que el archivo tenga esta columna.")
        
        # Aplicar la función a cada columna relevante
        for df in [buys_df, sells_df, ventas_df]:
            if 'Quantity' in df.columns:
                df['Quantity'] = clean_and_convert(df['Quantity'])
        
        # Ordenar las compras y ventas
        ventas_df = ventas_df.groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)
        buys_df = buys_df.groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)
        
        # Crear el DataFrame de portafolio final
        converted_buys = pd.DataFrame({
            'Accion': buys_df['Symbol'],
            'fecha': buys_df['Date'],
            'cantidad': buys_df['Quantity'],
            'precio_compra': buys_df['Price']
        })
        
        portafolio_final = pd.concat([portafolio, converted_buys], ignore_index=True)
        portafolio_final = portafolio_final.sort_values(by=['Accion', 'precio_compra'], ascending=[True, True])
        
        # Llenar las columnas nuevas con 0 en ventas_df
        ventas_df['costo'] = 0.0
        ventas_df['Quantity_compra'] = 0
        
        # Crear copias para procesamiento
        copia_ventas_df = ventas_df.copy()
        copia_portafolio_finalf = portafolio_final.copy()
        
        # Limpiar 'Fees & Comm' y convertir a float
        if 'Fees & Comm' in copia_ventas_df.columns:
            copia_ventas_df['Fees & Comm'] = copia_ventas_df['Fees & Comm'].astype(str).str.replace('[\$,]', '', regex=True).astype(float, errors='ignore')
            copia_ventas_df['Fees & Comm'].fillna(0, inplace=True)
        else:
            copia_ventas_df['Fees & Comm'] = 0.0  # Si la columna no existe, inicializar con 0
        
        # Algoritmo de emparejamiento de ventas con compras
        for i, venta in copia_ventas_df.iterrows():
            while venta['Quantity'] > copia_ventas_df.at[i, 'Quantity_compra']:
                # Filtrar compras posibles
                posibles_compras = copia_portafolio_finalf[
                    (copia_portafolio_finalf['precio_compra'] < venta['Price']) &
                    (copia_portafolio_finalf['Accion'] == venta['Symbol'])
                ]
                
                if not posibles_compras.empty:
                    # Seleccionar la compra con el precio más bajo
                    min_precio_compra = posibles_compras['precio_compra'].min()
                    compra_elegida = posibles_compras[posibles_compras['precio_compra'] == min_precio_compra].iloc[0]
                    
                    fecha_compra = compra_elegida['fecha']
                    cantidad_compra = min(compra_elegida['cantidad'], venta['Quantity'] - copia_ventas_df.at[i, 'Quantity_compra'])
                    
                    # Actualizar el costo ponderado
                    copia_ventas_df.at[i, 'costo'] += min_precio_compra * cantidad_compra
                    copia_ventas_df.at[i, 'fecha_compra'] = fecha_compra
                    copia_ventas_df.at[i, 'Quantity_compra'] += cantidad_compra
                    
                    # Actualizar el portafolio
                    if compra_elegida['cantidad'] == cantidad_compra:
                        # Eliminar la compra usada
                        copia_portafolio_finalf = copia_portafolio_finalf.drop(compra_elegida.name)
                    else:
                        # Restar la cantidad usada de la compra
                        copia_portafolio_finalf.at[compra_elegida.name, 'cantidad'] -= cantidad_compra
                else:
                    # No hay más compras posibles que cumplan las condiciones
                    break
        
        # Reasignar ventas_df con los cálculos realizados
        ventas_df = copia_ventas_df.copy()
        
        # Calcular el PnL
        ventas_df['PnL'] = (ventas_df['Price'] - (ventas_df['costo'] / ventas_df['Quantity'])) * ventas_df['Quantity'] - ventas_df['Fees & Comm']
        
        # Manipulaciones finales para ventas_df
        ventas_df['venta_total'] = ventas_df['Quantity'] * ventas_df['Price'] - ventas_df['Fees & Comm']
        ventas_df['compra_total'] = ventas_df['Quantity_compra'] * (ventas_df['costo'] / ventas_df['Quantity'])
        
        # Reorganizar las columnas
        ventas_df = ventas_df[['Symbol', "Date", 'Quantity', 'Price', 'Fees & Comm', 'venta_total', 'fecha_compra', 
                               'Quantity_compra', 'costo', 'compra_total', 'PnL']]
        
        # Renombrar columnas
        ventas_df.rename(columns={
            'Date': 'FECHA DE VENTA',
            'Symbol': 'ACCION',
            'Quantity': 'CANTIDAD VENDIDA',
            'Price': 'PRECIO DE VENTA',
            'Fees & Comm': 'COMISION',
            'costo': 'COSTO UNITARIO',
            'Quantity_compra': 'CANTIDAD COMPRADA',
            'fecha_compra': 'FECHA DE COMPRA',
            'PnL': 'UTILIDAD',
            'venta_total': 'VENTA TOTAL',
            'compra_total': 'COMPRA TOTAL'
        }, inplace=True)
        
        # Calcular el porcentaje de utilidad
        ventas_df['%'] = (ventas_df['UTILIDAD'] / ventas_df['COMPRA TOTAL']) * 100
        ventas_df['%'] = ventas_df['%'].fillna(0)  # Manejar divisiones por cero
        
        # Función para agregar SUB-TOTAL por ACCION
        def add_subtotal_ventas(group):
            subtotal = group.sum(numeric_only=True)
            subtotal['ACCION'] = 'SUB-TOTAL'
            
            # Calcular el precio de venta promedio
            if subtotal['CANTIDAD VENDIDA'] != 0:
                subtotal['PRECIO DE VENTA'] = subtotal['VENTA TOTAL'] / subtotal['CANTIDAD VENDIDA']
            else:
                subtotal['PRECIO DE VENTA'] = 0
            
            # Calcular el costo unitario promedio
            if subtotal['CANTIDAD COMPRADA'] != 0:
                subtotal['COSTO UNITARIO'] = subtotal['COMPRA TOTAL'] / subtotal['CANTIDAD COMPRADA']
            else:
                subtotal['COSTO UNITARIO'] = 0
            
            # Calcular el porcentaje de utilidad
            if subtotal['COMPRA TOTAL'] != 0:
                subtotal['%'] = (subtotal['UTILIDAD'] / subtotal['COMPRA TOTAL']) * 100
            else:
                subtotal['%'] = 0
            
            # Reset other columns
            subtotal['FECHA DE VENTA'] = ''
            subtotal['FECHA DE COMPRA'] = ''
            subtotal['COMISION'] = 0
            subtotal['VENTA TOTAL'] = 0
            subtotal['COMPRA TOTAL'] = 0
            subtotal['CANTIDAD VENDIDA'] = 0
            subtotal['CANTIDAD COMPRADA'] = 0
            subtotal['COSTO UNITARIO'] = 0
            subtotal['UTILIDAD'] = 0
            
            return pd.concat([group, pd.DataFrame([subtotal])], ignore_index=True)
        
        # Aplicar la función por grupo de ACCION
        ventas_df = ventas_df.groupby('ACCION').apply(add_subtotal_ventas).reset_index(drop=True)
        
        # Agregar la fila TOTAL
        subtotal_rows = ventas_df[ventas_df['ACCION'] == 'SUB-TOTAL']
        total = subtotal_rows[['COMPRA TOTAL', 'VENTA TOTAL', 'UTILIDAD']].sum()
        total['ACCION'] = 'TOTAL'
        total['%'] = (total['UTILIDAD'] / total['COMPRA TOTAL']) * 100 if total['COMPRA TOTAL'] != 0 else 0
        total['PRECIO DE VENTA'] = total['VENTA TOTAL'] / total['CANTIDAD VENDIDA'] if total['CANTIDAD VENDIDA'] != 0 else 0
        total['COSTO UNITARIO'] = total['COMPRA TOTAL'] / total['CANTIDAD COMPRADA'] if total['CANTIDAD COMPRADA'] != 0 else 0
        # Reset other columns
        total['FECHA DE VENTA'] = ''
        total['FECHA DE COMPRA'] = ''
        total['COMISION'] = 0
        total['VENTA TOTAL'] = 0
        total['COMPRA TOTAL'] = 0
        total['CANTIDAD VENDIDA'] = 0
        total['CANTIDAD COMPRADA'] = 0
        total['UTILIDAD'] = 0
        # Convert to DataFrame
        total_df = pd.DataFrame([total])
        ventas_df = pd.concat([ventas_df, total_df], ignore_index=True)
        
        # Manipulaciones para buys_df
        buys_df['COMPRA TOTAL'] = buys_df['Quantity'] * buys_df['Price']
        buys_df = buys_df[['Date', "Symbol", 'Quantity', 'Price', "COMPRA TOTAL"]].copy()
        buys_df.rename(columns={
            'Date': 'FECHA DE COMPRA',
            'Symbol': 'ACCION',
            'Quantity': 'CANTIDAD COMPRADA',
            'Price': 'PRECIO DE COMPRA',
        }, inplace=True)
        
        # Función para agregar SUB-TOTAL por ACCION en buys_df
        def add_subtotal_buys(group):
            subtotal = group.sum(numeric_only=True)
            subtotal['ACCION'] = 'SUB-TOTAL'
            
            # Calcular el precio de compra promedio
            if subtotal['CANTIDAD COMPRADA'] != 0:
                subtotal['PRECIO DE COMPRA'] = subtotal['COMPRA TOTAL'] / subtotal['CANTIDAD COMPRADA']
            else:
                subtotal['PRECIO DE COMPRA'] = 0
            
            # Reset other columns
            subtotal['FECHA DE COMPRA'] = ''
            subtotal['CANTIDAD COMPRADA'] = 0
            subtotal['PRECIO DE COMPRA'] = 0
            subtotal['COMPRA TOTAL'] = 0
            
            return pd.concat([group, pd.DataFrame([subtotal])], ignore_index=True)
        
        # Aplicar la función por grupo de ACCION
        buys_df = buys_df.groupby('ACCION').apply(add_subtotal_buys).reset_index(drop=True)
        
        # Agregar la fila TOTAL en buys_df
        subtotal_rows_buys = buys_df[buys_df['ACCION'] == 'SUB-TOTAL']
        total_buys = subtotal_rows_buys[['COMPRA TOTAL']].sum()
        total_buys['ACCION'] = 'TOTAL'
        total_buys['PRECIO DE COMPRA'] = (portafolio_final['precio_compra'] * portafolio_final['cantidad']).sum() / portafolio_final['cantidad'].sum() if portafolio_final['cantidad'].sum() != 0 else 0
        # Reset other columns
        total_buys['FECHA DE COMPRA'] = ''
        total_buys['CANTIDAD COMPRADA'] = 0
        total_buys['COMPRA TOTAL'] = 0
        # Convert to DataFrame
        total_buys_df = pd.DataFrame([total_buys])
        buys_df = pd.concat([buys_df, total_buys_df], ignore_index=True)
        
        # Manipulaciones para portafolio_final
        portafolio_final['valor_invertido'] = portafolio_final['cantidad'] * portafolio_final['precio_compra']
        
        # Función para agregar SUB-TOTAL por Accion en portafolio_final
        def add_subtotal_portafolio(group):
            subtotal = group[['cantidad', 'valor_invertido']].sum()
            total_cantidad = subtotal['cantidad']
            subtotal['precio_compra'] = (group['precio_compra'] * group['cantidad']).sum() / total_cantidad if total_cantidad != 0 else 0
            subtotal['Accion'] = 'SUB-TOTAL'
            subtotal['fecha'] = ''
            # Reordenar las columnas
            subtotal = subtotal[['Accion', 'fecha', 'cantidad', 'precio_compra', 'valor_invertido']]
            return pd.concat([group, pd.DataFrame([subtotal])], ignore_index=True)
        
        # Aplicar la función por grupo de Accion
        portafolio_final = portafolio_final.groupby('Accion').apply(add_subtotal_portafolio).reset_index(drop=True)
        
        # Agregar la fila TOTAL en portafolio_final
        subtotal_rows_portafolio = portafolio_final[portafolio_final['Accion'] == 'SUB-TOTAL']
        total_portafolio = subtotal_rows_portafolio[['cantidad', 'valor_invertido']].sum()
        total_portafolio_cantidad = total_portafolio['cantidad']
        total_portafolio['precio_compra'] = (portafolio_final['precio_compra'] * portafolio_final['cantidad']).sum() / total_portafolio_cantidad if total_portafolio_cantidad != 0 else 0
        total_portafolio['Accion'] = 'TOTAL'
        total_portafolio['fecha'] = ''
        # Reordenar las columnas
        total_portafolio = total_portafolio[['Accion', 'fecha', 'cantidad', 'precio_compra', 'valor_invertido']]
        # Convert to DataFrame
        total_portafolio_df = pd.DataFrame([total_portafolio])
        portafolio_final = pd.concat([portafolio_final, total_portafolio_df], ignore_index=True)
        
        # Dropear la columna 'FECHA DE VENTA' si existe
        if 'FECHA DE VENTA' in ventas_df.columns:
            ventas_df.drop(columns=['FECHA DE VENTA'], inplace=True)
        
        # Mostrar los DataFrames procesados
        st.subheader("Portafolio Final")
        st.dataframe(portafolio_final.head())
        
        st.subheader("Ventas Procesadas")
        st.dataframe(ventas_df.head())
        
        st.subheader("Compras Procesadas")
        st.dataframe(buys_df.head())
        
        st.markdown("---")
        
        # Generar enlaces de descarga para los DataFrames
        st.subheader("Descarga de Reportes")
        st.markdown(get_table_download_link(portafolio_final, f'portafolio_{dia_y_mes}.xlsx', 'Descargar Portafolio Final'), unsafe_allow_html=True)
        st.markdown(get_table_download_link(ventas_df, f'costo_FT_{dia_y_mes}.xlsx', 'Descargar Costo FT'), unsafe_allow_html=True)
        st.markdown(get_table_download_link(buys_df, f'compras_FT_{dia_y_mes}.xlsx', 'Descargar Compras FT'), unsafe_allow_html=True)
        
        st.success("Procesamiento completado y archivos listos para descargar.")
    
    except Exception as e:
        st.error(f"Ocurrió un error durante el procesamiento: {e}")
else:
    st.info("Por favor, sube los archivos requeridos y completa todos los campos en la barra lateral para comenzar el procesamiento.")
