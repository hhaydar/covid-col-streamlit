import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

@st.cache(ttl=3600,max_entries=50000)
def get_data():
    url = 'https://www.datos.gov.co/api/views/gt2j-8ykr/rows.csv?'
    url = url + 'accessType=DOWNLOAD&bom=true&format=true&delimiter=%3B'

    #Leer código Division Pólitica Admin para corregir posibles falata de datos
    #con el nombre del departamento
    df_cod_divipola = pd.read_excel('dataset/codigo_divipola.xls')
    cod_divipola_dict = dict(zip(df_cod_divipola.CODIGO, df_cod_divipola.DEPARTAMENTO))

    #Por si algo sale mal al momento de leer los datos
    try:
        data = pd.read_csv(url, sep=';')
    except:
        data = pd.read_csv('dataset/Casos_positivos_de_COVID-19_en_Colombia.csv', sep=';')

    #Replace \n (newline) for all columns
    data.rename(columns=lambda s: s.replace(' ', '_'), inplace=True)
    data.rename(columns={'ID_de_caso':'casos'}, inplace=True)

    #Corregir departamentos sin datos NaN
    #buscar el nombre en el diccionario apartir del código
    data.loc[data['Departamento_o_Distrito_'].isnull(),'Departamento_o_Distrito_'] = data['Código_DIVIPOLA'].map(cod_divipola_dict)

    #Corregir NaN en departamento y Ciudad (Solo si el código anterior no funcionó)
    data['Departamento_o_Distrito_'].fillna('No definido', inplace=True)
    data['Ciudad_de_ubicación'].fillna('No definido', inplace=True)


    #Información de latitud y longitud para los departamentos del dataset(únicamente)
    data_geo = pd.read_csv('dataset/departamentos_geocode_lat_lon.csv')

    #Feature Engineering
    #Fechas
    data['FIS'] = pd.to_datetime(data['FIS'], format='%Y-%m-%d', errors='coerce', yearfirst=True, exact=False)

    data['Fecha_de_muerte'] = pd.to_datetime(data['Fecha_de_muerte'], format='%Y-%m-%d', errors='coerce',   
    yearfirst=True, exact=False)

    data['Fecha_diagnostico'] = pd.to_datetime(data['Fecha_diagnostico'], format='%Y-%m-%d', errors='coerce', 
    yearfirst=True, exact=False)

    data['Fecha_recuperado'] = pd.to_datetime(data['Fecha_recuperado'], format='%Y-%m-%d', errors='coerce', 
    yearfirst=True, exact=False)

    data['fecha_reporte_web'] = pd.to_datetime(data['fecha_reporte_web'], format='%Y-%m-%d', errors='coerce', 
    yearfirst=True, exact=False)

    #Estado
    data['Estado'] = np.where(data['Estado'] == 'leve', 'Leve', data['Estado'])
    data['Estado'] = data['Estado'].str.strip()
    data['Departamento_o_Distrito_'] = data['Departamento_o_Distrito_'].str.strip()
    data['Ciudad_de_ubicación'] = data['Ciudad_de_ubicación'].str.strip()
    data['País_de_procedencia'] = data['País_de_procedencia'].str.strip()
    data['Sexo'] = data['Sexo'].str.strip()
    data['atención'] = data['atención'].str.strip()
    data['Tipo'] = data['Tipo'].str.strip()
    data['Sexo'] = data['Sexo'].str.upper()

    #Feature Engenieering
    #New Features
    data['Recuperado'] = np.where(data['atención'] == 'Recuperado', 'Si', 'No')
    data['Falleció'] = np.where(data['atención'] == 'Fallecido', 'Si', 'No')
    data['Extranjero'] = np.where(data['País_de_procedencia'] == 'Colombia', 'No', 'Si')

    #Edad
    data['Rango_Edad'] = pd.cut(x=data['Edad'], bins=[0, 5, 15, 25, 45, 65, 75, 999],
                        labels=['0-5', '5-15', '15-25', '25-45', '45-65', '65-75', '75->'])

    #Días Recuperación
    data['FIS'].fillna(data['fecha_reporte_web'], inplace=True)
    data['Días de tratamiento'] = abs(data['fecha_reporte_web'] - data['FIS'])
    data['Días de tratamiento'] = data['Días de tratamiento'].astype('timedelta64[D]')
    data['Días de tratamiento'].fillna(0, inplace=True)
    data['Días de tratamiento'] = data['Días de tratamiento'].astype(int)

    #Latitud y Longitud (para Departamento)
    data = data.join(data_geo.set_index('Departamento'), on='Departamento_o_Distrito_')

    #Definir Fecha Reporte Web como indice
    #data = data.rename(columns={'fecha_reporte_web':'index'}).set_index('index')

    #Return data
    return data

