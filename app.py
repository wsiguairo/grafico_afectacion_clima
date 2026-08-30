# app.py - CÓDIGO ROBUSTO CON ACTUALIZACIÓN AUTOMÁTICA
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import make_interp_spline, UnivariateSpline
from scipy.ndimage import uniform_filter1d
import warnings
import base64
import os
import time
import datetime
import requests
import io
import hashlib
import json

warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Gráfica Alpacas",
    page_icon="🦙",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# CSS - COMPACTO CON INDICADORES
# ============================================================
st.markdown("""
<style>
    .stApp > header { display: none !important; height: 0 !important; }
    footer { display: none !important; height: 0 !important; }
    
    .main .block-container { 
        padding: 0px 10px 5px 10px !important;
        max-width: 1200px !important;
        margin: 0 auto !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }
    
    h1, h2, h3, p { margin: 0 !important; padding: 0 !important; line-height: 1 !important; }
    h2 { font-size: 1rem !important; padding: 2px 0 2px 0 !important; margin: 0 !important; line-height: 1 !important; }
    
    .stPlotlyChart {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 100% !important;
        height: 450px !important;
        margin: 0 !important;
        padding: 0 !important;
        margin-top: -5px !important;
    }
    
    .stPlotlyChart > div {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 100% !important;
        height: 450px !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .modebar { transform: scale(0.6) !important; transform-origin: top right !important; top: 2px !important; right: 2px !important; }
    .stSidebar { padding: 8px !important; margin: 0 !important; }
    .stButton button { padding: 3px 6px !important; font-size: 0.7rem !important; min-height: 24px !important; margin: 0 !important; }
    
    .stMetric { padding: 0 !important; margin: 0 !important; }
    .stMetric label { font-size: 0.6rem !important; padding: 0 !important; margin: 0 !important; }
    .stMetric div { font-size: 0.8rem !important; padding: 0 !important; margin: 0 !important; }
    
    .element-container, .stMarkdown, .stColumns, .stColumn {
        margin: 0 !important;
        padding: 0 !important;
        gap: 0 !important;
    }
    .stColumns { gap: 3px !important; margin: 0 !important; padding: 0 !important; }
    .stColumn { padding: 0 3px !important; margin: 0 !important; }
    
    .streamlit-expanderHeader { font-size: 0.8rem !important; padding: 2px 0 !important; margin: 0 !important; }
    .streamlit-expanderContent { padding: 0 !important; margin: 0 !important; }
    
    .timestamp {
        font-size: 0.7rem;
        color: #0066cc;
        padding: 0 !important;
        margin: 0 !important;
        font-weight: bold;
    }
    .timestamp span {
        display: inline-block;
        width: 8px;
        height: 8px;
        background-color: #00cc00;
        border-radius: 50%;
        margin-right: 5px;
        animation: pulse 2s infinite;
    }
    .timestamp.error span {
        background-color: #ff0000 !important;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.3; }
        100% { opacity: 1; }
    }
    
    .status-bar {
        font-size: 0.6rem;
        color: #666;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    @media (max-width: 768px) {
        .main .block-container { padding: 0px 5px 2px 5px !important; }
        .stPlotlyChart { height: 300px !important; margin-top: -3px !important; }
        .stPlotlyChart > div { height: 300px !important; }
        h2 { font-size: 0.8rem !important; padding: 1px 0 !important; }
        .stButton button { font-size: 0.6rem !important; padding: 2px 4px !important; min-height: 18px !important; }
        .modebar { transform: scale(0.5) !important; }
        .timestamp { font-size: 0.5rem !important; }
    }
    
    @media (max-width: 480px) {
        .stPlotlyChart { height: 220px !important; }
        .stPlotlyChart > div { height: 220px !important; }
        h2 { font-size: 0.7rem !important; }
        .stButton button { font-size: 0.5rem !important; padding: 1px 3px !important; min-height: 14px !important; }
        .stMetric label { font-size: 0.5rem !important; }
        .stMetric div { font-size: 0.6rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# JAVASCRIPT PARA AUTO-REFRESH
# ============================================================
st.components.v1.html("""
<script>
    // Auto-refresh cada 30 segundos
    setInterval(function() {
        location.reload();
    }, 30000);
</script>
""", height=0)

# ============================================================
# DICCIONARIO DE MESES
# ============================================================
MESES_ES = {
    1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr',
    5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago',
    9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
}

def fecha_espanol(fecha):
    if isinstance(fecha, pd.Timestamp):
        return f"{MESES_ES[fecha.month]} {fecha.year}"
    return str(fecha)

def image_to_base64(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                return base64.b64encode(f.read()).decode()
        except:
            return None
    return None

# ============================================================
# FUNCIÓN PARA CALCULAR HASH DE DATOS
# ============================================================
def calcular_hash_datos(df):
    """Calcula un hash único de los datos para detectar cambios"""
    if df is None or df.empty:
        return "vacio"
    # Crear hash de las columnas numéricas
    datos_str = df.select_dtypes(include=[np.number]).to_string()
    return hashlib.md5(datos_str.encode()).hexdigest()

# ============================================================
# FUNCIÓN ROBUSTA PARA CARGAR DATOS
# ============================================================
def cargar_datos_robusto(sheet_id, sheet_sintomas, sheet_temperaturas):
    """
    Carga datos con múltiples estrategias anti-caché
    """
    resultados = []
    
    # Estrategia 1: requests con timestamp y headers anti-caché
    try:
        t = int(time.time() * 1000)
        
        url_sintomas = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_sintomas}&_={t}"
        url_temperaturas = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_temperaturas}&_={t}"
        
        headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '0',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Descargar con timeout
        response_sintomas = requests.get(url_sintomas, headers=headers, timeout=30)
        response_temperaturas = requests.get(url_temperaturas, headers=headers, timeout=30)
        
        if response_sintomas.status_code == 200 and response_temperaturas.status_code == 200:
            df_sintomas = pd.read_csv(io.StringIO(response_sintomas.text))
            df_temperaturas = pd.read_csv(io.StringIO(response_temperaturas.text))
            resultados.append(("requests", df_sintomas, df_temperaturas))
    except Exception as e:
        pass
    
    # Estrategia 2: pd.read_csv con parámetros anti-caché
    try:
        t = int(time.time() * 1000)
        url_sintomas = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_sintomas}&_={t}"
        url_temperaturas = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_temperaturas}&_={t}"
        
        df_sintomas = pd.read_csv(url_sintomas, cache=False)
        df_temperaturas = pd.read_csv(url_temperaturas, cache=False)
        resultados.append(("pd_read_csv", df_sintomas, df_temperaturas))
    except Exception as e:
        pass
    
    # Si no hay resultados, error
    if not resultados:
        st.error("❌ No se pudo conectar con Google Sheets")
        return None
    
    # Usar el primer resultado exitoso
    _, df_sintomas, df_temperaturas = resultados[0]
    
    # PROCESAR DATOS
    def encontrar_columna_fecha(df):
        for col in df.columns:
            col_lower = col.lower().strip()
            if any(palabra in col_lower for palabra in ['fecha', 'date', 'tiempo']):
                return col
        return df.columns[0]

    def encontrar_columna_por_patron(df, patrones):
        for col in df.columns:
            col_lower = col.lower().strip()
            for patron in patrones:
                if patron.lower() in col_lower:
                    return col
        return None

    def estandarizar_columnas(df, mapeo):
        for nuevo_nombre, patrones in mapeo.items():
            col_existente = encontrar_columna_por_patron(df, patrones)
            if col_existente and col_existente != nuevo_nombre:
                df.rename(columns={col_existente: nuevo_nombre}, inplace=True)
        return df

    try:
        col_fecha_sintomas = encontrar_columna_fecha(df_sintomas)
        col_fecha_temp = encontrar_columna_fecha(df_temperaturas)

        mapeo_sintomas = {
            'Enfermos': ['enfermos', 'enfermo', 'enfermas'],
            'Muertos': ['muertos', 'muerto', 'muertas', 'fallecidos'],
            'Abortos': ['abortos', 'aborto', 'abortadas']
        }
        df_sintomas = estandarizar_columnas(df_sintomas, mapeo_sintomas)

        mapeo_temp = {
            'Temperaturas minimas  (°C)': ['temperatura minima', 'temp min', 'tmin'],
            'Vel. viento (Km/h)': ['viento', 'velocidad viento', 'wind'],
            'Precipitacion ': ['precipitacion', 'precipitación', 'lluvia']
        }
        df_temperaturas = estandarizar_columnas(df_temperaturas, mapeo_temp)

        df_sintomas['fecha'] = pd.to_datetime(df_sintomas[col_fecha_sintomas], errors='coerce')
        df_temperaturas['fecha'] = pd.to_datetime(df_temperaturas[col_fecha_temp], errors='coerce')

        df_sintomas = df_sintomas.dropna(subset=['fecha'])
        df_temperaturas = df_temperaturas.dropna(subset=['fecha'])

        columnas_sintomas = ['fecha'] + [col for col in ['Enfermos', 'Muertos', 'Abortos'] if col in df_sintomas.columns]
        columnas_temp = ['fecha'] + [col for col in ['Temperaturas minimas  (°C)', 'Vel. viento (Km/h)', 'Precipitacion '] if col in df_temperaturas.columns]
        
        df_sintomas = df_sintomas[columnas_sintomas]
        df_temperaturas = df_temperaturas[columnas_temp]

        df = pd.merge(df_sintomas, df_temperaturas, on='fecha', how='outer')
        df = df.sort_values(by='fecha').reset_index(drop=True)
        df = df.dropna(subset=['fecha'])

        columnas_numericas = ['Enfermos', 'Muertos', 'Abortos', 'Temperaturas minimas  (°C)', 
                            'Vel. viento (Km/h)', 'Precipitacion ']
        for col in columnas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                if col in ['Enfermos', 'Muertos', 'Abortos']:
                    df[col] = df[col].fillna(0)

        agg_dict = {}
        for col in ['Enfermos', 'Muertos', 'Abortos']:
            if col in df.columns:
                agg_dict[col] = 'sum'
        for col in ['Temperaturas minimas  (°C)', 'Precipitacion ', 'Vel. viento (Km/h)']:
            if col in df.columns:
                agg_dict[col] = 'mean'
        
        df = df.groupby('fecha').agg(agg_dict).reset_index()

        # Suavizado
        fecha_smooth = np.array([])
        enfermos_smooth = np.array([])
        
        df_filtrado = df[(df['Enfermos'] > 0) & (df['Enfermos'].notna())].copy()
        if len(df_filtrado) >= 3:
            try:
                df_filtrado = df_filtrado.sort_values('fecha')
                x_tiempo = df_filtrado['fecha'].map(pd.Timestamp.to_julian_date).values
                y = df_filtrado['Enfermos'].values
                
                _, unique_indices = np.unique(x_tiempo, return_index=True)
                x_tiempo = x_tiempo[unique_indices]
                y = y[unique_indices]
                
                if len(x_tiempo) >= 3:
                    x_suave = np.linspace(x_tiempo.min(), x_tiempo.max(), 300)
                    k = min(3, len(x_tiempo) - 1)
                    
                    spline = make_interp_spline(x_tiempo, y, k=k)
                    y_suave = spline(x_suave)
                    spline_extra = UnivariateSpline(x_tiempo, y, s=len(y)*1.5, k=k)
                    y_suave_extra = spline_extra(x_suave)
                    y_suave_final = 0.7 * y_suave_extra + 0.3 * y_suave
                    y_suave_final = np.clip(y_suave_final, 0.1, None)
                    
                    window_size = min(5, len(y_suave_final) // 10)
                    if window_size > 1:
                        y_suave_final = uniform_filter1d(y_suave_final, size=window_size, mode='nearest')
                    
                    fecha_smooth = pd.to_datetime(x_suave, unit='D', origin='julian')
                    enfermos_smooth = y_suave_final
            except:
                pass
        
        df.attrs['fecha_smooth'] = fecha_smooth
        df.attrs['enfermos_smooth'] = enfermos_smooth

        # Guardar metadatos
        df.attrs['timestamp_carga'] = datetime.datetime.now().strftime("%H:%M:%S")
        df.attrs['fecha_carga'] = datetime.datetime.now().strftime("%d/%m/%Y")
        df.attrs['hash'] = calcular_hash_datos(df)
        df.attrs['registros'] = len(df)

        return df

    except Exception as e:
        st.error(f"❌ Error al procesar datos: {e}")
        return None

# ============================================================
# FUNCIÓN PARA CREAR LA GRÁFICA
# ============================================================
def crear_grafica(df, images_paths, zoom_meses=None):
    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No se pudieron cargar los datos",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        return fig

    fecha_smooth = df.attrs.get('fecha_smooth', np.array([]))
    enfermos_smooth = df.attrs.get('enfermos_smooth', np.array([]))

    img_enferma = image_to_base64(images_paths.get('enferma', ''))
    img_muerta = image_to_base64(images_paths.get('muerta', ''))
    img_aborto = image_to_base64(images_paths.get('aborto', ''))

    fig = go.Figure()

    # PRECIPITACIÓN
    if 'Precipitacion ' in df.columns and not df['Precipitacion '].dropna().empty:
        fig.add_trace(go.Bar(
            x=df['fecha'],
            y=df['Precipitacion '],
            name='Precipitación',
            marker=dict(color='#87CEEB', opacity=0.5),
            yaxis='y2',
            hovertemplate='💧 %{y:02.0f} mm<extra></extra>'
        ))

    # TEMPERATURA
    if 'Temperaturas minimas  (°C)' in df.columns and not df['Temperaturas minimas  (°C)'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['fecha'],
            y=df['Temperaturas minimas  (°C)'],
            mode='lines+markers',
            name='Temperatura',
            line=dict(color='#2563EB', width=2.5),
            marker=dict(size=4, color='#2563EB'),
            hovertemplate='🌡️ %{y:.0f}°C<extra></extra>'
        ))

    # VIENTO
    if 'Vel. viento (Km/h)' in df.columns and not df['Vel. viento (Km/h)'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['fecha'],
            y=df['Vel. viento (Km/h)'],
            mode='lines',
            name='Viento',
            line=dict(color='#808080', width=2, dash='dash'),
            opacity=0.6,
            hovertemplate='💨 %{y:.0f} Km/h<extra></extra>'
        ))

    # ALPACAS ENFERMAS
    if len(enfermos_smooth) > 0:
        fig.add_trace(go.Scatter(
            x=fecha_smooth,
            y=enfermos_smooth,
            mode='lines',
            name='Alpacas enfermas',
            line=dict(color='#8B0000', width=2.5),
            opacity=0.8,
            fill='tozeroy',
            fillgradient=dict(
                type='vertical',
                colorscale=[[0, 'rgba(139, 0, 0, 0)'], [1, 'rgba(139, 0, 0, 0.15)']]
            ),
            yaxis='y2',
            hovertemplate='🦙 %{y:02.0f}<extra></extra>'
        ))

    # MUERTOS
    if 'Muertos' in df.columns:
        df_muertos = df[df['Muertos'] > 0].copy()
        if not df_muertos.empty:
            fig.add_trace(go.Scatter(
                x=df_muertos['fecha'],
                y=[0.2] * len(df_muertos),
                mode='markers',
                name='Muertas',
                marker=dict(size=12, color='#555555', line=dict(color='black', width=0.5)),
                yaxis='y2',
                customdata=df_muertos['Muertos'],
                hovertemplate='💀 %{customdata:02.0f}<extra></extra>'
            ))

    # ABORTOS
    if 'Abortos' in df.columns:
        df_abortos = df[df['Abortos'] > 0].copy()
        if not df_abortos.empty:
            fig.add_trace(go.Scatter(
                x=df_abortos['fecha'],
                y=[0.25] * len(df_abortos),
                mode='markers',
                name='Abortos',
                marker=dict(size=12, color='#1E90FF', line=dict(color='#87CEEB', width=1)),
                yaxis='y2',
                customdata=df_abortos['Abortos'],
                hovertemplate='⚠️ %{customdata:02.0f}<extra></extra>'
            ))

    # IMÁGENES
    images_plotly = []
    y_offset = 0.2

    if img_enferma is not None and len(enfermos_smooth) > 0:
        for idx in [0, -1]:
            images_plotly.append({
                'source': f"data:image/png;base64,{img_enferma}",
                'xref': 'x',
                'yref': 'y2',
                'x': fecha_smooth[idx],
                'y': float(enfermos_smooth[idx]),
                'sizex': 14,
                'sizey': 14,
                'xanchor': 'center',
                'yanchor': 'middle',
                'layer': 'above'
            })

    if img_muerta is not None and 'Muertos' in df.columns:
        df_muertos_varios = df[df['Muertos'] >= 3].copy()
        if not df_muertos_varios.empty:
            for _, row in df_muertos_varios.iterrows():
                images_plotly.append({
                    'source': f"data:image/png;base64,{img_muerta}",
                    'xref': 'x',
                    'yref': 'y2',
                    'x': row['fecha'],
                    'y': y_offset,
                    'sizex': 14,
                    'sizey': 14,
                    'xanchor': 'center',
                    'yanchor': 'middle',
                    'layer': 'above'
                })

    if img_aborto is not None and 'Abortos' in df.columns:
        df_abortos_pos = df[df['Abortos'] > 0].copy()
        if not df_abortos_pos.empty:
            for idx in [0, -1] if len(df_abortos_pos) > 1 else [0]:
                if idx < len(df_abortos_pos):
                    images_plotly.append({
                        'source': f"data:image/png;base64,{img_aborto}",
                        'xref': 'x',
                        'yref': 'y2',
                        'x': df_abortos_pos['fecha'].iloc[idx],
                        'y': y_offset,
                        'sizex': 14,
                        'sizey': 14,
                        'xanchor': 'center',
                        'yanchor': 'middle',
                        'layer': 'above'
                    })

    # RANGOS
    min_temp = df['Temperaturas minimas  (°C)'].min() if 'Temperaturas minimas  (°C)' in df.columns and not df['Temperaturas minimas  (°C)'].dropna().empty else 0
    max_temp = df['Temperaturas minimas  (°C)'].max() if 'Temperaturas minimas  (°C)' in df.columns and not df['Temperaturas minimas  (°C)'].dropna().empty else 10
    max_wind = df['Vel. viento (Km/h)'].max() if 'Vel. viento (Km/h)' in df.columns and not df['Vel. viento (Km/h)'].dropna().empty else 0

    y1_min = min_temp * 1.2 if min_temp < 0 else -5
    y1_max = max(max_temp, max_wind) * 1.3 if max(max_temp, max_wind) > 0 else 15

    max_y2 = 1
    if len(enfermos_smooth) > 0:
        max_y2 = max(max_y2, max(enfermos_smooth) * 1.3)
    if 'Muertos' in df.columns and not df['Muertos'].dropna().empty:
        max_y2 = max(max_y2, df['Muertos'].max() * 1.5)
    if 'Abortos' in df.columns and not df['Abortos'].dropna().empty:
        max_y2 = max(max_y2, df['Abortos'].max() * 1.5)
    if 'Precipitacion ' in df.columns and not df['Precipitacion '].dropna().empty:
        max_y2 = max(max_y2, df['Precipitacion '].max() * 1.1)
    max_y2 = max(max_y2, 2)

    # ZOOM
    if zoom_meses is None:
        año_datos = df['fecha'].max().year
        fecha_inicio_zoom = pd.Timestamp(year=año_datos, month=5, day=1)
        fecha_fin_zoom = pd.Timestamp(year=año_datos, month=8, day=31)
        
        if df[(df['fecha'] >= fecha_inicio_zoom) & (df['fecha'] <= fecha_fin_zoom)].empty:
            fecha_inicio_zoom = df['fecha'].max() - pd.DateOffset(months=6)
            fecha_fin_zoom = df['fecha'].max()
    else:
        fecha_fin_zoom = df['fecha'].max()
        fecha_inicio_zoom = df['fecha'].max() - pd.DateOffset(months=zoom_meses)
        if fecha_inicio_zoom < df['fecha'].min():
            fecha_inicio_zoom = df['fecha'].min()

    # TICKS
    fecha_ticks = pd.date_range(start=df['fecha'].min(), end=df['fecha'].max(), freq='MS')
    tick_labels = [fecha_espanol(f) for f in fecha_ticks]

    # ============================================================
    # LAYOUT
    # ============================================================
    fig.update_layout(
        hovermode='x unified',
        template='plotly_white',
        autosize=True,
        height=450,
        dragmode='pan',
        xaxis={
            'title': {'text': 'Meses', 'font': {'size': 11}},
            'type': 'date',
            'tickvals': fecha_ticks,
            'ticktext': tick_labels,
            'hoverformat': '%d de %B de %Y',
            'dtick': 'M1',
            'ticklabelmode': 'period',
            'tickfont': {'size': 9},
            'showgrid': True,
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'gridwidth': 0.5,
            'fixedrange': False,
            'range': [fecha_inicio_zoom, fecha_fin_zoom],
        },
        yaxis={
            'title': {'text': 'Temperatura (°C)', 'font': {'size': 11}},
            'range': [y1_min, y1_max],
            'tickformat': '.0f',
            'tickfont': {'size': 9},
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'gridwidth': 0.5,
            'zeroline': True,
            'zerolinecolor': 'rgba(128, 128, 128, 0.5)',
            'zerolinewidth': 1,
            'fixedrange': False,
            'side': 'left'
        },
        yaxis2={
            'title': {'text': 'Precipitación / Afectación', 'font': {'size': 11}},
            'range': [0, max_y2],
            'tickformat': 'd',
            'dtick': max(2, int(max_y2 / 8)),
            'tickfont': {'size': 9},
            'overlaying': 'y',
            'side': 'right',
            'gridcolor': 'rgba(200, 200, 200, 0.15)',
            'gridwidth': 0.3,
            'showgrid': True,
            'fixedrange': False
        },
        images=images_plotly,
        legend={
            'orientation': 'h',
            'x': 0.5,
            'y': -0.15,
            'xanchor': 'center',
            'yanchor': 'top',
            'bgcolor': 'rgba(255, 255, 255, 0.95)',
            'bordercolor': '#bdc3c7',
            'borderwidth': 1,
            'font': {'size': 9},
            'itemwidth': 25,
            'tracegroupgap': 5
        },
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin={'t': 15, 'b': 20, 'l': 40, 'r': 50}
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=0.8, opacity=0.4)

    return fig

# ============================================================
# MAIN - CON SISTEMA ROBUSTO
# ============================================================
def main():
    # Inicializar session_state
    if 'ultima_actualizacion' not in st.session_state:
        st.session_state.ultima_actualizacion = None
    if 'hash_anterior' not in st.session_state:
        st.session_state.hash_anterior = None
    if 'datos_cargados' not in st.session_state:
        st.session_state.datos_cargados = None
    
    # Obtener timestamp actual
    now = datetime.datetime.now()
    hora_actual = now.strftime("%H:%M:%S")
    fecha_actual = now.strftime("%d/%m/%Y")
    
    # Mostrar timestamp
    st.markdown(f"""
    ## 🦙 Monitoreo Diario
    <div class="timestamp"><span></span> Datos cargados: {fecha_actual} {hora_actual}</div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("### 🎛️ Controles")
        st.markdown("**Seleccionar período:**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📅 1 Mes", use_container_width=True):
                st.session_state.zoom_periodo = 1
                st.rerun()
            if st.button("📅 6 Meses", use_container_width=True):
                st.session_state.zoom_periodo = 6
                st.rerun()
            if st.button("📅 Todo", use_container_width=True):
                st.session_state.zoom_periodo = None
                st.rerun()
        with col2:
            if st.button("📅 3 Meses", use_container_width=True):
                st.session_state.zoom_periodo = 3
                st.rerun()
            if st.button("📅 1 Año", use_container_width=True):
                st.session_state.zoom_periodo = 12
                st.rerun()
        
        st.markdown("---")
        st.markdown("**🖱️ Interactuar:**")
        st.markdown("- Arrastra para deslizar")
        st.markdown("- Rueda para hacer zoom")
        
        st.markdown("---")
        
        # Estado de la actualización
        if st.session_state.ultima_actualizacion:
            st.caption(f"🔄 Última recarga: {st.session_state.ultima_actualizacion}")
        else:
            st.caption("🔄 Cargando datos...")
        
        # Botón de actualización forzada
        if st.button("🔄 Actualizar ahora", use_container_width=True):
            st.session_state.ultima_actualizacion = hora_actual
            st.rerun()
        
        st.markdown("---")
        st.caption("⏱️ Auto-actualización cada 30 segundos")

    GOOGLE_SHEETS_ID = '11UWULdTZL2tKKpeGRETXOHvQt_3jHxIMgap2lfkDpro'
    SHEET_NAME_SINTOMAS = 'sintomas'
    SHEET_NAME_TEMPERATURAS = 'temperaturas'

    os.makedirs('imagenes', exist_ok=True)
    
    IMAGES = {
        'enferma': 'imagenes/enferma.png',
        'muerta': 'imagenes/muerta.png',
        'aborto': 'imagenes/aborto.png'
    }

    zoom_meses = st.session_state.get('zoom_periodo', None)

    with st.spinner('🔄 Cargando datos desde Google Sheets...'):
        df = cargar_datos_robusto(GOOGLE_SHEETS_ID, SHEET_NAME_SINTOMAS, SHEET_NAME_TEMPERATURAS)

    if df is not None and not df.empty:
        # Verificar si los datos cambiaron
        hash_actual = df.attrs.get('hash', '')
        if st.session_state.hash_anterior is None:
            st.session_state.hash_anterior = hash_actual
        elif st.session_state.hash_anterior != hash_actual:
            st.session_state.hash_anterior = hash_actual
            # Mostrar notificación de cambio
            st.success("🔄 ¡Datos actualizados!")
        
        st.session_state.ultima_actualizacion = df.attrs.get('timestamp_carga', hora_actual)
        
        with st.spinner('📊 Generando gráfica...'):
            fig = crear_grafica(df, IMAGES, zoom_meses)

        if fig is not None:
            st.plotly_chart(
                fig, 
                use_container_width=True,
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['toImage', 'sendDataToCloud', 'zoomIn2d', 'zoomOut2d'],
                    'displaylogo': False,
                    'scrollZoom': True,
                    'responsive': True,
                }
            )

            with st.expander("📊 Ver estadísticas"):
                col1, col2, col3 = st.columns(3)
                if 'Enfermos' in df.columns and not df['Enfermos'].dropna().empty:
                    col1.metric("🦙 Total Enfermos", f"{df['Enfermos'].sum():.0f}")
                if 'Muertos' in df.columns and not df['Muertos'].dropna().empty:
                    col2.metric("💀 Total Muertos", f"{df['Muertos'].sum():.0f}")
                if 'Abortos' in df.columns and not df['Abortos'].dropna().empty:
                    col3.metric("⚠️ Total Abortos", f"{df['Abortos'].sum():.0f}")
                
                # Mostrar metadatos
                st.caption(f"📊 Registros: {df.attrs.get('registros', 0)} | Hash: {df.attrs.get('hash', '')[:8]}...")

            st.success("✅ ¡Gráfica cargada exitosamente!")
        else:
            st.error("❌ Error al generar la gráfica")
    else:
        st.error("❌ No se pudieron cargar los datos")

if __name__ == "__main__":
    main()
