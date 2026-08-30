# app.py - VERSIÓN OPTIMIZADA PARA PC Y MÓVIL
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import make_interp_spline, UnivariateSpline
from scipy.ndimage import uniform_filter1d
import warnings
import base64
import os

warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Gráfica Alpacas Interactiva",
    page_icon="🦙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# DETECTAR DISPOSITIVO (PC vs MÓVIL)
# ============================================================
def is_mobile():
    """Detecta si el usuario está en un dispositivo móvil"""
    try:
        # Streamlit no tiene detección nativa, usamos el ancho de pantalla
        # Por defecto asumimos que es móvil si no se puede detectar
        return True
    except:
        return False

# ============================================================
# CSS OPTIMIZADO PARA PC Y MÓVIL
# ============================================================
def inject_custom_css():
    """Inyecta CSS optimizado para PC y móvil"""
    st.markdown("""
    <style>
        /* === RESET Y CONFIGURACIÓN BASE === */
        .main .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0rem !important;
            max-width: 100% !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        h1, h2, h3 {
            margin-top: 0rem !important;
            margin-bottom: 0rem !important;
        }
        
        header { display: none !important; }
        footer { display: none !important; }
        
        /* === MEJORAS PARA MÓVIL === */
        @media (max-width: 768px) {
            .main .block-container {
                padding-left: 0.2rem !important;
                padding-right: 0.2rem !important;
                padding-top: 0.2rem !important;
            }
            
            /* Botones más grandes y táctiles en móvil */
            .stButton > button {
                width: 100% !important;
                min-height: 44px !important;
                font-size: 14px !important;
                padding: 8px 12px !important;
                border-radius: 8px !important;
            }
            
            /* Sidebar más ancha en móvil */
            .css-1d391kg, .css-1lcbmhc {
                width: 280px !important;
                min-width: 280px !important;
            }
            
            /* Títulos más pequeños en móvil */
            h2 {
                font-size: 1.2rem !important;
            }
            
            /* Gráfica ocupa más espacio */
            .stPlotlyChart > div {
                margin-top: -5px !important;
                height: 400px !important;
            }
            
            /* Expander más compacto */
            .streamlit-expanderHeader {
                font-size: 14px !important;
                padding: 8px !important;
            }
            
            /* Métricas más compactas */
            [data-testid="metric-container"] {
                padding: 8px !important;
                margin: 0 !important;
            }
            
            [data-testid="metric-container"] label {
                font-size: 12px !important;
            }
            
            [data-testid="metric-container"] div {
                font-size: 18px !important;
            }
        }
        
        /* === PC === */
        @media (min-width: 769px) {
            .stPlotlyChart > div {
                margin-top: -10px !important;
                height: 750px !important;
            }
            
            .stButton > button {
                min-height: 36px !important;
                font-size: 14px !important;
            }
        }
        
        /* === OCULTAR ELEMENTOS NO DESEADOS === */
        .rangeselector { display: none !important; }
        
        /* === MEJORAR LEGIBILIDAD === */
        .stMarkdown {
            font-size: 14px !important;
        }
        
        /* === SCROLLBAR MEJORADA === */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 3px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 3px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        
        /* === TOOLTIP EN MÓVIL === */
        .hoverlayer .hovertext {
            font-size: 12px !important;
        }
        
        /* === SIDEBAR MEJORADA === */
        .css-1d391kg, .css-1lcbmhc {
            background-color: #f8f9fa !important;
        }
        
        /* === BOTONES DE PERIODO === */
        .period-buttons {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 4px;
            margin-bottom: 8px;
        }
        
        @media (max-width: 768px) {
            .period-buttons {
                grid-template-columns: 1fr 1fr;
                gap: 6px;
            }
        }
    </style>
    """, unsafe_allow_html=True)

# ============================================================
# DICCIONARIO DE MESES Y DÍAS EN ESPAÑOL
# ============================================================
MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
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
# FUNCIONES DE PROCESAMIENTO
# ============================================================
@st.cache_data(ttl=3600)
def cargar_datos(sheet_id, sheet_sintomas, sheet_temperaturas):
    """Carga datos desde Google Sheets con caché"""
    try:
        url_sintomas = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_sintomas}"
        url_temperaturas = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_temperaturas}"
        
        df_sintomas = pd.read_csv(url_sintomas)
        df_temperaturas = pd.read_csv(url_temperaturas)

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

        return df

    except Exception as e:
        st.error(f"❌ Error al cargar datos: {e}")
        return None