@st.cache(ttl=3600,max_entries=50000)
def get_data_velocidad_propagacion(df):
    dg = df.groupby([pd.Grouper(key='fecha_reporte_web', freq='W', label='left')])['fecha_reporte_web'].count().to_frame()
    #dg.drop(dg.tail(1).index,inplace=True) #drop last row, incomplete 5D seven days
    dg.rename(columns={'fecha_reporte_web':'Número de casos'}, inplace=True)
    dg.drop(dg[dg.index < '2020-03-15'].index, inplace=True)
    dg['Fila Anterior Número de casos'] = dg['Número de casos'].shift()
    dg['Velocidad de Propagación'] = dg['Número de casos'] / dg['Fila Anterior Número de casos']

    #Return data
    return dg

@st.cache(ttl=3600,max_entries=50000)
def get_data_recuperados(df):
    recu_df = pd.crosstab(df['fecha_reporte_web'],df['Recuperado'], margins=True,
                    margins_name='Total', rownames=['Fecha'], colnames=['Recuperado'])
    recu_df['Recuperados Acumulado'] = recu_df['Si'].cumsum()
    recu_df['Total Recuperados Acumulado'] = recu_df['Total'].cumsum()
    recu_df['% Acumulado Recuperados'] = (recu_df['Recuperados Acumulado'] / recu_df['Total Recuperados Acumulado'])*100

    #Return data
    return recu_df

@st.cache(ttl=3600,max_entries=50000)
def get_data_fallecidos(df):
    fallecio_df = pd.crosstab(df['fecha_reporte_web'],df['Falleció'], margins=True,
                        margins_name='Total', rownames=['Fecha'], colnames=['Fallecido'])
    try:
        fallecio_df['Fallecidos Acumulado'] = fallecio_df['Si'].cumsum()
        fallecio_df['Total Fallecidos Acumulado'] = fallecio_df['Total'].cumsum()
        fallecio_df['% Acumulado Fallecidos'] = (fallecio_df['Fallecidos Acumulado'] / fallecio_df['Total Fallecidos Acumulado'])*100
    except:
        fallecio_df['Fallecidos Acumulado'] = 0
        fallecio_df['Total Fallecidos Acumulado'] = 0
        fallecio_df['% Acumulado Fallecidos'] = 0
    #Return data
    return fallecio_df

#Create web-page
df = get_data()
df_pais_recuperados = get_data_recuperados(df.copy())
df_pais_fallecidos = get_data_fallecidos(df.copy())
df_pais_velocidad_propagacion = get_data_velocidad_propagacion(df.copy())

#Radiobutton con la lista de departamentos o distritos
lista_depto = sorted(df['Departamento_o_Distrito_'].unique())
lista_depto.insert(0, 'Colombia')
depto = st.sidebar.radio("Elije el departamento para conocer sus cifras, por defecto se muestra Colombia", lista_depto)

if depto == 'Colombia':
    df = df.query("Departamento_o_Distrito_!='None'")
else:
    df = df.query("Departamento_o_Distrito_==@depto")


#Datos descriptivos
total_casos = df.shape[0]
recuperados =  df[df['Recuperado']=='Si']['Recuperado'].count()
fallecidos =  df[df['Falleció']=='Si']['Falleció'].count()
tasa_recuperados = recuperados / total_casos
tasa_fallecidos = fallecidos / total_casos
fecha_reporte_inicial = df['fecha_reporte_web'].min()
fecha_reporte = df['fecha_reporte_web'].max()
edad_promedio = df['Edad'].median()

try:
    edad_mas_casos = df['Edad'].mode()[0]
except:
    edad_mas_casos = edad_promedio

