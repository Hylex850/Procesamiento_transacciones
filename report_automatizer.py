import streamlit as st
import pandas as pd
import io

def process_normal(portafolio, transacciones_dia, fecha_pa_filtrar, dia_y_mes):
    # Inicio del primer código (Normal)
    # IMPORTANTE!!! PARAMETROS PARA EDITAR CADA VEZ QUE SE USE EL PROGRAMA

    # Fecha para filtrar las transacciones
    # fecha_pa_filtrar = "10/24/2024"  # Ahora es un parámetro

    # Dia y mes para los archivos de salida
    # dia_y_mes = "24octubre"  # Ahora es un parámetro

    # Leo archivos
    # Hago conversiones de fecha
    transacciones_dia['Date'] = pd.to_datetime(transacciones_dia['Date'])

    # Manipulo datos
    # Dropeo las columnas inservibles
    transacciones_dia = transacciones_dia.drop(['Description', 'Amount'], axis=1)
    transacciones_dia = transacciones_dia[transacciones_dia['Date'] == fecha_pa_filtrar]

    # Replace 'Sell Short' with 'Sell' in the 'Action' column
    transacciones_dia['Action'] = transacciones_dia['Action'].replace("Sell Short", "Sell")

    # Creo dataframes de compras, ventas y de costo (ventas_df)
    buys_df = transacciones_dia[transacciones_dia['Action'] == 'Buy']
    buys_df = buys_df.drop(["Fees & Comm"], axis=1)
    sells_df = transacciones_dia[transacciones_dia['Action'] == 'Sell']

    ventas_df = sells_df.copy()
    ventas_df['costo'] = None

    # Convierto tipo de datos dentro de las columnas
    def clean_and_convert(column):
        if column.dtype == 'object':
            return column.str.replace(',', '').astype(int)
        elif column.dtype in ['float64', 'int64']:
            return column.astype(int)
        else:
            return column

    buys_df['Price'] = buys_df['Price'].str.replace('$', '').astype(float)
    ventas_df['Price'] = ventas_df['Price'].str.replace('$', '').astype(float)
    portafolio['precio_compra'] = portafolio['precio_compra'].astype(float)

    sells_df['Quantity'] = clean_and_convert(sells_df['Quantity'])
    buys_df['Quantity'] = clean_and_convert(buys_df['Quantity'])
    ventas_df['Quantity'] = clean_and_convert(ventas_df['Quantity'])

    # Sorting within each group
    ventas_df = ventas_df.groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)
    buys_df = buys_df.groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)

    # Creo el dataframe de portafolio final
    converted_buys = pd.DataFrame({
        'Accion': buys_df['Symbol'],
        'fecha': buys_df['Date'],
        'cantidad': buys_df['Quantity'],
        'precio_compra': buys_df['Price']
    })

    portafolio_final = pd.concat([portafolio, converted_buys], ignore_index=True)
    portafolio_final = portafolio_final.sort_values(by=['Accion', 'precio_compra'], ascending=[True, True])

    # Lleno las columnas nuevas con 0
    ventas_df['Quantity_compra'] = 0
    ventas_df['costo'] = 0

    # Algoritmo corregido
    copia_ventas_df = ventas_df.copy()
    copia_portafolio_finalf = portafolio_final.copy()

    copia_ventas_df['Fees & Comm'] = copia_ventas_df['Fees & Comm'].replace('[\$,]', '', regex=True).astype(float)
    copia_ventas_df['Fees & Comm'].fillna(0, inplace=True)

    # Iterar sobre cada fila del DataFrame de ventas
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

    # Ordenar el DataFrame combinado por 'Accion' y 'precio_compra' en orden ascendente
    copia_ventas_df = copia_ventas_df.sort_values(by=['Symbol', 'Price'], ascending=[True, True])

    ventas_df = copia_ventas_df[['Date', 'Action', 'Symbol', "Quantity", "Price", "Fees & Comm", "costo", "Quantity_compra"]]
    ventas_df['Quantity_compra'] = 0
    ventas_df['costo'] = 0
    ventas_df.reset_index(drop=True, inplace=True)

    # Corro el algoritmo
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

    # Borro el simbolo $ de la columna fees y lleno los NA con 0
    ventas_df['Fees & Comm'] = ventas_df['Fees & Comm'].replace('[\$,]', '', regex=True).astype(float)
    ventas_df['Fees & Comm'].fillna(0, inplace=True)

    # Recalcular el PnL restando las tarifas
    ventas_df['PnL'] = (ventas_df['Price'] - ventas_df['costo']) * ventas_df['Quantity'] - ventas_df['Fees & Comm']

    # Manipulo dataframes para entrega final
    # ventas_df
    # Cambio nombre de columnas
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

    # Lista de columnas que necesitan conversión
    columnas_a_convertir = ['CANTIDAD VENDIDA', 'PRECIO DE VENTA', 'venta_total', 'compra_total', 'UTILIDAD']
    for columna in columnas_a_convertir:
        if columna in ventas_df.columns:
            ventas_df[columna] = pd.to_numeric(ventas_df[columna], errors='coerce')

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

    # Filtrar las filas que contienen 'SUB-TOTAL' en la columna 'ACCION'
    subtotal_rows = result_df[result_df['ACCION'] == 'SUB-TOTAL']

    # Calcular la suma de las columnas específicas de las filas de subtotal
    total = subtotal_rows[['compra_total', 'venta_total', 'UTILIDAD']].sum()

    # Añadir otras columnas necesarias para el formato de la fila 'TOTAL'
    total['ACCION'] = 'TOTAL'

    # Calcular el porcentaje de utilidad sobre la compra total para la fila 'TOTAL'
    total['%'] = (total['UTILIDAD'] / total['compra_total']) * 100 if total['compra_total'] != 0 else 0

    # Concatenar la fila 'TOTAL' al DataFrame
    result_df = pd.concat([result_df, pd.DataFrame([total])], ignore_index=True)

    ventas_df = result_df

    # buys_df
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

    # Filtrar las filas que contienen 'SUB-TOTAL' en la columna 'ACCION'
    subtotal_rows_buys = result_df_buys[result_df_buys['ACCION'] == 'SUB-TOTAL']

    # Calcular la suma de las columnas específicas de las filas de subtotal
    total_buys = subtotal_rows_buys[['COMPRA TOTAL']].sum()

    # Añadir otras columnas necesarias para el formato de la fila 'TOTAL'
    total_buys['ACCION'] = 'TOTAL'

    # Concatenar la fila 'TOTAL' al DataFrame
    result_df_buys = pd.concat([result_df_buys, pd.DataFrame([total_buys])], ignore_index=True)

    buys_df = result_df_buys

    # Portafolio final
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

    # Filtrar las filas que contienen 'SUB-TOTAL' en la columna 'Accion'
    subtotal_rows_portafolio = result_df_portafolio[result_df_portafolio['Accion'] == 'SUB-TOTAL']

    # Calcular la suma de las columnas específicas de las filas de subtotal
    total_portafolio = subtotal_rows_portafolio[['cantidad', 'valor_invertido']].sum()

    # Calcular el precio de compra promedio ponderado para el total
    if total_portafolio['cantidad'] != 0:
        total_portafolio['precio_compra'] = (portafolio_final['precio_compra'] * portafolio_final['cantidad']).sum() / total_portafolio['cantidad']
    else:
        total_portafolio['precio_compra'] = 0

    # Añadir otras columnas necesarias para el formato de la fila 'TOTAL'
    total_portafolio['Accion'] = 'TOTAL'
    total_portafolio['fecha'] = ''

    # Reordenar las columnas
    total_portafolio = total_portafolio[['Accion', 'fecha', 'cantidad', 'precio_compra', 'valor_invertido']]

    # Concatenar la fila 'TOTAL' al DataFrame
    result_df_portafolio = pd.concat([result_df_portafolio, pd.DataFrame([total_portafolio])], ignore_index=True)

    portafolio_final = result_df_portafolio

    # Dropeo la columna de fecha de venta
    ventas_df.drop(columns=['FECHA DE VENTA'], inplace=True)

    # Guardar los DataFrames como archivos Excel en memoria
    return ventas_df, buys_df, portafolio_final