# ============================================================
# FUNCIÓN PARA CREAR LA GRÁFICA (OPTIMIZADA)
# ============================================================
def crear_grafica(df, images_paths, zoom_meses=None, is_mobile_device=False):
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
            hovertemplate='<b>💧 Precipitación:</b> %{y:02.0f} mm<extra></extra>'
        ))

    # TEMPERATURA
    if 'Temperaturas minimas  (°C)' in df.columns and not df['Temperaturas minimas  (°C)'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['fecha'],
            y=df['Temperaturas minimas  (°C)'],
            mode='lines+markers',
            name='Temperatura mínima',
            line=dict(color='#2563EB', width=2.5),
            marker=dict(size=4 if not is_mobile_device else 6, color='#2563EB'),
            opacity=0.9,
            hovertemplate='<b>🌡️ Temperatura mínima:</b> %{y:.0f} °C<extra></extra>'
        ))

    # VIENTO
    if 'Vel. viento (Km/h)' in df.columns and not df['Vel. viento (Km/h)'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['fecha'],
            y=df['Vel. viento (Km/h)'],
            mode='lines',
            name='Viento',
            line=dict(color='#808080', width=2 if not is_mobile_device else 1.5, dash='dash'),
            opacity=0.6,
            hovertemplate='<b>💨 Viento:</b> %{y:.0f} Km/h<extra></extra>'
        ))

    # ALPACAS ENFERMAS
    if len(enfermos_smooth) > 0:
        fig.add_trace(go.Scatter(
            x=fecha_smooth,
            y=enfermos_smooth,
            mode='lines',
            name='Alpacas enfermas',
            line=dict(color='#8B0000', width=2.5 if not is_mobile_device else 2),
            opacity=0.8,
            fill='tozeroy',
            fillgradient=dict(
                type='vertical',
                colorscale=[[0, 'rgba(139, 0, 0, 0)'], [1, 'rgba(139, 0, 0, 0.15)']]
            ),
            yaxis='y2',
            hovertemplate='<b>🦙 Alpacas enfermas:</b> %{y:02.0f}<extra></extra>'
        ))

    # MUERTOS
    if 'Muertos' in df.columns:
        df_muertos = df[df['Muertos'] > 0].copy()
        if not df_muertos.empty:
            fig.add_trace(go.Scatter(
                x=df_muertos['fecha'],
                y=[0.2] * len(df_muertos),
                mode='markers',
                name='Alpacas muertas',
                marker=dict(
                    size=12 if not is_mobile_device else 16,
                    color='#555555',
                    line=dict(color='black', width=0.5)
                ),
                yaxis='y2',
                customdata=df_muertos['Muertos'],
                hovertemplate='<b>💀 Alpacas muertas:</b> %{customdata:02.0f}<extra></extra>'
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
                marker=dict(
                    size=12 if not is_mobile_device else 16,
                    color='#1E90FF',
                    line=dict(color='#87CEEB', width=1)
                ),
                yaxis='y2',
                customdata=df_abortos['Abortos'],
                hovertemplate='<b>⚠️ Abortos:</b> %{customdata:02.0f}<extra></extra>'
            ))

    # IMÁGENES (optimizado para móvil)
    images_plotly = []
    y_offset = 0.2
    img_size = 14 if not is_mobile_device else 20

    if img_enferma is not None and len(enfermos_smooth) > 0:
        # Solo mostrar en puntos clave para móvil
        indices = [0, len(fecha_smooth)//2, -1] if is_mobile_device else [0, -1]
        for idx in indices:
            if 0 <= idx < len(fecha_smooth):
                images_plotly.append({
                    'source': f"data:image/png;base64,{img_enferma}",
                    'xref': 'x',
                    'yref': 'y2',
                    'x': fecha_smooth[idx],
                    'y': float(enfermos_smooth[idx]),
                    'sizex': img_size,
                    'sizey': img_size,
                    'xanchor': 'center',
                    'yanchor': 'middle',
                    'layer': 'above'
                })

    if img_muerta is not None and 'Muertos' in df.columns:
        df_muertos_varios = df[df['Muertos'] >= 3].copy()
        if not df_muertos_varios.empty:
            # Limitar cantidad de imágenes en móvil
            max_images = 3 if is_mobile_device else len(df_muertos_varios)
            df_muertos_limit = df_muertos_varios.head(max_images)
            for _, row in df_muertos_limit.iterrows():
                images_plotly.append({
                    'source': f"data:image/png;base64,{img_muerta}",
                    'xref': 'x',
                    'yref': 'y2',
                    'x': row['fecha'],
                    'y': y_offset,
                    'sizex': img_size,
                    'sizey': img_size,
                    'xanchor': 'center',
                    'yanchor': 'middle',
                    'layer': 'above'
                })

    if img_aborto is not None and 'Abortos' in df.columns:
        df_abortos_pos = df[df['Abortos'] > 0].copy()
        if not df_abortos_pos.empty:
            max_images = 3 if is_mobile_device else len(df_abortos_pos)
            df_abortos_limit = df_abortos_pos.head(max_images)
            for _, row in df_abortos_limit.iterrows():
                images_plotly.append({
                    'source': f"data:image/png;base64,{img_aborto}",
                    'xref': 'x',
                    'yref': 'y2',
                    'x': row['fecha'],
                    'y': y_offset,
                    'sizex': img_size,
                    'sizey': img_size,
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

    # ZOOM INICIAL
    fecha_inicio = df['fecha'].min()
    fecha_fin = df['fecha'].max()
    
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

    # TICKS (menos ticks en móvil)
    if is_mobile_device:
        # Menos ticks en móvil para mejor legibilidad
        num_ticks = 6
        date_range = df['fecha'].max() - df['fecha'].min()
        if date_range.days > 180:
            freq = 'MS'  # Mensual
        else:
            freq = 'MS'  # Mensual
        fecha_ticks = pd.date_range(start=df['fecha'].min(), end=df['fecha'].max(), freq=freq)
        # Tomar solo algunos ticks para móvil
        if len(fecha_ticks) > 8:
            step = max(1, len(fecha_ticks) // 8)
            fecha_ticks = fecha_ticks[::step]
    else:
        fecha_ticks = pd.date_range(start=df['fecha'].min(), end=df['fecha'].max(), freq='MS')
    
    tick_labels = [fecha_espanol(f) for f in fecha_ticks]

    # Ajustar altura según dispositivo
    chart_height = 400 if is_mobile_device else 750

    # LAYOUT OPTIMIZADO
    fig.update_layout(
        hovermode='x unified',
        template='plotly_white',
        height=chart_height,
        dragmode='pan',
        xaxis={
            'title': {'text': 'Meses' if not is_mobile_device else '', 'font': {'size': 11 if is_mobile_device else 13, 'color': '#34495e'}},
            'type': 'date',
            'tickvals': fecha_ticks,
            'ticktext': tick_labels,
            'hoverformat': '%d de %B de %Y',
            'dtick': 'M1',
            'ticklabelmode': 'period',
            'tickfont': {'size': 9 if is_mobile_device else 11, 'color': '#2c3e50'},
            'showgrid': True,
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'gridwidth': 0.5,
            'fixedrange': False,
            'range': [fecha_inicio_zoom, fecha_fin_zoom],
        },
        yaxis={
            'title': {'text': 'Temperatura mínima (°C)' if not is_mobile_device else 'T°C', 'font': {'size': 11 if is_mobile_device else 13, 'color': '#34495e'}},
            'range': [y1_min, y1_max],
            'tickformat': '.1f',
            'tickfont': {'size': 9 if is_mobile_device else 11, 'color': '#2c3e50'},
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'gridwidth': 0.5,
            'zeroline': True,
            'zerolinecolor': 'rgba(128, 128, 128, 0.5)',
            'zerolinewidth': 1,
            'fixedrange': False,
            'side': 'left'
        },
        yaxis2={
            'title': {'text': 'Precipitación / Afectación' if not is_mobile_device else 'Afectación', 
                     'font': {'size': 11 if is_mobile_device else 13, 'color': '#34495e'}},
            'range': [0, max_y2],
            'tickformat': 'd',
            'dtick': max(2, int(max_y2 / 8)),
            'tickfont': {'size': 9 if is_mobile_device else 11, 'color': '#2c3e50'},
            'overlaying': 'y',
            'side': 'right',
            'gridcolor': 'rgba(200, 200, 200, 0.15)',
            'gridwidth': 0.3,
            'showgrid': True,
            'fixedrange': False
        },
        images=images_plotly,
        legend={
            'orientation': 'h' if not is_mobile_device else 'h',
            'x': 0.5,
            'y': -0.15 if not is_mobile_device else -0.25,
            'xanchor': 'center',
            'yanchor': 'top',
            'bgcolor': 'rgba(255, 255, 255, 0.95)',
            'bordercolor': '#bdc3c7',
            'borderwidth': 1,
            'font': {'size': 10 if is_mobile_device else 11, 'color': '#2c3e50'},
            'itemwidth': 30 if not is_mobile_device else 20,
            'tracegroupgap': 5
        },
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin={'t': 20 if is_mobile_device else 30, 
                'b': 20 if is_mobile_device else 30, 
                'l': 30 if is_mobile_device else 50, 
                'r': 40 if is_mobile_device else 60}
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=0.8, opacity=0.4)

    return fig

# ============================================================
# MAIN - APLICACIÓN STREAMLIT
# ============================================================
def main():
    # Inyectar CSS
    inject_custom_css()
    
    # Título
    st.markdown("## 🦙 Monitoreo Diaria - Temperatura, Precipitación y Afectación de Alpacas")
    
    # ============================================================
    # BARRA LATERAL - CONTROLES OPTIMIZADOS
    # ============================================================
    with st.sidebar:
        st.markdown("### 🎛️ Controles")
        
        st.markdown("**Seleccionar período:**")
        
        # Botones en grid para mejor organización en móvil
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📅 1 Mes", use_container_width=True):
                st.session_state.zoom_periodo = 1
            if st.button("📅 3 Meses", use_container_width=True):
                st.session_state.zoom_periodo = 3
            if st.button("📅 Todo", use_container_width=True):
                st.session_state.zoom_periodo = None
        
        with col2:
            if st.button("📅 6 Meses", use_container_width=True):
                st.session_state.zoom_periodo = 6
            if st.button("📅 1 Año", use_container_width=True):
                st.session_state.zoom_periodo = 12
        
        st.markdown("---")
        st.markdown("**🖱️ Cómo interactuar:**")
        
        # Ayuda adaptada a móvil
        st.markdown("""
        - **Deslizar**: Arrastra el mouse/dedo ← →
        - **Zoom**: Rueda del mouse/pellizcar
        - **Ver valores**: Pasa el cursor/toca sobre puntos
        """)
        
        st.markdown("---")
        if st.button("🔄 Actualizar datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # CONFIGURACIÓN
    GOOGLE_SHEETS_ID = '11UWULdTZL2tKKpeGRETXOHvQt_3jHxIMgap2lfkDpro'
    SHEET_NAME_SINTOMAS = 'sintomas'
    SHEET_NAME_TEMPERATURAS = 'temperaturas'

    # IMÁGENES
    os.makedirs('imagenes', exist_ok=True)
    
    IMAGES = {
        'enferma': 'imagenes/enferma.png',
        'muerta': 'imagenes/muerta.png',
        'aborto': 'imagenes/aborto.png'
    }

    # Obtener zoom seleccionado
    zoom_meses = st.session_state.get('zoom_periodo', None)

    # Cargar datos
    with st.spinner('🔄 Cargando datos desde Google Sheets...'):
        df = cargar_datos(GOOGLE_SHEETS_ID, SHEET_NAME_SINTOMAS, SHEET_NAME_TEMPERATURAS)

    if df is not None and not df.empty:
        with st.spinner('📊 Generando gráfica interactiva...'):
            # Detectar si es móvil (por defecto asumimos que puede ser móvil)
            # Streamlit no tiene detección nativa, pero el CSS se encargará del responsive
            fig = crear_grafica(df, IMAGES, zoom_meses, is_mobile_device=False)
            
            # También creamos versión para móvil (se usará según CSS)
            # La gráfica se adaptará automáticamente gracias al CSS responsive

        if fig is not None:
            # Configuración de la barra de herramientas adaptada
            mode_bar_buttons = [
                'zoom2d',
                'pan2d',
                'select2d',
                'lasso2d',
                'zoomIn2d',
                'zoomOut2d',
                'autoScale2d',
                'resetScale2d',
                'toImage'
            ]
            
            # Mostrar gráfica
            st.plotly_chart(fig, use_container_width=True, config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['sendDataToCloud'],
                'displaylogo': False,
                'scrollZoom': True,
                'responsive': True,
                'modeBarButtonsToAdd': mode_bar_buttons
            })

            # ESTADÍSTICAS (optimizadas para móvil)
            with st.expander("📊 Ver estadísticas de los datos"):
                # Métricas en columnas que se adaptan
                cols = st.columns(3)
                
                if 'Enfermos' in df.columns and not df['Enfermos'].dropna().empty:
                    cols[0].metric("🦙 Total Enfermos", f"{df['Enfermos'].sum():.0f}")
                if 'Muertos' in df.columns and not df['Muertos'].dropna().empty:
                    cols[1].metric("💀 Total Muertos", f"{df['Muertos'].sum():.0f}")
                if 'Abortos' in df.columns and not df['Abortos'].dropna().empty:
                    cols[2].metric("⚠️ Total Abortos", f"{df['Abortos'].sum():.0f}")

                # Tabla con scroll horizontal en móvil
                st.dataframe(df, use_container_width=True, height=300)

            st.success("✅ ¡Gráfica cargada exitosamente!")
        else:
            st.error("❌ Error al generar la gráfica")
    else:
        st.error("❌ No se pudieron cargar los datos")

if __name__ == "__main__":
    main()