edad_maxima = df['Edad'].max()
total_casos_hombres = df[df['Sexo'] == 'M']['Sexo'].count()
total_casos_mujeres = df[df['Sexo'] == 'F']['Sexo'].count()
tasa_casos_hombres = total_casos_hombres / total_casos
tasa_casos_mujeres = total_casos_mujeres / total_casos
recuperados_hombres =  df[(df['Recuperado']=='Si')&(df['Sexo']=='M')]['Recuperado'].count()
recuperados_mujeres = df[(df['Recuperado']=='Si')&(df['Sexo']=='F')]['Recuperado'].count()
tasa_recuperacion_hombres = recuperados_hombres / recuperados
tasa_recuperacion_mujeres = recuperados_mujeres / recuperados
edad_prom_mas_muerte = df[df['Falleció'] == 'Si']['Edad'].median()

try:
    edad_mas_muerte = df[df['Falleció'] == 'Si']['Edad'].mode()[0]
except:
    edad_mas_muerte = edad_prom_mas_muerte

min_dia_tratamiento_recu = df[(df['Recuperado']=='Si')&(df['Días de tratamiento']>0)]['Días de tratamiento'].min()
max_dia_tratamiento_recu = df[(df['Recuperado']=='Si')&(df['Días de tratamiento']>0)]['Días de tratamiento'].max()
prom_dia_tratamiento_recu = df[(df['Recuperado']=='Si')&(df['Días de tratamiento']>0)]['Días de tratamiento'].median()
try:
    mode_dia_tratamiento_recu = df[(df['Recuperado']=='Si')&(df['Días de tratamiento']>0)]['Días de tratamiento'].mode()[0]
except:
    mode_dia_tratamiento_recu = prom_dia_tratamiento_recu

#Introducción
st.title("{:,}".format(total_casos) + " Casos positivos COVID-19 en " + depto)
st.markdown("Reportados al " + fecha_reporte.strftime("%d-%m-%Y") + 
            " por el Instituto Nacional de Salud (INS)." + 
            " Se han recuperado {:,}".format(recuperados) + " personas, " +
            " representando cerca del {:.2%}".format(tasa_recuperados) + " de todos los casos." +
            " El {:.2%}".format(tasa_fallecidos) + " de los casos positivos no lograron recuperarse" +
            " lo que indica que {:,}".format(fallecidos) + " personas fallecieron por causa del virus.")
st.write("""Datos obtenidos desde
[`datos.gov.co`](https://www.datos.gov.co/Salud-y-Protecci-n-Social/Casos-positivos-de-COVID-19-en-Colombia/gt2j-8ykr/data).""")


#Sección: Factor de Crecimiento

#dg = df.groupby('fecha_reporte_web')['fecha_reporte_web'].agg(['count'])
#dg.rename(columns={'count':'Número de casos'}, inplace=True)
dg = df.groupby([pd.Grouper(key='fecha_reporte_web', freq='W', label='left')])['fecha_reporte_web'].count().to_frame()
dg.rename(columns={'fecha_reporte_web':'Número de casos'}, inplace=True)
#dg.drop(dg.tail(1).index,inplace=True) #drop last row, incomplete 7D seven days
dg.drop(dg[dg.index < '2020-03-15'].index, inplace=True)
dg['Fila Anterior Número de casos'] = dg['Número de casos'].shift()
dg['Velocidad de Propagación'] = dg['Número de casos'] / dg['Fila Anterior Número de casos']
vp = dg[dg.index==dg.index.max()]['Velocidad de Propagación'][0]

st.header("¿Qué tan rápido se propaga el virus?")
st.markdown("El factor de crecimiento o velocidad de propagación del virus es una medida que" +
            " permite determinar que tan rápido se contagian las personas." + 
            " Si el número de reproducción es mayor que 1, cada persona infectada transmite " +
            "la enfermedad al menos a una persona más." + " Para " + depto + 
            " ese valor es de :  {:.4}".format(vp))

#Initialize Figure
f = go.Figure()

if depto != 'Colombia':
    f.add_trace(go.Scatter(x=df_pais_velocidad_propagacion.index,
                            y=df_pais_velocidad_propagacion['Velocidad de Propagación'],
                            mode='lines',
                            name='Colombia'))