def process_opcion2(portafolio, transacciones_dia, fecha_pa_filtrar, dia_y_mes):
    # Inicio del segundo código (Opción 2)
    # IMPORTANTE!!! PARAMETROS PARA EDITAR CADA VEZ QUE SE USE EL PROGRAMA

    # Fecha para filtrar las transacciones
    # fecha_pa_filtrar = "10/29/2024"  # Ahora es un parámetro

    # Dia y mes para los archivos de salida
    # dia_y_mes = "29octubre"  # Ahora es un parámetro

    # Leo archivos
    # Hago conversiones de fecha
    transacciones_dia['Date'] = pd.to_datetime(transacciones_dia['Date'])

    # Manipulo datos
    # Dropeo las columnas inservibles
    transacciones_dia = transacciones_dia.drop(['Description', 'Amount'], axis=1)
    transacciones_dia = transacciones_dia[transacciones_dia['Date'] == fecha_pa_filtrar]

    # Replace 'Sell Short' with 'Sell' in the 'Action' column
    transacciones_dia['Action'] = transacciones_dia['Action'].replace("Sell Short", "Sell")

    # Creo dataframes de compras, ventas y de costo (ventas_df)
    buys_df = transacciones_dia[transacciones_dia['Action'] == 'Buy']
    buys_df = buys_df.drop(["Fees & Comm"], axis=1)
    sells_df = transacciones_dia[transacciones_dia['Action'] == 'Sell']

    ventas_df = sells_df.copy()
    ventas_df['costo'] = None

    # Convierto tipo de datos dentro de las columnas
    def clean_and_convert(column):
        if column.dtype == 'object':
            return column.str.replace(',', '').astype(int)
        elif column.dtype in ['float64', 'int64']:
            return column.astype(int)
        else:
            return column

    buys_df['Price'] = buys_df['Price'].str.replace('$', '').astype(float)
    ventas_df['Price'] = ventas_df['Price'].str.replace('$', '').astype(float)
    portafolio['precio_compra'] = portafolio['precio_compra'].astype(float)

    sells_df['Quantity'] = clean_and_convert(sells_df['Quantity'])
    buys_df['Quantity'] = clean_and_convert(buys_df['Quantity'])
    ventas_df['Quantity'] = clean_and_convert(ventas_df['Quantity'])

    # Sorting within each group
    ventas_df = ventas_df.groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)
    buys_df = buys_df.groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)

    # Creo el dataframe de portafolio final
    converted_buys = pd.DataFrame({
        'Accion': buys_df['Symbol'],
        'fecha': buys_df['Date'],
        'cantidad': buys_df['Quantity'],
        'precio_compra': buys_df['Price']
    })

    portafolio_final = pd.concat([portafolio, converted_buys], ignore_index=True)
    portafolio_final = portafolio_final.sort_values(by=['Accion', 'precio_compra'], ascending=[True, True])

    # Lleno las columnas nuevas con 0
    ventas_df['Quantity_compra'] = 0
    ventas_df['costo'] = 0

    # Algoritmo corregido
    copia_ventas_df = ventas_df.copy()
    copia_portafolio_finalf = portafolio_final.copy()

    copia_ventas_df['Fees & Comm'] = copia_ventas_df['Fees & Comm'].replace('[\$,]', '', regex=True).astype(float)
    copia_ventas_df['Fees & Comm'].fillna(0, inplace=True)

    # Iterar sobre cada fila del DataFrame de ventas
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

    # Ordenar el DataFrame combinado por 'Accion' y 'precio_compra' en orden ascendente
    copia_ventas_df = copia_ventas_df.sort_values(by=['Symbol', 'Price'], ascending=[True, True])

    ventas_df = copia_ventas_df[['Date', 'Action', 'Symbol', "Quantity", "Price", "Fees & Comm", "costo", "Quantity_compra"]]
    ventas_df['Quantity_compra'] = 0
    ventas_df['costo'] = 0
    ventas_df.reset_index(drop=True, inplace=True)

    # Corro el algoritmo
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

    # Borro el simbolo $ de la columna fees y lleno los NA con 0
    ventas_df['Fees & Comm'] = ventas_df['Fees & Comm'].replace('[\$,]', '', regex=True).astype(float)
    ventas_df['Fees & Comm'].fillna(0, inplace=True)

    # Recalcular el PnL restando las tarifas
    ventas_df['PnL'] = (ventas_df['Price'] - ventas_df['costo']) * ventas_df['Quantity'] - ventas_df['Fees & Comm']

    # Manipulo dataframes para entrega final
    # ventas_df
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

    # Lista de columnas que necesitan conversión
    columnas_a_convertir = ['CANTIDAD VENDIDA', 'PRECIO DE VENTA', 'venta_total', 'compra_total', 'UTILIDAD']
    for columna in columnas_a_convertir:
        if columna in ventas_df.columns:
            ventas_df[columna] = pd.to_numeric(ventas_df[columna], errors='coerce')

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

    # Filtrar las filas que contienen 'SUB-TOTAL' en la columna 'ACCION'
    subtotal_rows = result_df[result_df['ACCION'] == 'SUB-TOTAL']

    # Calcular la suma de las columnas específicas de las filas de subtotal
    total = subtotal_rows[['compra_total', 'venta_total', 'UTILIDAD']].sum()

    # Añadir otras columnas necesarias para el formato de la fila 'TOTAL'
    total['ACCION'] = 'TOTAL'

    # Calcular el porcentaje de utilidad sobre la compra total para la fila 'TOTAL'
    total['%'] = (total['UTILIDAD'] / total['compra_total']) * 100 if total['compra_total'] != 0 else 0

    # Concatenar la fila 'TOTAL' al DataFrame
    result_df = pd.concat([result_df, pd.DataFrame([total])], ignore_index=True)

    ventas_df = result_df

    # buys_df
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

    # Filtrar las filas que contienen 'SUB-TOTAL' en la columna 'ACCION'
    subtotal_rows_buys = result_df_buys[result_df_buys['ACCION'] == 'SUB-TOTAL']

    # Calcular la suma de las columnas específicas de las filas de subtotal
    total_buys = subtotal_rows_buys[['COMPRA TOTAL']].sum()

    # Añadir otras columnas necesarias para el formato de la fila 'TOTAL'
    total_buys['ACCION'] = 'TOTAL'

    # Concatenar la fila 'TOTAL' al DataFrame
    result_df_buys = pd.concat([result_df_buys, pd.DataFrame([total_buys])], ignore_index=True)

    buys_df = result_df_buys

    # Portafolio final
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

    # Filtrar las filas que contienen 'SUB-TOTAL' en la columna 'Accion'
    subtotal_rows_portafolio = result_df_portafolio[result_df_portafolio['Accion'] == 'SUB-TOTAL']

    # Calcular la suma de las columnas específicas de las filas de subtotal
    total_portafolio = subtotal_rows_portafolio[['cantidad', 'valor_invertido']].sum()

    # Calcular el precio de compra promedio ponderado para el total
    if total_portafolio['cantidad'] != 0:
        total_portafolio['precio_compra'] = (portafolio_final['precio_compra'] * portafolio_final['cantidad']).sum() / total_portafolio['cantidad']
    else:
        total_portafolio['precio_compra'] = 0

    # Añadir otras columnas necesarias para el formato de la fila 'TOTAL'
    total_portafolio['Accion'] = 'TOTAL'
    total_portafolio['fecha'] = ''

    # Reordenar las columnas
    total_portafolio = total_portafolio[['Accion', 'fecha', 'cantidad', 'precio_compra', 'valor_invertido']]

    # Concatenar la fila 'TOTAL' al DataFrame
    result_df_portafolio = pd.concat([result_df_portafolio, pd.DataFrame([total_portafolio])], ignore_index=True)

    portafolio_final = result_df_portafolio

    # Dropeo la columna de fecha de venta
    ventas_df.drop(columns=['FECHA DE VENTA'], inplace=True)

    # Guardar los DataFrames como archivos Excel en memoria
    return ventas_df, buys_df, portafolio_final

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
    codigo_seleccionado = st.radio('Seleccione el código a utilizar:', ['Normal', 'Opción 2'])

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
                if codigo_seleccionado == 'Normal':
                    ventas_df, buys_df, portafolio_final = process_normal(portafolio, transacciones_dia, fecha_pa_filtrar_dt, dia_y_mes)
                else:
                    ventas_df, buys_df, portafolio_final = process_opcion2(portafolio, transacciones_dia, fecha_pa_filtrar_dt, dia_y_mes)

                st.success('Procesamiento completado.')
                st.write('Descarga los archivos resultantes:')

                # Función auxiliar para convertir DataFrame a Excel en memoria
                def to_excel(df):
                    output = io.BytesIO()
                    writer = pd.ExcelWriter(output, engine='xlsxwriter')
                    df.to_excel(writer, index=False)
                    writer.save()
                    processed_data = output.getvalue()
                    return processed_data

                # Convertir los DataFrames a archivos Excel
                ventas_xlsx = to_excel(ventas_df)
                buys_xlsx = to_excel(buys_df)
                portafolio_xlsx = to_excel(portafolio_final)

                # Botones para descargar los archivos resultantes
                st.download_button(
                    label=f'Descargar costo_{dia_y_mes}.xlsx',
                    data=ventas_xlsx,
                    file_name=f'costo_{dia_y_mes}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

                st.download_button(
                    label=f'Descargar compras_{dia_y_mes}.xlsx',
                    data=buys_xlsx,
                    file_name=f'compras_{dia_y_mes}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

                st.download_button(
                    label=f'Descargar portafolio_{dia_y_mes}.xlsx',
                    data=portafolio_xlsx,
                    file_name=f'portafolio_{dia_y_mes}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            except Exception as e:
                st.error(f'Ocurrió un error durante el procesamiento: {e}')
        else:
            st.error('Por favor, asegúrate de haber cargado los archivos y completado todos los campos.')

if __name__ == '__main__':
    main()
