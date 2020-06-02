import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

@st.cache
def get_data():
    url = 'https://www.datos.gov.co/api/views/gt2j-8ykr/rows.csv?'
    url = url + 'accessType=DOWNLOAD&bom=true&format=true&delimiter=%3B'

    #Por si algo sale mal al momento de leer los datos
    try:
        data = pd.read_csv(url, sep=';')
    except:
        data = pd.read_csv('dataset/covid-01-06-2020.csv', sep=';')

    #Replace \n (newline) for all columns
    data.rename(columns=lambda s: s.replace(' ', '_'), inplace=True)
    data.rename(columns={'ID_de_caso':'casos'}, inplace=True)

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
    data['Recuperado'] = np.where(data['Fecha_recuperado'].notnull(), 'Si', 'No')
    data['Falleció'] = np.where(data['Fecha_de_muerte'].notnull(), 'Si', 'No')
    data['Extranjero'] = np.where(data['País_de_procedencia'] == 'Colombia', 'No', 'Si')

    #Edad
    data['Rango_Edad'] = pd.cut(x=data['Edad'], bins=[0, 5, 15, 25, 45, 65, 75, 999],
                        labels=['0-5', '5-15', '15-25', '25-45', '45-65', '65-75', '75->'])

    #Días Recuperación
    data['Días de tratamiento'] = abs(data['Fecha_recuperado'] - data['FIS'])
    data['Días de tratamiento'] = data['Días de tratamiento'].astype('timedelta64[D]')
    data['Días de tratamiento'].fillna(0, inplace=True)
    data['Días de tratamiento'] = data['Días de tratamiento'].astype(int)

    #Latitud y Longitud (para Departamento)
    data = data.join(data_geo.set_index('Departamento'), on='Departamento_o_Distrito_')

    #Definir Fecha Reporte Web como indice
    #data = data.rename(columns={'fecha_reporte_web':'index'}).set_index('index')

    #Return data
    return data

#Create web-page
df = get_data()

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
fecha_reporte = df['fecha_reporte_web'].max()
edad_promedio = df['Edad'].median()
edad_mas_casos = df['Edad'].mode()[0]
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
edad_mas_muerte = df[df['Falleció'] == 'Si']['Edad'].mode()[0]
min_dia_tratamiento_recu = df[(df['Recuperado']=='Si')&(df['Días de tratamiento']>0)]['Días de tratamiento'].min()
max_dia_tratamiento_recu = df[(df['Recuperado']=='Si')&(df['Días de tratamiento']>0)]['Días de tratamiento'].max()
prom_dia_tratamiento_recu = df[(df['Recuperado']=='Si')&(df['Días de tratamiento']>0)]['Días de tratamiento'].median()
mode_dia_tratamiento_recu = df[(df['Recuperado']=='Si')&(df['Días de tratamiento']>0)]['Días de tratamiento'].mode()[0]

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


#Sección: Distribución Edad
st.header("¿Cuál es la distribución de casos por edad?")
st.write("La edad promedio de casos positivos es de {:.0f} años,".format(edad_promedio) + 
         " sin embargo, se presentaron más casos en personas de {:.0f} años.".format(edad_mas_casos))
st.write(" Si desea puede seleccionar un rango menor desde la barra de herramientas.")
#values = st.sidebar.slider("Edad", float(df.Edad.min()), float(df.Edad.clip(upper=120.).max()), (0., 100.))
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
st.map(df[['lat','lon']])