f.add_trace(go.Scatter(
    x=dg.index,
    y=dg['Velocidad de Propagación'],
    mode='lines+markers',
    name=depto
))
f.add_shape(
        # Line Horizontal
            type="line",
            x0=dg.index.min(),
            y0=1,
            x1=dg.index.max(),
            y1=1,
            line=dict(
                color="green",
                width=2,
                dash="solid",
            ),
    )
f.update_xaxes(title="Fecha (semana a semana)")
f.update_yaxes(title="Velocidad de Propagación")
st.plotly_chart(f)

#Sección: Afectación Por Departamento o Distrito
depto_df = pd.crosstab(df['Departamento_o_Distrito_'],df['Recuperado'],
             margins=True, margins_name='Total Casos', rownames=['Departamento'], colnames=['Recuperado'])
try:
    depto_df['% Recuperados'] = (depto_df['Si'] / depto_df['Total Casos']) * 100
    depto_df.drop('No', axis=1, inplace=True)
    depto_df.rename(columns={'Si':'Recuperados'}, inplace=True)
except:
    pass
st.header("¿Cuál es la situación por departamento?")
st.markdown("La siguiente tabla permite visualizar la tasa de recuperación por departamento." +
            " Los datos pueden ser ordenados según la necesidad, por ejemplo: conocer los departamentos con menos casos.")
st.dataframe(depto_df)

#Sección: Tasa Recuperados
st.header("¿Cuál es la tasa de recuperación desde el " + fecha_reporte_inicial.strftime("%d-%m-%Y") + "?")
st.markdown("Al día de hoy en " + depto +
            " se han recuperado {:,}".format(recuperados) + " personas, " +
            " representando cerca del {:.2%}".format(tasa_recuperados) + " de todos los casos.")
recu_df = pd.crosstab(df['fecha_reporte_web'],df['Recuperado'], margins=True,
                 margins_name='Total', rownames=['Fecha'], colnames=['Recuperado'])
recu_df['Recuperados Acumulado'] = recu_df['Si'].cumsum()
recu_df['Total Recuperados Acumulado'] = recu_df['Total'].cumsum()
recu_df['% Acumulado Recuperados'] = (recu_df['Recuperados Acumulado'] / recu_df['Total Recuperados Acumulado'])*100
#Initialize Figure
f = go.Figure()

if depto != 'Colombia':
    f.add_trace(go.Scatter(x=df_pais_recuperados.index, y=df_pais_recuperados['% Acumulado Recuperados'],
                    mode='lines',
                    name='Total Casos Colombia'))

f.add_trace(go.Scatter(x=recu_df.index, y=recu_df['% Acumulado Recuperados'],
                    mode='lines+markers',
                    name='Total Casos ' + depto))
f.update_xaxes(title="Fecha")
f.update_yaxes(title="% Acumulado Personas Recuperadas")
st.plotly_chart(f)

#Sección: Tasa Letalidad

#Sección: Tasa Letalidad
st.header("¿Cuál es la tasa de letalidad desde el " + fecha_reporte_inicial.strftime("%d-%m-%Y") + "?")
st.markdown("Al día de hoy en " + depto +
            " han fallecido {:,}".format(fallecidos) + " personas, " +
            " representando cerca del {:.2%}".format(tasa_fallecidos) + " de todos los casos.")
fallecio_df = pd.crosstab(df['fecha_reporte_web'],df['Falleció'], margins=True,
                margins_name='Total', rownames=['Fecha'], colnames=['Fallecido'])
try:
    fallecio_df['Fallecidos Acumulado'] = fallecio_df['Si'].cumsum()
    fallecio_df['Total Fallecidos Acumulado'] = fallecio_df['Total'].cumsum()
    fallecio_df['% Acumulado Fallecidos'] = (fallecio_df['Fallecidos Acumulado'] / fallecio_df['Total Fallecidos Acumulado'])*100
except:
    fallecio_df['Fallecidos Acumulado'] = 0
    fallecio_df['Total Fallecidos Acumulado'] = 0
    fallecio_df['% Acumulado Fallecidos'] = 0
#Initialize Figure
f = go.Figure()

if depto != 'Colombia':
    f.add_trace(go.Scatter(x=df_pais_recuperados.index, y=df_pais_fallecidos['% Acumulado Fallecidos'],
                    mode='lines',
                    name='Total Casos Colombia'))

