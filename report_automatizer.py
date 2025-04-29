"""
Created on Tue Dec  3 23:21:36 2024
@author: franciscotafur
"""

import streamlit as st
import pandas as pd
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import time
from zoneinfo import ZoneInfo

def update_google_sheet(ventas_df, positions_df, fecha_pa_filtrar):
    # Configurar conexión
    secrets = st.secrets["Google_cloud_platform"]
    creds = Credentials.from_service_account_info(
        json.loads(secrets["service_account_key"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key("157CHLt-Re4oswqd_2c_1mXgkeVo8Sc-iOsafuBHUPJA").sheet1

    # Obtener cabeceras actuales
    headers = sheet.row_values(1)

    # Paso 1: Obtener patrimonio de positions_df
    patrimonio = positions_df[
        positions_df['Symbol'] == 'Account Total'
    ]['Mkt Val (Market Value)'].values[0]
    patrimonio = float(patrimonio.replace('$', '').replace(',', ''))

    # Paso 2: Calcular utilidades por acción
    utilidades = ventas_df[
        ~ventas_df['ACCION'].isin(['TOTAL', 'SUB-TOTAL'])
    ].groupby('ACCION')['UTILIDAD'].sum().to_dict()

    # Paso 3: Identificar columnas necesarias (en minúscula)
    columnas_necesarias = {f"utilidad {symbol}" for symbol in utilidades.keys()}
    columnas_existentes = set(headers)

    # Paso 4: Crear nuevas columnas SOLO EN FILA 1
    nuevas_columnas = []
    for col in columnas_necesarias - columnas_existentes:
        headers.append(col)
        nuevas_columnas.append(col)

    # Actualizar cabeceras si hay nuevas columnas
    if nuevas_columnas:
        sheet.update('A1', [headers])
        time.sleep(2)

    # Paso 5: Construir fila de datos
    fecha_hoy = datetime.strptime(fecha_pa_filtrar, "%m/%d/%Y").strftime("%d/%m/%Y")
    fila = [
        fecha_hoy,                    # Fecha
        patrimonio,                   # Patrimonio
        "",                           # Cambio en patrimonio (vacío)
        ventas_df.loc[ventas_df['ACCION'] == 'TOTAL', 'UTILIDAD'].values[0]  # Utilidad Total
    ]

    # Paso 6: Mapear utilidades por acción
    for header in headers[4:]:  # Saltar primeras 4 columnas
        if header.startswith("utilidad "):
            symbol = header.split()[-1]
            fila.append(utilidades.get(symbol, 0))
        else:
            fila.append("")

    # Paso 7: Escribir en nueva fila
    next_row = len(sheet.col_values(1)) + 1
    sheet.update(
        f"A{next_row}:{chr(65 + len(headers) - 1)}{next_row}",
        [fila]
    )

    st.success("Datos actualizados con nuevo formato")

def update_google_sheet2(ventas_df, positions_df, fecha_pa_filtrar):
    # Configurar conexión
    secrets = st.secrets["Google_cloud_platform"]
    creds = Credentials.from_service_account_info(
        json.loads(secrets["service_account_key"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key("157CHLt-Re4oswqd_2c_1mXgkeVo8Sc-iOsafuBHUPJA").sheet1

    # Obtener cabeceras actuales
    headers = sheet.row_values(1)

    # Paso 1: Calcular utilidades por acción (sumar duplicados)
    utilidades = ventas_df[
        ~ventas_df['ACCION'].isin(['TOTAL', 'SUB-TOTAL'])
    ].groupby('ACCION')['UTILIDAD'].sum().to_dict()

    # Paso 2: Identificar columnas necesarias
    columnas_necesarias = {f"UTILIDAD {symbol}" for symbol in utilidades.keys()}
    columnas_existentes = set(headers)

    # Paso 3: Crear nuevas columnas SOLO EN FILA 1
    nuevas_columnas = []
    for col in columnas_necesarias - columnas_existentes:
        headers.append(col)
        nuevas_columnas.append(col)

    # Actualizar cabeceras si hay nuevas columnas
    if nuevas_columnas:
        sheet.update('A1', [headers])
        time.sleep(2)

    # Paso 4: Construir fila de datos
    fecha_hoy = datetime.strptime(fecha_pa_filtrar, "%m/%d/%Y").strftime("%d/%m/%Y")
    fila = [
        fecha_hoy,
        ventas_df.loc[ventas_df['ACCION'] == 'TOTAL', 'UTILIDAD'].values[0],
        ventas_df.loc[ventas_df['ACCION'] == 'TOTAL', 'venta_total'].values[0],
        ventas_df.loc[ventas_df['ACCION'] == 'TOTAL', '%'].values[0]
    ]

    # Mapear utilidades al orden correcto de columnas
    for header in headers[4:]:
        if header.startswith("UTILIDAD "):
            symbol = header.split()[-1]
            fila.append(utilidades.get(symbol, 0))
        else:
            fila.append("")

    # Paso 5: Escribir en nueva fila
    next_row = len(sheet.col_values(1)) + 1
    sheet.update(
        f"A{next_row}:{chr(65 + len(headers) - 1)}{next_row}",
        [fila]
    )

    st.success("Datos actualizados correctamente con utilidades por acción")

def update_google_sheet1(ventas_df, positions_df, fecha_pa_filtrar):
    """
    Actualiza Google Sheets con la fecha de hoy, la utilidad total diaria,
    el porcentaje de utilidad y el total de ventas.
    """
    secrets = st.secrets["Google_cloud_platform"]
    creds = Credentials.from_service_account_info(
        json.loads(secrets["service_account_key"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    sheet_id = "157CHLt-Re4oswqd_2c_1mXgkeVo8Sc-iOsafuBHUPJA"
    workbook = client.open_by_key(sheet_id)
    sheet = workbook.sheet1

    fecha_datetime = datetime.strptime(fecha_pa_filtrar, "%m/%d/%Y")
    fecha_hoy = fecha_datetime.strftime("%d/%m/%Y")

    utilidad_total = ventas_df.loc[ventas_df['ACCION'] == 'TOTAL', 'UTILIDAD'].values[0]
    porcentaje_utilidad = ventas_df.loc[ventas_df['ACCION'] == 'TOTAL', '%'].values[0]
    total_ventas = ventas_df.loc[ventas_df['ACCION'] == 'TOTAL', 'venta_total'].values[0]

    columna_a = sheet.col_values(1)
    fila_vacia = len(columna_a) + 1

    sheet.update(f"A{fila_vacia}:D{fila_vacia}",
                 [[fecha_hoy, utilidad_total, total_ventas, porcentaje_utilidad]])

    st.success("Datos escritos en el excel de google")

def process_normal(portafolio, transacciones_dia, fecha_pa_filtrar, dia_y_mes):
    # Convertir Date a datetime y filtrar
    transacciones_dia['Date'] = pd.to_datetime(transacciones_dia['Date'])
    transacciones_dia = transacciones_dia.drop(['Description', 'Amount'], axis=1)
    transacciones_dia = transacciones_dia[transacciones_dia['Date'] == fecha_pa_filtrar]

    # Normalizar columna Action
    transacciones_dia['Action'] = transacciones_dia['Action'].replace({
        "Sell Short": "Sell",
        "Buy to Open": "Buy",
        "Sell to Open": "Sell",
        "Sell to Close": "Sell",
        "Buy to Close": "Buy"
    })

    # Creo dataframes de compras y ventas
    buys_df = transacciones_dia[transacciones_dia['Action'] == 'Buy'].copy()
    sells_df = transacciones_dia[transacciones_dia['Action'] == 'Sell'].copy()

    ventas_df = sells_df.copy()
    ventas_df['costo'] = None

    # Función para limpiar cantidades
    def clean_and_convert(column):
        if column.dtype == 'object':
            return column.str.replace(',', '').astype(int)
        elif column.dtype in ['float64', 'int64']:
            return column.astype(int)
        else:
            return column

    # Limpiar y convertir columnas Price y Quantity
    buys_df['Price'] = buys_df['Price'].str.replace('$', '').astype(float)
    ventas_df['Price'] = ventas_df['Price'].str.replace('$', '').astype(float)
    portafolio['precio_compra'] = portafolio['precio_compra'].astype(float)

    sells_df['Quantity'] = clean_and_convert(sells_df['Quantity'])
    buys_df['Quantity'] = clean_and_convert(buys_df['Quantity'])
    ventas_df['Quantity'] = clean_and_convert(ventas_df['Quantity'])

    # Ordenar por Symbol y Price
    ventas_df = ventas_df.groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)
    buys_df   = buys_df  .groupby('Symbol').apply(lambda x: x.sort_values('Price')).reset_index(drop=True)

    # Portafolio final intermedio
    converted_buys = pd.DataFrame({
        'Accion': buys_df['Symbol'],
        'fecha': buys_df['Date'],
        'cantidad': buys_df['Quantity'],
        'precio_compra': buys_df['Price']
    })
    converted_buys['valor_invertido'] = converted_buys['cantidad'] * converted_buys['precio_compra']
    portafolio_final = pd.concat([portafolio, converted_buys], ignore_index=True)
    portafolio_final = portafolio_final.sort_values(['Accion','precio_compra'],ascending=[True,True])

    # Preparo ventas_df para cálculo de PnL
    ventas_df['Quantity_compra'] = 0
    ventas_df['costo'] = 0
    copia_ventas_df = ventas_df.copy()
    copia_ventas_df['Fees & Comm'] = copia_ventas_df['Fees & Comm'].replace('[\$,]', '', regex=True).astype(float)
    copia_ventas_df['Fees & Comm'].fillna(0, inplace=True)

    # Emparejamiento costo/ventas (idéntico al tuyo)
    for i, venta in copia_ventas_df.iterrows():
        while venta['Quantity'] > venta['Quantity_compra']:
            posibles_compras = portafolio_final[
                (portafolio_final['precio_compra'] < venta['Price']) &
                (portafolio_final['Accion'] == venta['Symbol'])
            ]
            if not posibles_compras.empty:
                max_precio_compra = posibles_compras['precio_compra'].min()
                compra_elegida = posibles_compras[posibles_compras['precio_compra']==max_precio_compra].iloc[0]
                fecha_compra = compra_elegida['fecha']
                cantidad_compra = min(compra_elegida['cantidad'], venta['Quantity']-venta['Quantity_compra'])
                copia_ventas_df.at[i,'costo'] += max_precio_compra * (cantidad_compra/venta['Quantity'])
                copia_ventas_df.at[i,'fecha_compra'] = fecha_compra
                copia_ventas_df.at[i,'Quantity_compra'] += cantidad_compra
                venta['Quantity_compra'] += cantidad_compra
                if compra_elegida['cantidad']==cantidad_compra:
                    portafolio_final = portafolio_final.drop(compra_elegida.name)
                else:
                    portafolio_final.at[compra_elegida.name,'cantidad'] -= cantidad_compra
            else:
                break

    ventas_df = copia_ventas_df[['Date','Action','Symbol','Quantity','Price','Fees & Comm','costo','Quantity_compra']]
    ventas_df['Fees & Comm'] = ventas_df['Fees & Comm'].fillna(0)
    ventas_df['PnL'] = (ventas_df['Price']-ventas_df['costo'])*ventas_df['Quantity'] - ventas_df['Fees & Comm']

    # Formateo final de ventas_df (idéntico al tuyo) …
    # [Aquí va todo tu bloque de renombrado, agregado de SUB-TOTAL/TOTAL para ventas_df]
    # …

    # --- BLOQUE MODIFICADO PARA buys_df ---
    # convertimos Fees & Comm y calculamos COMPRA TOTAL incluyendo comisiones
    buys_df['Fees & Comm'] = buys_df['Fees & Comm'].replace('[\$,]', '', regex=True).astype(float)
    buys_df['Fees & Comm'].fillna(0, inplace=True)
    buys_df['COMPRA TOTAL'] = buys_df['Quantity'] * buys_df['Price'] + buys_df['Fees & Comm']
    buys_df = buys_df[["Date","Symbol","Quantity","Price","Fees & Comm","COMPRA TOTAL"]]
    buys_df.rename(columns={
        'Date': 'FECHA DE COMPRA',
        'Symbol': 'ACCION',
        'Quantity': 'CANTIDAD COMPRADA',
        'Price': 'PRECIO DE COMPRA',
        'Fees & Comm': 'COMISION'
    }, inplace=True)

    def add_subtotal_buys(group):
        subtotal = group.sum(numeric_only=True)
        subtotal['ACCION'] = 'SUB-TOTAL'
        if subtotal['CANTIDAD COMPRADA']!=0:
            subtotal['PRECIO DE COMPRA'] = subtotal['COMPRA TOTAL']/subtotal['CANTIDAD COMPRADA']
        else:
            subtotal['PRECIO DE COMPRA'] = 0
        return pd.concat([group, pd.DataFrame([subtotal],columns=group.columns)])

    result_df_buys = buys_df.groupby('ACCION',as_index=False).apply(add_subtotal_buys).reset_index(drop=True)
    subtotal_rows_buys = result_df_buys[result_df_buys['ACCION']=='SUB-TOTAL']
    total_buys = subtotal_rows_buys[['COMPRA TOTAL','COMISION']].sum()
    total_buys['ACCION']='TOTAL'
    result_df_buys = pd.concat([result_df_buys,pd.DataFrame([total_buys])],ignore_index=True)
    buys_df = result_df_buys
    # --- FIN BLOQUE buys_df ---

    # Portafolio final (idéntico al tuyo) …
    # …

    return ventas_df, buys_df, portafolio_final

def process_opcion2(portafolio, transacciones_dia, fecha_pa_filtrar, dia_y_mes):
    # Igual hasta crear buys_df y sells_df …
    transacciones_dia['Date'] = pd.to_datetime(transacciones_dia['Date'])
    transacciones_dia = transacciones_dia.drop(['Description','Amount'],axis=1)
    transacciones_dia = transacciones_dia[transacciones_dia['Date']==fecha_pa_filtrar]
    transacciones_dia['Action'] = transacciones_dia['Action'].replace({
        "Sell Short":"Sell","Buy to Open":"Buy","Sell to Open":"Sell",
        "Sell to Close":"Sell","Buy to Close":"Buy"
    })

    buys_df = transacciones_dia[transacciones_dia['Action']=="Buy"].copy()
    sells_df = transacciones_dia[transacciones_dia['Action']=="Sell"].copy()

    # Conversiones Price y Quantity idénticas …
    # Emparejamiento ventas idem …

    # --- BLOQUE MODIFICADO PARA buys_df en option2 ---
    buys_df['Fees & Comm'] = buys_df['Fees & Comm'].replace('[\$,]','',regex=True).astype(float)
    buys_df['Fees & Comm'].fillna(0,inplace=True)
    buys_df['COMPRA TOTAL'] = buys_df['Quantity']*buys_df['Price'] + buys_df['Fees & Comm']
    buys_df = buys_df[["Date","Symbol","Quantity","Price","Fees & Comm","COMPRA TOTAL"]]
    buys_df.rename(columns={
        'Date':'FECHA DE COMPRA','Symbol':'ACCION','Quantity':'CANTIDAD COMPRADA',
        'Price':'PRECIO DE COMPRA','Fees & Comm':'COMISION'
    },inplace=True)

    def add_subtotal_buys(group):
        subtotal = group.sum(numeric_only=True)
        subtotal['ACCION']='SUB-TOTAL'
        if subtotal['CANTIDAD COMPRADA']!=0:
            subtotal['PRECIO DE COMPRA']=subtotal['COMPRA TOTAL']/subtotal['CANTIDAD COMPRADA']
        else:
            subtotal['PRECIO DE COMPRA']=0
        return pd.concat([group,pd.DataFrame([subtotal],columns=group.columns)])

    result_df_buys = buys_df.groupby('ACCION',as_index=False).apply(add_subtotal_buys).reset_index(drop=True)
    subtotal_rows_buys = result_df_buys[result_df_buys['ACCION']=='SUB-TOTAL']
    total_buys = subtotal_rows_buys[['COMPRA TOTAL','COMISION']].sum()
    total_buys['ACCION']='TOTAL'
    result_df_buys = pd.concat([result_df_buys,pd.DataFrame([total_buys])],ignore_index=True)
    buys_df = result_df_buys
    # --- FIN BLOQUE buys_df option2 ---

    # Resto de process_opcion2 idéntico al tuyo …
    return ventas_df, buys_df, portafolio_final

def main():
    st.title('Procesador de Transacciones Financieras')
    st.write('Por favor, sube los archivos de **portafolio**, **transacciones** y **posiciones**.')

    portafolio_file = st.file_uploader('Subir archivo de portafolio (formato Excel)', type=['xlsx'])
    transacciones_file = st.file_uploader('Subir archivo de transacciones (formato CSV)', type=['csv'])
    positions_file = st.file_uploader('Subir archivo de posiciones (formato CSV)', type=['csv'])

    ahora_bogota = datetime.now(ZoneInfo("America/Bogota"))
    fecha_hoy = ahora_bogota.strftime("%m/%d/%Y")

    fecha_pa_filtrar = st.text_input('Fecha para filtrar las transacciones (MM/DD/AAAA)', fecha_hoy)
    dia_y_mes = st.text_input('Día y mes para archivos de salida (e.g. 28abril)', '28abril')

    modo = st.radio('Seleccione el modo:', ['CMB (Normal)','FT (Sube resultados al Excel de google)'])
    codigo_seleccionado = st.radio('Seleccione el código a utilizar:', ['Normal (pueden quedar huecos)','Sin huecos (los cortos se manejan como perdida)'])

    if 'ventas_xlsx' not in st.session_state: st.session_state['ventas_xlsx'] = None
    if 'buys_xlsx'   not in st.session_state: st.session_state['buys_xlsx']   = None
    if 'portafolio_xlsx' not in st.session_state: st.session_state['portafolio_xlsx'] = None

    if st.button('Procesar'):
        if portafolio_file and transacciones_file and fecha_pa_filtrar and dia_y_mes:
            try:
                portafolio = pd.read_excel(portafolio_file)
                transacciones_dia = pd.read_csv(transacciones_file)
                positions_df = None
                if modo.startswith('FT'):
                    if not positions_file:
                        st.error("Se requiere el archivo de posiciones para el modo FT")
                        return
                    positions_df = pd.read_csv(positions_file, skiprows=3)
                    positions_df.columns = positions_df.columns.str.strip()

                fecha_pa_filtrar_dt = pd.to_datetime(fecha_pa_filtrar)

                if codigo_seleccionado.startswith('Normal'):
                    ventas_df, buys_df, portafolio_final = process_normal(portafolio, transacciones_dia, fecha_pa_filtrar_dt, dia_y_mes)
                else:
                    ventas_df, buys_df, portafolio_final = process_opcion2(portafolio, transacciones_dia, fecha_pa_filtrar_dt, dia_y_mes)

                st.success('Procesamiento completado.')
                st.write('Descarga los archivos resultantes:')

                def convertir_a_excel(df):
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Hoja1')
                    buffer.seek(0)
                    return buffer.getvalue()

                st.session_state['ventas_xlsx'] = convertir_a_excel(ventas_df)
                st.session_state['buys_xlsx']   = convertir_a_excel(buys_df)
                st.session_state['portafolio_xlsx'] = convertir_a_excel(portafolio_final)

                if modo.startswith('FT'):
                    update_google_sheet(ventas_df, positions_df, fecha_pa_filtrar)
            except Exception as e:
                st.error(f'Ocurrió un error durante el procesamiento: {e}')
        else:
            st.error('Por favor, asegúrate de haber cargado los archivos y completado todos los campos.')

    if st.session_state['ventas_xlsx']:
        st.write('### Archivos Generados')
        st.download_button('Descargar costo_'+dia_y_mes+'.xlsx', st.session_state['ventas_xlsx'], file_name='costo_'+dia_y_mes+'.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.download_button('Descargar compras_'+dia_y_mes+'.xlsx', st.session_state['buys_xlsx'],   file_name='compras_'+dia_y_mes+'.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.download_button('Descargar portafolio_'+dia_y_mes+'.xlsx', st.session_state['portafolio_xlsx'], file_name='portafolio_'+dia_y_mes+'.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    main()
