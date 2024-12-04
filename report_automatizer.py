#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec  3 23:21:30 2024

@author: franciscotafur
"""

import streamlit as st
import pandas as pd
from io import BytesIO

def process_normal(portafolio, transacciones_dia, fecha_pa_filtrar, dia_y_mes):
    # Inicio del primer código (Normal)
    # IMPORTANTE!!! PARAMETROS PARA EDITAR CADA VEZ QUE SE USE EL PROGRAMA
    
    # Convertir la columna 'Date' a datetime
    transacciones_dia['Date'] = pd.to_datetime(transacciones_dia['Date'])
    
    # Filtrar y limpiar datos
    transacciones_dia = transacciones_dia.drop(['Description', 'Amount'], axis=1)
    transacciones_dia = transacciones_dia[transacciones_dia['Date'] == fecha_pa_filtrar]
    transacciones_dia['Action'] = transacciones_dia['Action'].replace("Sell Short", "Sell")
    
    # Separar compras y ventas
    buys_df = transacciones_dia[transacciones_dia['Action'] == 'Buy'].drop(["Fees & Comm"], axis=1)
    sells_df = transacciones_dia[transacciones_dia['Action'] == 'Sell']
    
    ventas_df = sells_df.copy()
    ventas_df['costo'] = None
    
    # Función para limpiar y convertir columnas
    def clean_and_convert(column):
        if column.dtype == 'object':
            return column.str.replace(',', '').astype(int)
        elif column.dtype in ['float64', 'int64']:
            return column.astype(int)
        else:
            return column
    
    # Limpiar y convertir columnas
    buys_df['Price'] = buys_df['Price'].str.replace('$', '').astype(float)
    ventas_df['Price'] = ventas_df['Price'].str.replace('$', '').astype(float)
    portafolio['precio_compra'] = portafolio['precio_compra'].astype(float)
    
    sells_df['Quantity'] = clean_and_convert(sells_df['Quantity'])
    buys_df['Quantity'] = clean_and_convert(buys_df['Quantity'])
    ventas_df['Quantity'] = clean_and_convert(ventas_df['Quantity'])
    
    # Ordenar compras y ventas por símbolo y precio
    ventas_df = ventas_df.groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)
    buys_df = buys_df.groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)
    
    # Crear dataframe de compras convertidas
    converted_buys = pd.DataFrame({
        'Accion': buys_df['Symbol'],
        'fecha': buys_df['Date'],
        'cantidad': buys_df['Quantity'],
        'precio_compra': buys_df['Price']
    })
    
    # Combinar con el portafolio
    portafolio_final = pd.concat([portafolio, converted_buys], ignore_index=True)
    portafolio_final = portafolio_final.sort_values(by=['Accion', 'precio_compra'], ascending=[True, True])
    
    # Inicializar columnas
    ventas_df['Quantity_compra'] = 0
    ventas_df['costo'] = 0
    
    # Copias para procesamiento
    copia_ventas_df = ventas_df.copy()
    copia_portafolio_finalf = portafolio_final.copy()
    
    # Limpiar y convertir 'Fees & Comm'
    copia_ventas_df['Fees & Comm'] = copia_ventas_df['Fees & Comm'].replace('[\$,]', '', regex=True).astype(float)
    copia_ventas_df['Fees & Comm'].fillna(0, inplace=True)
    
    # Asignar costos y fechas de compra
    for i, venta in copia_ventas_df.iterrows():
        while venta['Quantity'] > venta['Quantity_compra']:
            posibles_compras = copia_portafolio_finalf[
                (copia_portafolio_finalf['precio_compra'] < venta['Price']) &
                (copia_portafolio_finalf['Accion'] == venta['Symbol'])
            ]
            cantidad_total_ = venta["Quantity"]
            if not posibles_compras.empty:
                max_precio_compra = posibles_compras['precio_compra'].min()
                compra_elegida = posibles_compras[posibles_compras['precio_compra'] == max_precio_compra].iloc[0]
    
                fecha_compra = compra_elegida['fecha']
                cantidad_compra = min(compra_elegida['cantidad'], venta['Quantity'] - venta['Quantity_compra'])
    
                copia_ventas_df.at[i, 'costo'] += max_precio_compra * (cantidad_compra / venta['Quantity'])
                copia_ventas_df.at[i, 'fecha_compra'] = fecha_compra
                copia_ventas_df.at[i, 'Quantity_compra'] += cantidad_compra
    
                venta['Quantity_compra'] += cantidad_compra
    
                if compra_elegida['cantidad'] == cantidad_compra:
                    copia_portafolio_finalf = copia_portafolio_finalf.drop(compra_elegida.name)
                else:
                    copia_portafolio_finalf.at[compra_elegida.name, 'cantidad'] -= cantidad_compra
            else:
                if venta['Quantity'] == venta['Quantity_compra']:
                    break
                elif venta['Quantity_compra'] == 0:
                    break
                else:
                    cantidad_no_emparejada = copia_ventas_df.at[i, 'Quantity'] - copia_ventas_df.at[i, 'Quantity_compra']
                    if cantidad_no_emparejada > 0:
                        nueva_venta = copia_ventas_df.loc[i].copy()
                        nueva_venta['Quantity'] = cantidad_no_emparejada
                        nueva_venta['Quantity_compra'] = 0
                        nueva_venta['costo'] = 0.0
                        nueva_venta['fecha_compra'] = pd.NaT
                        nueva_venta['Fees & Comm'] = (cantidad_no_emparejada / cantidad_total_) * venta["Fees & Comm"]
    
                        nueva_venta_df = nueva_venta.to_frame().T
                        copia_ventas_df = pd.concat([copia_ventas_df, nueva_venta_df], ignore_index=True)
    
                        copia_ventas_df.at[i, 'Quantity'] = copia_ventas_df.at[i, 'Quantity_compra']
                        copia_ventas_df.at[i, 'Fees & Comm'] = (copia_ventas_df.at[i, 'Quantity'] / cantidad_total_) * venta["Fees & Comm"]
                        break
    
    # Ordenar las ventas
    copia_ventas_df = copia_ventas_df.sort_values(by=['Symbol', 'Price'], ascending=[True, True])
    
    # Seleccionar columnas relevantes
    ventas_df = copia_ventas_df[['Date', 'Action', 'Symbol', "Quantity", "Price", "Fees & Comm", "costo", "Quantity_compra"]]
    ventas_df['Quantity_compra'] = 0
    ventas_df['costo'] = 0
    ventas_df.reset_index(drop=True, inplace=True)
    
    # Repetir el algoritmo para asignar costos
    for i, venta in ventas_df.iterrows():
        while venta['Quantity'] > venta['Quantity_compra']:
            posibles_compras = portafolio_final[
                (portafolio_final['precio_compra'] < venta['Price']) &
                (portafolio_final['Accion'] == venta['Symbol'])
            ]
            if not posibles_compras.empty:
                max_precio_compra = posibles_compras['precio_compra'].min()
                compra_elegida = posibles_compras[posibles_compras['precio_compra'] == max_precio_compra].iloc[0]
    
                fecha_compra = compra_elegida['fecha']
                cantidad_compra = min(compra_elegida['cantidad'], venta['Quantity'] - venta['Quantity_compra'])
    
                ventas_df.at[i, 'costo'] += max_precio_compra * (cantidad_compra / venta['Quantity'])
                ventas_df.at[i, 'fecha_compra'] = fecha_compra
                ventas_df.at[i, 'Quantity_compra'] += cantidad_compra
    
                venta['Quantity_compra'] += cantidad_compra
    
                if compra_elegida['cantidad'] == cantidad_compra:
                    portafolio_final = portafolio_final.drop(compra_elegida.name)
                else:
                    portafolio_final.at[compra_elegida.name, 'cantidad'] -= cantidad_compra
            else:
                break
    
    # Limpiar 'Fees & Comm' y llenar NaN con 0
    ventas_df['Fees & Comm'] = ventas_df['Fees & Comm'].replace('[\$,]', '', regex=True).astype(float)
    ventas_df['Fees & Comm'].fillna(0, inplace=True)
    
    # Recalcular PnL
    ventas_df['PnL'] = (ventas_df['Price'] - ventas_df['costo']) * ventas_df['Quantity'] - ventas_df['Fees & Comm']
    
    # Renombrar columnas y calcular totales
    ventas_df.drop('Action', axis=1, inplace=True)
    ventas_df['venta_total'] = ventas_df['Quantity'] * ventas_df['Price'] - ventas_df['Fees & Comm']
    ventas_df['compra_total'] = ventas_df['Quantity_compra'] * ventas_df['costo']
    ventas_df = ventas_df[['Symbol', "Date", 'Quantity', 'Price', 'Fees & Comm', 'venta_total', 'fecha_compra',
                           'Quantity_compra', 'costo', 'compra_total', 'PnL']]
    
    ventas_df.rename(columns={
        'Date': 'FECHA DE VENTA',
        'Symbol': 'ACCION',
        'Quantity': 'CANTIDAD VENDIDA',
        'Price': 'PRECIO DE VENTA',
        'Fees & Comm': 'COMISION',
        'costo': 'COSTO UNITARIO',
        'Quantity_compra': 'CANTIDAD COMPRADA',
        'fecha_compra': 'FECHA DE COMPRA',
        'PnL': 'UTILIDAD'
    }, inplace=True)
    
    # Convertir columnas a numéricas
    columnas_a_convertir = ['CANTIDAD VENDIDA', 'PRECIO DE VENTA', 'venta_total', 'compra_total', 'UTILIDAD']
    for columna in columnas_a_convertir:
        if columna in ventas_df.columns:
            ventas_df[columna] = pd.to_numeric(ventas_df[columna], errors='coerce')
    
    # Calcular porcentaje de utilidad
    ventas_df['%'] = (ventas_df['UTILIDAD'] / ventas_df['compra_total']) * 100
    
    # Agregar SUB-TOTAL y TOTAL
    def add_subtotal(group):
        subtotal = group.sum(numeric_only=True)
        subtotal['ACCION'] = 'SUB-TOTAL'
    
        if subtotal['CANTIDAD VENDIDA'] != 0:
            subtotal['PRECIO DE VENTA'] = subtotal['venta_total'] / subtotal['CANTIDAD VENDIDA']
        else:
            subtotal['PRECIO DE VENTA'] = 0
    
        if subtotal['CANTIDAD COMPRADA'] != 0:
            subtotal['COSTO UNITARIO'] = subtotal['compra_total'] / subtotal['CANTIDAD COMPRADA']
        else:
            subtotal['COSTO UNITARIO'] = 0
    
        if subtotal['compra_total'] != 0:
            subtotal['%'] = (subtotal['UTILIDAD'] / subtotal['compra_total']) * 100
        else:
            subtotal['%'] = 0
    
        return pd.concat([group, pd.DataFrame([subtotal], columns=group.columns)])
    
    result_df = ventas_df.groupby('ACCION', as_index=False).apply(add_subtotal).reset_index(drop=True)
    
    # Calcular TOTAL
    subtotal_rows = result_df[result_df['ACCION'] == 'SUB-TOTAL']
    total = subtotal_rows[['compra_total', 'venta_total', 'UTILIDAD']].sum()
    total['ACCION'] = 'TOTAL'
    total['%'] = (total['UTILIDAD'] / total['compra_total']) * 100 if total['compra_total'] != 0 else 0
    result_df = pd.concat([result_df, pd.DataFrame([total])], ignore_index=True)
    
    ventas_df = result_df
    
    # Procesar buys_df
    buys_df['COMPRA TOTAL'] = buys_df['Quantity'] * buys_df['Price']
    buys_df = buys_df[["Date", "Symbol", 'Quantity', 'Price', "COMPRA TOTAL"]]
    buys_df.rename(columns={
        'Date': 'FECHA DE COMPRA',
        'Symbol': 'ACCION',
        'Quantity': 'CANTIDAD COMPRADA',
        'Price': 'PRECIO DE COMPRA',
    }, inplace=True)
    
    # Agregar SUB-TOTAL y TOTAL a buys_df
    def add_subtotal_buys(group):
        subtotal = group.sum(numeric_only=True)
        subtotal['ACCION'] = 'SUB-TOTAL'
    
        if subtotal['CANTIDAD COMPRADA'] != 0:
            subtotal['PRECIO DE COMPRA'] = subtotal['COMPRA TOTAL'] / subtotal['CANTIDAD COMPRADA']
        else:
            subtotal['PRECIO DE COMPRA'] = 0
    
        return pd.concat([group, pd.DataFrame([subtotal], columns=group.columns)])
    
    result_df_buys = buys_df.groupby('ACCION', as_index=False).apply(add_subtotal_buys).reset_index(drop=True)
    
    # Calcular TOTAL para buys_df
    subtotal_rows_buys = result_df_buys[result_df_buys['ACCION'] == 'SUB-TOTAL']
    total_buys = subtotal_rows_buys[['COMPRA TOTAL']].sum()
    total_buys['ACCION'] = 'TOTAL'
    result_df_buys = pd.concat([result_df_buys, pd.DataFrame([total_buys])], ignore_index=True)
    
    buys_df = result_df_buys
    
    # Procesar portafolio_final
    def add_subtotal_portafolio(group):
        subtotal = group[['cantidad', 'valor_invertido']].sum()
    
        if subtotal['cantidad'] != 0:
            subtotal['precio_compra'] = group['precio_compra'].dot(group['cantidad']) / subtotal['cantidad']
        else:
            subtotal['precio_compra'] = 0
    
        subtotal['Accion'] = 'SUB-TOTAL'
        subtotal['fecha'] = ''
    
        subtotal = subtotal[['Accion', 'fecha', 'cantidad', 'precio_compra', 'valor_invertido']]
        return pd.concat([group, pd.DataFrame([subtotal])], ignore_index=True)
    
    result_df_portafolio = portafolio_final.groupby('Accion', as_index=False).apply(add_subtotal_portafolio).reset_index(drop=True)
    
    # Calcular TOTAL para portafolio_final
    subtotal_rows_portafolio = result_df_portafolio[result_df_portafolio['Accion'] == 'SUB-TOTAL']
    total_portafolio = subtotal_rows_portafolio[['cantidad', 'valor_invertido']].sum()
    
    if total_portafolio['cantidad'] != 0:
        total_portafolio['precio_compra'] = (portafolio_final['precio_compra'] * portafolio_final['cantidad']).sum() / total_portafolio['cantidad']
    else:
        total_portafolio['precio_compra'] = 0
    
    total_portafolio['Accion'] = 'TOTAL'
    total_portafolio['fecha'] = ''
    
    total_portafolio = total_portafolio[['Accion', 'fecha', 'cantidad', 'precio_compra', 'valor_invertido']]
    result_df_portafolio = pd.concat([result_df_portafolio, pd.DataFrame([total_portafolio])], ignore_index=True)
    
    portafolio_final = result_df_portafolio
    
    # Eliminar columna 'FECHA DE VENTA'
    ventas_df.drop(columns=['FECHA DE VENTA'], inplace=True)
    
    # Guardar los DataFrames como archivos Excel en memoria
    return ventas_df, buys_df, portafolio_final

def process_opcion2(portafolio, transacciones_dia, fecha_pa_filtrar, dia_y_mes):
    # Inicio del segundo código (Opción 2)
    # IMPORTANTE!!! PARAMETROS PARA EDITAR CADA VEZ QUE SE USE EL PROGRAMA
    
    # Convertir la columna 'Date' a datetime
    transacciones_dia['Date'] = pd.to_datetime(transacciones_dia['Date'])
    
    # Filtrar y limpiar datos
    transacciones_dia = transacciones_dia.drop(['Description', 'Amount'], axis=1)
    transacciones_dia = transacciones_dia[transacciones_dia['Date'] == fecha_pa_filtrar]
    transacciones_dia['Action'] = transacciones_dia['Action'].replace("Sell Short", "Sell")
    
    # Separar compras y ventas
    buys_df = transacciones_dia[transacciones_dia['Action'] == 'Buy'].drop(["Fees & Comm"], axis=1)
    sells_df = transacciones_dia[transacciones_dia['Action'] == 'Sell']
    
    ventas_df = sells_df.copy()
    ventas_df['costo'] = None
    
    # Función para limpiar y convertir columnas
    def clean_and_convert(column):
        if column.dtype == 'object':
            return column.str.replace(',', '').astype(int)
        elif column.dtype in ['float64', 'int64']:
            return column.astype(int)
        else:
            return column
    
    # Limpiar y convertir columnas
    buys_df['Price'] = buys_df['Price'].str.replace('$', '').astype(float)
    ventas_df['Price'] = ventas_df['Price'].str.replace('$', '').astype(float)
    portafolio['precio_compra'] = portafolio['precio_compra'].astype(float)
    
    sells_df['Quantity'] = clean_and_convert(sells_df['Quantity'])
    buys_df['Quantity'] = clean_and_convert(buys_df['Quantity'])
    ventas_df['Quantity'] = clean_and_convert(ventas_df['Quantity'])
    
    # Ordenar compras y ventas por símbolo y precio
    ventas_df = ventas_df.groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)
    buys_df = buys_df.groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)
    
    # Crear dataframe de compras convertidas
    converted_buys = pd.DataFrame({
        'Accion': buys_df['Symbol'],
        'fecha': buys_df['Date'],
        'cantidad': buys_df['Quantity'],
        'precio_compra': buys_df['Price']
    })
    
    # Combinar con el portafolio
    portafolio_final = pd.concat([portafolio, converted_buys], ignore_index=True)
    portafolio_final = portafolio_final.sort_values(by=['Accion', 'precio_compra'], ascending=[True, True])
    
    # Inicializar columnas
    ventas_df['Quantity_compra'] = 0
    ventas_df['costo'] = 0
    
    # Copias para procesamiento
    copia_ventas_df = ventas_df.copy()
    copia_portafolio_finalf = portafolio_final.copy()
    
    # Limpiar y convertir 'Fees & Comm'
    copia_ventas_df['Fees & Comm'] = copia_ventas_df['Fees & Comm'].replace('[\$,]', '', regex=True).astype(float)
    copia_ventas_df['Fees & Comm'].fillna(0, inplace=True)
    
    # Asignar costos y fechas de compra
    for i, venta in copia_ventas_df.iterrows():
        while venta['Quantity'] > venta['Quantity_compra']:
            posibles_compras = copia_portafolio_finalf[
                (copia_portafolio_finalf['precio_compra'] < venta['Price']) &
                (copia_portafolio_finalf['Accion'] == venta['Symbol'])
            ]
            cantidad_total_ = venta["Quantity"]
            if not posibles_compras.empty:
                max_precio_compra = posibles_compras['precio_compra'].min()
                compra_elegida = posibles_compras[posibles_compras['precio_compra'] == max_precio_compra].iloc[0]
    
                fecha_compra = compra_elegida['fecha']
                cantidad_compra = min(compra_elegida['cantidad'], venta['Quantity'] - venta['Quantity_compra'])
    
                copia_ventas_df.at[i, 'costo'] += max_precio_compra * (cantidad_compra / venta['Quantity'])
                copia_ventas_df.at[i, 'fecha_compra'] = fecha_compra
                copia_ventas_df.at[i, 'Quantity_compra'] += cantidad_compra
    
                venta['Quantity_compra'] += cantidad_compra
    
                if compra_elegida['cantidad'] == cantidad_compra:
                    copia_portafolio_finalf = copia_portafolio_finalf.drop(compra_elegida.name)
                else:
                    copia_portafolio_finalf.at[compra_elegida.name, 'cantidad'] -= cantidad_compra
            else:
                if venta['Quantity'] == venta['Quantity_compra']:
                    break
                elif venta['Quantity_compra'] == 0:
                    break
                else:
                    cantidad_no_emparejada = copia_ventas_df.at[i, 'Quantity'] - copia_ventas_df.at[i, 'Quantity_compra']
                    if cantidad_no_emparejada > 0:
                        nueva_venta = copia_ventas_df.loc[i].copy()
                        nueva_venta['Quantity'] = cantidad_no_emparejada
                        nueva_venta['Quantity_compra'] = 0
                        nueva_venta['costo'] = 0.0
                        nueva_venta['fecha_compra'] = pd.NaT
                        nueva_venta['Fees & Comm'] = (cantidad_no_emparejada / cantidad_total_) * venta["Fees & Comm"]
    
                        nueva_venta_df = nueva_venta.to_frame().T
                        copia_ventas_df = pd.concat([copia_ventas_df, nueva_venta_df], ignore_index=True)
    
                        copia_ventas_df.at[i, 'Quantity'] = copia_ventas_df.at[i, 'Quantity_compra']
                        copia_ventas_df.at[i, 'Fees & Comm'] = (copia_ventas_df.at[i, 'Quantity'] / cantidad_total_) * venta["Fees & Comm"]
                        break
    
    # Ordenar las ventas
    copia_ventas_df = copia_ventas_df.sort_values(by=['Symbol', 'Price'], ascending=[True, True])
    
    # Seleccionar columnas relevantes
    ventas_df = copia_ventas_df[['Date', 'Action', 'Symbol', "Quantity", "Price", "Fees & Comm", "costo", "Quantity_compra"]]
    ventas_df['Quantity_compra'] = 0
    ventas_df['costo'] = 0
    ventas_df.reset_index(drop=True, inplace=True)
    
    # Repetir el algoritmo para asignar costos
    for i, venta in ventas_df.iterrows():
        while venta['Quantity'] > venta['Quantity_compra']:
            posibles_compras = portafolio_final[
                (portafolio_final['precio_compra'] < venta['Price']) &
                (portafolio_final['Accion'] == venta['Symbol'])
            ]
            if not posibles_compras.empty:
                max_precio_compra = posibles_compras['precio_compra'].min()
                compra_elegida = posibles_compras[posibles_compras['precio_compra'] == max_precio_compra].iloc[0]
    
                fecha_compra = compra_elegida['fecha']
                cantidad_compra = min(compra_elegida['cantidad'], venta['Quantity'] - venta['Quantity_compra'])
    
                ventas_df.at[i, 'costo'] += max_precio_compra * (cantidad_compra / venta['Quantity'])
                ventas_df.at[i, 'fecha_compra'] = fecha_compra
                ventas_df.at[i, 'Quantity_compra'] += cantidad_compra
    
                venta['Quantity_compra'] += cantidad_compra
    
                if compra_elegida['cantidad'] == cantidad_compra:
                    portafolio_final = portafolio_final.drop(compra_elegida.name)
                else:
                    portafolio_final.at[compra_elegida.name, 'cantidad'] -= cantidad_compra
            else:
                break
            
    # Limpiar 'Fees & Comm' y llenar NaN con 0
    ventas_df['Fees & Comm'] = ventas_df['Fees & Comm'].replace('[\$,]', '', regex=True).astype(float)
    ventas_df['Fees & Comm'].fillna(0, inplace=True)
    
    # Recalcular PnL
    ventas_df['PnL'] = (ventas_df['Price'] - ventas_df['costo']) * ventas_df['Quantity'] - ventas_df['Fees & Comm']
    
    # Renombrar columnas y calcular totales
    ventas_df.drop('Action', axis=1, inplace=True)
    ventas_df['venta_total'] = ventas_df['Quantity'] * ventas_df['Price'] - ventas_df['Fees & Comm']
    ventas_df['compra_total'] = ventas_df['Quantity_compra'] * ventas_df['costo']
    ventas_df = ventas_df[['Symbol', "Date", 'Quantity', 'Price', 'Fees & Comm', 'venta_total', 'fecha_compra',
                           'Quantity_compra', 'costo', 'compra_total', 'PnL']]
    
    ventas_df.rename(columns={
        'Date': 'FECHA DE VENTA',
        'Symbol': 'ACCION',
        'Quantity': 'CANTIDAD VENDIDA',
        'Price': 'PRECIO DE VENTA',
        'Fees & Comm': 'COMISION',
        'costo': 'COSTO UNITARIO',
        'Quantity_compra': 'CANTIDAD COMPRADA',
        'fecha_compra': 'FECHA DE COMPRA',
        'PnL': 'UTILIDAD'
    }, inplace=True)
    
    # Convertir columnas a numéricas
    columnas_a_convertir = ['CANTIDAD VENDIDA', 'PRECIO DE VENTA', 'venta_total', 'compra_total', 'UTILIDAD']
    for columna in columnas_a_convertir:
        if columna in ventas_df.columns:
            ventas_df[columna] = pd.to_numeric(ventas_df[columna], errors='coerce')
    
    # Calcular porcentaje de utilidad
    ventas_df['%'] = (ventas_df['UTILIDAD'] / ventas_df['compra_total']) * 100
    
    # Agregar SUB-TOTAL y TOTAL
    def add_subtotal(group):
        subtotal = group.sum(numeric_only=True)
        subtotal['ACCION'] = 'SUB-TOTAL'
    
        if subtotal['CANTIDAD VENDIDA'] != 0:
            subtotal['PRECIO DE VENTA'] = subtotal['venta_total'] / subtotal['CANTIDAD VENDIDA']
        else:
            subtotal['PRECIO DE VENTA'] = 0
    
        if subtotal['CANTIDAD COMPRADA'] != 0:
            subtotal['COSTO UNITARIO'] = subtotal['compra_total'] / subtotal['CANTIDAD COMPRADA']
        else:
            subtotal['COSTO UNITARIO'] = 0
    
        if subtotal['compra_total'] != 0:
            subtotal['%'] = (subtotal['UTILIDAD'] / subtotal['compra_total']) * 100
        else:
            subtotal['%'] = 0
    
        return pd.concat([group, pd.DataFrame([subtotal], columns=group.columns)])
    
    result_df = ventas_df.groupby('ACCION', as_index=False).apply(add_subtotal).reset_index(drop=True)
    
    # Calcular TOTAL para ventas_df
    subtotal_rows = result_df[result_df['ACCION'] == 'SUB-TOTAL']
    total = subtotal_rows[['compra_total', 'venta_total', 'UTILIDAD']].sum()
    total['ACCION'] = 'TOTAL'
    total['%'] = (total['UTILIDAD'] / total['compra_total']) * 100 if total['compra_total'] != 0 else 0
    result_df = pd.concat([result_df, pd.DataFrame([total])], ignore_index=True)
    
    ventas_df = result_df
    
    # Procesar buys_df
    buys_df['COMPRA TOTAL'] = buys_df['Quantity'] * buys_df['Price']
    buys_df = buys_df[["Date", "Symbol", 'Quantity', 'Price', "COMPRA TOTAL"]]
    buys_df.rename(columns={
        'Date': 'FECHA DE COMPRA',
        'Symbol': 'ACCION',
        'Quantity': 'CANTIDAD COMPRADA',
        'Price': 'PRECIO DE COMPRA',
    }, inplace=True)
    
    # Agregar SUB-TOTAL y TOTAL a buys_df
    def add_subtotal_buys(group):
        subtotal = group.sum(numeric_only=True)
        subtotal['ACCION'] = 'SUB-TOTAL'
    
        if subtotal['CANTIDAD COMPRADA'] != 0:
            subtotal['PRECIO DE COMPRA'] = subtotal['COMPRA TOTAL'] / subtotal['CANTIDAD COMPRADA']
        else:
            subtotal['PRECIO DE COMPRA'] = 0
    
        return pd.concat([group, pd.DataFrame([subtotal], columns=group.columns)])
    
    result_df_buys = buys_df.groupby('ACCION', as_index=False).apply(add_subtotal_buys).reset_index(drop=True)
    
    # Calcular TOTAL para buys_df
    subtotal_rows_buys = result_df_buys[result_df_buys['ACCION'] == 'SUB-TOTAL']
    total_buys = subtotal_rows_buys[['COMPRA TOTAL']].sum()
    total_buys['ACCION'] = 'TOTAL'
    result_df_buys = pd.concat([result_df_buys, pd.DataFrame([total_buys])], ignore_index=True)
    
    buys_df = result_df_buys
    
    # Procesar portafolio_final
    def add_subtotal_portafolio(group):
        subtotal = group[['cantidad', 'valor_invertido']].sum()
    
        if subtotal['cantidad'] != 0:
            subtotal['precio_compra'] = group['precio_compra'].dot(group['cantidad']) / subtotal['cantidad']
        else:
            subtotal['precio_compra'] = 0
    
        subtotal['Accion'] = 'SUB-TOTAL'
        subtotal['fecha'] = ''
    
        subtotal = subtotal[['Accion', 'fecha', 'cantidad', 'precio_compra', 'valor_invertido']]
        return pd.concat([group, pd.DataFrame([subtotal])], ignore_index=True)
    
    result_df_portafolio = portafolio_final.groupby('Accion', as_index=False).apply(add_subtotal_portafolio).reset_index(drop=True)
    
    # Calcular TOTAL para portafolio_final
    subtotal_rows_portafolio = result_df_portafolio[result_df_portafolio['Accion'] == 'SUB-TOTAL']
    total_portafolio = subtotal_rows_portafolio[['cantidad', 'valor_invertido']].sum()
    
    if total_portafolio['cantidad'] != 0:
        total_portafolio['precio_compra'] = (portafolio_final['precio_compra'] * portafolio_final['cantidad']).sum() / total_portafolio['cantidad']
    else:
        total_portafolio['precio_compra'] = 0
    
    total_portafolio['Accion'] = 'TOTAL'
    total_portafolio['fecha'] = ''
    
    total_portafolio = total_portafolio[['Accion', 'fecha', 'cantidad', 'precio_compra', 'valor_invertido']]
    result_df_portafolio = pd.concat([result_df_portafolio, pd.DataFrame([total_portafolio])], ignore_index=True)
    
    portafolio_final = result_df_portafolio
    
    # Eliminar columna 'FECHA DE VENTA'
    ventas_df.drop(columns=['FECHA DE VENTA'], inplace=True)
    
    # Guardar los DataFrames como archivos Excel en memoria
    return ventas_df, buys_df, portafolio_final

def convertir_a_excel_con_formulas(df_ventas, df_buys, df_portafolio):
    # Crear un buffer en memoria
    buffer = BytesIO()
    
    # Usar ExcelWriter con xlsxwriter como motor
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Escribir cada DataFrame en una hoja diferente
        df_ventas.to_excel(writer, index=False, sheet_name='Ventas')
        df_buys.to_excel(writer, index=False, sheet_name='Compras')
        df_portafolio.to_excel(writer, index=False, sheet_name='Portafolio')
        
        # Acceder al workbook y worksheets
        workbook  = writer.book
        worksheet_ventas = writer.sheets['Ventas']
        worksheet_buys = writer.sheets['Compras']
        worksheet_portafolio = writer.sheets['Portafolio']
        
        # Formato para las celdas con fórmulas
        formato_numero = workbook.add_format({'num_format': '#,##0.00'})
        formato_porcentaje = workbook.add_format({'num_format': '0.00%'})
        
        # Obtener dimensiones de los DataFrames
        filas_ventas, columnas_ventas = df_ventas.shape
        filas_buys, columnas_buys = df_buys.shape
        filas_portafolio, columnas_portafolio = df_portafolio.shape
        
        # Insertar fórmulas en 'Ventas'
        # Asumiendo que 'venta_total' está en la columna F (índice 5)
        # 'compra_total' en la columna J (índice 9)
        # 'PnL' en la columna K (índice 10)
        for row in range(1, filas_ventas + 1):
            # Evitar filas de 'SUB-TOTAL' y 'TOTAL'
            accion = df_ventas.at[row-1, 'ACCION']
            if accion not in ['SUB-TOTAL', 'TOTAL']:
                # Fórmula para 'venta_total' = C*D - F
                formula_venta_total = f"=C{row+2}*D{row+2}-F{row+2}"
                worksheet_ventas.write_formula(row, 5, formula_venta_total, formato_numero)
                
                # Fórmula para 'compra_total' = H*I
                formula_compra_total = f"=H{row+2}*I{row+2}"
                worksheet_ventas.write_formula(row, 9, formula_compra_total, formato_numero)
                
                # Fórmula para 'PnL' = (D - H)*C - F
                formula_pnl = f"=(D{row+2}-H{row+2})*C{row+2}-F{row+2}"
                worksheet_ventas.write_formula(row, 10, formula_pnl, formato_numero)
                
                # Fórmula para '%' = UTILIDAD / compra_total
                formula_porcentaje = f"=K{row+2}/J{row+2}"
                worksheet_ventas.write_formula(row, 11, formula_porcentaje, formato_porcentaje)
        
        # Insertar fórmulas en filas de 'SUB-TOTAL' y 'TOTAL' en 'Ventas'
        # Suponiendo que las filas de 'SUB-TOTAL' y 'TOTAL' están al final de cada grupo
        # Aquí simplemente aplicamos SUM en las columnas numéricas
        # Puedes ajustar según la estructura específica de tus datos
        
        # Similar inserción de fórmulas puede hacerse para 'Compras' y 'Portafolio'
        
        # Insertar fórmulas en 'Compras'
        # 'COMPRA TOTAL' está en la columna E (índice 4)
        for row in range(1, filas_buys + 1):
            accion = df_buys.at[row-1, 'ACCION']
            if accion not in ['SUB-TOTAL', 'TOTAL']:
                # Fórmula para 'COMPRA TOTAL' = C*D
                formula_compra_total = f"=C{row+2}*D{row+2}"
                worksheet_buys.write_formula(row, 4, formula_compra_total, formato_numero)
        
        # Insertar fórmulas en 'Portafolio'
        # Asumimos que 'valor_invertido' está en la columna E (índice 4)
        for row in range(1, filas_portafolio + 1):
            accion = df_portafolio.at[row-1, 'Accion']
            if accion not in ['SUB-TOTAL', 'TOTAL']:
                # Fórmula para 'valor_invertido' = C*D
                formula_valor_invertido = f"=C{row+2}*D{row+2}"
                worksheet_portafolio.write_formula(row, 4, formula_valor_invertido, formato_numero)
        
        # Opcional: Ajustar el ancho de las columnas para mejor visualización
        for worksheet, df in zip(
            [worksheet_ventas, worksheet_buys, worksheet_portafolio],
            [df_ventas, df_buys, df_portafolio]
        ):
            for idx, col in enumerate(df.columns):
                max_len = df[col].astype(str).map(len).max()
                max_len = max(max_len, len(col)) + 2  # Añadir un poco de espacio
                worksheet.set_column(idx, idx, max_len)
    
    # Obtener el contenido del buffer
    buffer.seek(0)
    return buffer.getvalue()

def convertir_a_excel(df):
    # Función original para convertir DataFrame a Excel sin fórmulas
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Hoja1')
    buffer.seek(0)
    return buffer.getvalue()

def main():
    st.title('Procesador de Transacciones Financieras')

    st.write('Por favor, sube los archivos de **portafolio** y **transacciones**.')

    # Widgets para cargar archivos
    portafolio_file = st.file_uploader('Subir archivo de portafolio (formato Excel)', type=['xlsx'])
    transacciones_file = st.file_uploader('Subir archivo de transacciones (formato CSV)', type=['csv'])

    # Inputs adicionales
    fecha_pa_filtrar = st.text_input('Fecha para filtrar las transacciones (formato MM/DD/AAAA)', '10/24/2024')
    dia_y_mes = st.text_input('Día y mes para los archivos de salida (ejemplo: 24octubre)', '24octubre')

    # Selección del código a utilizar
    codigo_seleccionado = st.radio('Seleccione el código a utilizar:', ['Normal (pueden quedar huecos)', 'Sin huecos (los cortos se manejan como perdida)'])

    # Inicializar variables en session_state si no existen
    if 'ventas_xlsx' not in st.session_state:
        st.session_state['ventas_xlsx'] = None
    if 'buys_xlsx' not in st.session_state:
        st.session_state['buys_xlsx'] = None
    if 'portafolio_xlsx' not in st.session_state:
        st.session_state['portafolio_xlsx'] = None

    # Botón para procesar
    if st.button('Procesar'):
        # Verificar que los archivos y campos necesarios están proporcionados
        if portafolio_file and transacciones_file and fecha_pa_filtrar and dia_y_mes:
            try:
                # Leer los archivos cargados
                portafolio = pd.read_excel(portafolio_file)
                transacciones_dia = pd.read_csv(transacciones_file)

                # Convertir fecha de filtro a formato datetime
                fecha_pa_filtrar_dt = pd.to_datetime(fecha_pa_filtrar)

                # Ejecutar el código seleccionado
                if codigo_seleccionado == 'Normal (pueden quedar huecos)':
                    ventas_df, buys_df, portafolio_final = process_normal(portafolio, transacciones_dia, fecha_pa_filtrar_dt, dia_y_mes)
                else:
                    ventas_df, buys_df, portafolio_final = process_opcion2(portafolio, transacciones_dia, fecha_pa_filtrar_dt, dia_y_mes)

                st.success('Procesamiento completado.')
                st.write('Descarga los archivos resultantes:')

                # Convertir los DataFrames a archivos Excel con fórmulas y almacenar en session_state
                st.session_state['ventas_xlsx'] = convertir_a_excel_con_formulas(ventas_df, buys_df, portafolio_final)
                st.session_state['buys_xlsx'] = convertir_a_excel(buys_df)
                st.session_state['portafolio_xlsx'] = convertir_a_excel(portafolio_final)

            except Exception as e:
                st.error(f'Ocurrió un error durante el procesamiento: {e}')
        else:
            st.error('Por favor, asegúrate de haber cargado los archivos y completado todos los campos.')

    # Mostrar los botones de descarga si los archivos están disponibles en session_state
    if st.session_state['ventas_xlsx'] and st.session_state['buys_xlsx'] and st.session_state['portafolio_xlsx']:
        st.write('### Archivos Generados')
        
        st.download_button(
            label=f'Descargar costo_{dia_y_mes}.xlsx',
            data=st.session_state['ventas_xlsx'],
            file_name=f'costo_{dia_y_mes}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        st.download_button(
            label=f'Descargar compras_{dia_y_mes}.xlsx',
            data=st.session_state['buys_xlsx'],
            file_name=f'compras_{dia_y_mes}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        st.download_button(
            label=f'Descargar portafolio_{dia_y_mes}.xlsx',
            data=st.session_state['portafolio_xlsx'],
            file_name=f'portafolio_{dia_y_mes}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

if __name__ == '__main__':
    main()