f.add_trace(go.Scatter(x=fallecio_df.index, y=fallecio_df['% Acumulado Fallecidos'],
                    mode='lines+markers',
                    name='Total Casos ' + depto))

f.update_xaxes(title="Fecha")
f.update_yaxes(title="% Acumulado Personas Fallecidas")
st.plotly_chart(f)

#Sección: Distribución Edad
st.header("¿Cuál es la distribución de casos por edad?")
st.write("La edad promedio de casos positivos es de {:.0f} años,".format(edad_promedio) + 
         " sin embargo, se presentaron más casos en personas de {:.0f} años.".format(edad_mas_casos))
f = px.histogram(df, x="Edad", nbins=15, title=None)
f.update_xaxes(title="Edad")
f.update_yaxes(title="Casos positivos")
st.plotly_chart(f)

#Sección: Crecimiento Casos

st.header("¿Cuál es el comportamiento de casos por sexo?")
st.write("De los {:,} casos positivos, ".format(total_casos) + 
         " el {:.2%} son del sexo masculino y ".format(tasa_casos_hombres) + 
         "{:.2%} del femenino.".format(tasa_casos_mujeres))
st.subheader("Tasa de recuperación")
st.write("De los {:,} casos recuperados, ".format(recuperados) + 
         " el {:.2%} son del sexo masculino y ".format(tasa_recuperacion_hombres) + 
         "{:.2%} del femenino.".format(tasa_recuperacion_mujeres) + 
         " Esto es {:,} hombres y {:,} mujeres recuperados.".format(recuperados_hombres, recuperados_mujeres))

#Initialize Figure
f = go.Figure()

# Add traces
#Total Casos
dg = df.groupby('fecha_reporte_web')['fecha_reporte_web'].agg(['count'])
dg.rename(columns={'count':'Número de casos'}, inplace=True)
f.add_trace(go.Scatter(x=dg.index, y=dg['Número de casos'],
                    mode='lines+markers',
                    name='Total Casos'))
#Total Casos : Mujeres
dg = df[df['Sexo'] == 'F'].groupby('fecha_reporte_web')['fecha_reporte_web'].agg(['count'])
dg.rename(columns={'count':'Número de casos'}, inplace=True)
f.add_trace(go.Scatter(x=dg.index, y=dg['Número de casos'],
                    mode='lines',
                    name='Femenino'))

#Total Casos : Hombres
dg = df[df['Sexo'] == 'M'].groupby('fecha_reporte_web')['fecha_reporte_web'].agg(['count'])
dg.rename(columns={'count':'Número de casos'}, inplace=True)
f.add_trace(go.Scatter(x=dg.index, y=dg['Número de casos'],
                    mode='lines',
                    name='Masculino'))

f.update_xaxes(title="Fecha")
f.update_yaxes(title="#. de casos")
st.plotly_chart(f)

#Sección: Relación Edad y Muertes
st.header("¿Cuál es la relación entre la edad y las muertes?")
st.write("Para los {:,} casos positivos, ".format(total_casos) + 
         " la edad promedio de facellimiento es de {:.0f} años,".format(edad_prom_mas_muerte) + 
         " si embargo, la mayoria de casos ocurre a los {:.0f} años de edad.".format(edad_mas_muerte))
st.subheader("Duración tratamiento con recuperación satisfactoria")
st.write("De los {:,} casos recuperados, ".format(recuperados) + 
         " el tratamiento esta entre {:.0f} y {:.0f} días.".format(min_dia_tratamiento_recu, max_dia_tratamiento_recu) + 
         " En promedio las personas contagiadas se recuperan a los {:.0f} dias, ".format(prom_dia_tratamiento_recu) +
         " sin embargo, la mayoría de los casos se recuperan aproximadamente en {:.0f} días.".format(mode_dia_tratamiento_recu))

f = px.scatter(df[(df['Edad'] > 0)&(df['Días de tratamiento'] > 0)], 
                x="Edad", y="Días de tratamiento", color='Falleció')
st.plotly_chart(f)

#Mapa
st.header("Dónde estan ubicados?")
st.subheader("Mapa casos positivos")
st.markdown("El siguiente mapa muestra los departamentos con casos positivos")

st.map(df[df['lat'].notnull()][['lat','lon']])