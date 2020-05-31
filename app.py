import streamlit as st
import pandas as pd
import numpy as np

#Read geo-points
df = pd.read_csv('dataset/covid-coords.csv')

#Create web-page
st.map(df[['lat','lon']])