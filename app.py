# app.py - VERSIÓN SIGUAIRO ( AUTO-REFRESH 60s y ESTADÍSTICAS DESPLEGABLES)
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import warnings
import base64
import os

warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Gráfica afectación alpaca",
    page_icon="🦙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# ESTILOS RESPONSIVE - LOGO SENAMHI
# ============================================================
st.markdown("""
<style>
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
    
    .stPlotlyChart > div {
        margin-top: -10px !important;
        width: 100% !important;
    }
    
    .rangeselector { display: none !important; }
    
    .logo-senamhi {
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 999999;
        width: 80px;
        height: auto;
        opacity: 0.9;
        transition: all 0.3s ease;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        background: rgba(255, 255, 255, 0.85);
        padding: 4px;
    }
    
    .logo-senamhi:hover {
        opacity: 1;
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    
    @media only screen and (max-width: 768px) {
        .logo-senamhi {
            width: 55px;
            top: 5px;
            left: 5px;
            padding: 3px;
            border-radius: 6px;
        }
        
        .main .block-container {
            padding-left: 0.2rem !important;
            padding-right: 0.2rem !important;
            padding-top: 0.2rem !important;
        }
        
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1rem !important; }
        
        .stButton button {
            font-size: 14px !important;
            padding: 8px 12px !important;
            min-height: 44px !important;
        }
        
        .css-1d391kg { width: 280px !important; }
        
        .stMetric { font-size: 14px !important; }
        .stMetric label { font-size: 12px !important; }
        .stMetric .stMetricValue { font-size: 18px !important; }
        
        .stDataFrame { font-size: 12px !important; }
        .stDataFrame table { font-size: 11px !important; }
        
        .stSpinner > div { font-size: 14px !important; }
        .row-widget.stColumns { gap: 0.2rem !important; }
    }
    
    @media only screen and (min-width: 769px) and (max-width: 1024px) {
        .logo-senamhi {
            width: 65px;
            top: 8px;
            left: 8px;
        }
        
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        .stButton button {
            font-size: 15px !important;
            padding: 10px 16px !important;
        }
    }
    
    @media only screen and (min-width: 1025px) {
        .logo-senamhi {
            width: 80px;
            top: 10px;
            left: 10px;
        }
        
        .main .block-container {
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1400px !important;
            margin: 0 auto !important;
        }
    }
    
    .js-plotly-plot .plotly .scrollbar {
        display: none !important;
    }
    
    body {
        font-size: 16px !important;
        line-height: 1.5 !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# MOSTRAR LOGO SENAMHI
# ============================================================
def mostrar_logo_senamhi():
    ruta_logo = "fotosenamhi.png"
    
    if os.path.exists(ruta_logo):
        try:
            with open(ruta_logo, "rb") as f:
                imagen_base64 = base64.b64encode(f.read()).decode()
            
            st.markdown(f"""
            <img src="data:image/png;base64,{imagen_base64}" 
                 class="logo-senamhi" 
                 alt="Logo SENAMHI"
                 title="SENAMHI - Servicio Nacional de Meteorología e Hidrología">
            """, unsafe_allow_html=True)
        except:
            pass

# ============================================================
# DICCIONARIO DE MESES
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
@st.cache_data(ttl=10)
def cargar_datos(sheet_id, sheet_sintomas, sheet_temperaturas):
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

        # FILTRO: ELIMINAR FECHAS FUTURAS
        fecha_actual = pd.Timestamp.now().normalize()
        df = df[df['fecha'] <= fecha_actual].copy()
        
        if df.empty:
            st.warning("⚠️ No se encontraron datos con fechas válidas (no futuras)")
            return None

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

        return df

    except Exception as e:
        st.error(f"❌ Error al cargar datos: {e}")
        return None

# ============================================================
# FUNCIÓN PARA CREAR LA GRÁFICA - FECHA ÚNICA
# ============================================================
def crear_grafica(df, images_paths, zoom_meses=None, es_movil=False):
    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No se pudieron cargar los datos",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        return fig

    img_enferma = image_to_base64(images_paths.get('enferma', ''))
    img_muerta = image_to_base64(images_paths.get('muerta', ''))
    img_aborto = image_to_base64(images_paths.get('aborto', ''))

    fig = go.Figure()

    # ============================================================
    # PRECIPITACIÓN
    # ============================================================
    if 'Precipitacion ' in df.columns and not df['Precipitacion '].dropna().empty:
        fig.add_trace(go.Bar(
            x=df['fecha'],
            y=df['Precipitacion '],
            name='Precipitación',
            marker=dict(color='#87CEEB', opacity=0.5),
            yaxis='y2',
            hoverinfo='skip'
        ))

    # ============================================================
    # TEMPERATURA
    # ============================================================
    if 'Temperaturas minimas  (°C)' in df.columns and not df['Temperaturas minimas  (°C)'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['fecha'],
            y=df['Temperaturas minimas  (°C)'],
            mode='lines+markers',
            name='Temperatura mínima',
            line=dict(color='#0000FF', width=3.0),
            marker=dict(size=4, color='#2563EB'),
            opacity=0.9,
            hoverinfo='skip'
        ))

    # ============================================================
    # VIENTO
    # ============================================================
    if 'Vel. viento (Km/h)' in df.columns and not df['Vel. viento (Km/h)'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['fecha'],
            y=df['Vel. viento (Km/h)'],
            mode='lines',
            name='Viento',
            line=dict(color='#808080', width=2, dash='dash'),
            opacity=0.6,
            hoverinfo='skip'
        ))

    # ============================================================
    # ALPACAS ENFERMAS - LÍNEA QUE SE CORTA AL FINAL
    # ============================================================
    
    # En lugar de anular todos los ceros, solo anulamos los ceros que están al final.
    # Primero rellenamos con 0 los días sin registro para que la línea sea continua.
    df_linea = df.copy()
    df_linea['Enfermos_plot'] = df_linea['Enfermos'].fillna(0)
    
    # Detectamos el índice del último valor mayor a 0
    idx_ultimo_positivo = df_linea[df_linea['Enfermos_plot'] > 0].index.max()
    
    # Si hay valores positivos, cortamos la línea después de ese punto
    if pd.notna(idx_ultimo_positivo):
        df_linea.loc[df_linea.index > idx_ultimo_positivo, 'Enfermos_plot'] = None
        
    # Agregamos el trazado. Plotly cortará donde haya None (al final).
    fig.add_trace(go.Scatter(
        x=df_linea['fecha'],
        y=df_linea['Enfermos_plot'],
        mode='lines', # Solo línea
        name='Alpacas enfermas',
        line=dict(
            color='#8B0000', 
            width=2.5,
            shape='spline',       # <--- Efecto de ola de Excel
            smoothing=1.0         # <--- Nivel de suavizado
        ),
        opacity=0.8,
        fill='tozeroy',
        fillgradient=dict(
            type='vertical',
            colorscale=[[0, 'rgba(139, 0, 0, 0)'], [1, 'rgba(139, 0, 0, 0.15)']]
        ),
        yaxis='y2',
        hoverinfo='skip',
        showlegend=True
    ))

    # ============================================================
    # ALPACAS MUERTAS
    # ============================================================
    if 'Muertos' in df.columns:
        df_muertos = df[df['Muertos'] > 0].copy()
        if not df_muertos.empty:
            fig.add_trace(go.Scatter(
                x=df_muertos['fecha'],
                y=[0.2] * len(df_muertos),
                mode='markers',
                name='Alpacas muertas',
                marker=dict(size=12, color='#555555', line=dict(color='black', width=0.5)),
                yaxis='y2',
                customdata=df_muertos['Muertos'],
                hoverinfo='skip'
            ))

    # ============================================================
    # ABORTOS
    # ============================================================
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
                hoverinfo='skip'
            ))

    # ============================================================
    # TRACE INVISIBLE CON HOVER Y FECHA ÚNICA
    # ============================================================
    df_hover = df.copy()
    
    for col in ['Precipitacion ', 'Temperaturas minimas  (°C)', 'Vel. viento (Km/h)', 
                'Enfermos', 'Muertos', 'Abortos']:
        if col not in df_hover.columns:
            df_hover[col] = np.nan
    
    hover_texts = []
    for _, row in df_hover.iterrows():
        texto = f"<b>📅 {row['fecha'].strftime('%d/%m/%Y')}</b><br>"
        
        if pd.notna(row['Precipitacion ']):
            texto += f"<b>💧 Precipitación:</b> {row['Precipitacion ']:.0f} mm<br>"
        if pd.notna(row['Temperaturas minimas  (°C)']):
            texto += f"<b>🌡️ Temperatura mínima:</b> {row['Temperaturas minimas  (°C)']:.1f} °C<br>"
        if pd.notna(row['Vel. viento (Km/h)']):
            texto += f"<b>💨 Viento:</b> {row['Vel. viento (Km/h)']:.0f} Km/h<br>"
        if pd.notna(row['Enfermos']) and row['Enfermos'] > 0:
            texto += f"<b>🦙 Alpacas enfermas:</b> {row['Enfermos']:.0f}<br>"
        if pd.notna(row['Muertos']) and row['Muertos'] > 0:
            texto += f"<b>💀 Alpacas muertas:</b> {row['Muertos']:.0f}<br>"
        if pd.notna(row['Abortos']) and row['Abortos'] > 0:
            texto += f"<b>⚠️ Abortos:</b> {row['Abortos']:.0f}<br>"
        
        hover_texts.append(texto)
    
    fig.add_trace(go.Scatter(
        x=df_hover['fecha'],
        y=[10] * len(df_hover),
        mode='markers',
        name='',
        marker=dict(size=0.1, color='rgba(0,0,0,0)', opacity=0),
        yaxis='y2',
        showlegend=False,
        hoverinfo='text',
        text=hover_texts,
        hoverlabel=dict(
            bgcolor='rgba(255, 255, 255, 0.75)',
            font_size=13,
            font_color='#2c3e50',
            bordercolor='rgba(189, 195, 199, 0.5)'
        )
    ))

    # ============================================================
    # IMÁGENES PEQUEÑAS (SOLO PC)
    # ============================================================
    images_plotly = []
    y_offset = 0.2

    if not es_movil:
        if img_enferma is not None and 'Enfermos' in df.columns:
            df_enferma_pos = df[df['Enfermos'] > 0].copy()
            if not df_enferma_pos.empty:
                for idx in [0, -1]:
                    if idx < len(df_enferma_pos):
                        images_plotly.append({
                            'source': f"data:image/png;base64,{img_enferma}",
                            'xref': 'x', 'yref': 'y2',
                            'x': df_enferma_pos['fecha'].iloc[idx], 'y': float(df_enferma_pos['Enfermos'].iloc[idx]),
                            'sizex': 8, 'sizey': 8,
                            'xanchor': 'center', 'yanchor': 'middle', 'layer': 'above'
                        })

        if img_muerta is not None and 'Muertos' in df.columns:
            df_muertos_varios = df[df['Muertos'] >= 3].copy()
            if not df_muertos_varios.empty:
                for _, row in df_muertos_varios.iterrows():
                    images_plotly.append({
                        'source': f"data:image/png;base64,{img_muerta}",
                        'xref': 'x', 'yref': 'y2',
                        'x': row['fecha'], 'y': y_offset,
                        'sizex': 8, 'sizey': 8,
                        'xanchor': 'center', 'yanchor': 'middle', 'layer': 'above'
                    })

        if img_aborto is not None and 'Abortos' in df.columns:
            df_abortos_pos = df[df['Abortos'] > 0].copy()
            if not df_abortos_pos.empty:
                for idx in [0, -1] if len(df_abortos_pos) > 1 else [0]:
                    if idx < len(df_abortos_pos):
                        images_plotly.append({
                            'source': f"data:image/png;base64,{img_aborto}",
                            'xref': 'x', 'yref': 'y2',
                            'x': df_abortos_pos['fecha'].iloc[idx], 'y': y_offset,
                            'sizex': 8, 'sizey': 8,
                            'xanchor': 'center', 'yanchor': 'middle', 'layer': 'above'
                        })

    # ============================================================
    # RANGOS Y VISTA INICIAL
    # ============================================================
    min_temp = df['Temperaturas minimas  (°C)'].min() if 'Temperaturas minimas  (°C)' in df.columns and not df['Temperaturas minimas  (°C)'].dropna().empty else 0
    max_temp = df['Temperaturas minimas  (°C)'].max() if 'Temperaturas minimas  (°C)' in df.columns and not df['Temperaturas minimas  (°C)'].dropna().empty else 10
    max_wind = df['Vel. viento (Km/h)'].max() if 'Vel. viento (Km/h)' in df.columns and not df['Vel. viento (Km/h)'].dropna().empty else 0

    y1_min = min_temp * 1.2 if min_temp < 0 else -5
    y1_max = max(max_temp, max_wind) * 1.3 if max(max_temp, max_wind) > 0 else 15

    max_y2 = 1
    if 'Enfermos' in df.columns:
        max_y2 = max(max_y2, df['Enfermos'].max() * 1.3) 
    if 'Muertos' in df.columns and not df['Muertos'].dropna().empty:
        max_y2 = max(max_y2, df['Muertos'].max() * 1.5)
    if 'Abortos' in df.columns and not df['Abortos'].dropna().empty:
        max_y2 = max(max_y2, df['Abortos'].max() * 1.5)
    max_y2 = max(max_y2, 2)

    fecha_mas_reciente = df['fecha'].max()
    anio_reciente = fecha_mas_reciente.year
    mes_reciente = fecha_mas_reciente.month
    
    if mes_reciente - 3 <= 0:
        anio_inicio = anio_reciente - 1
        mes_inicio = mes_reciente - 3 + 12
    else:
        anio_inicio = anio_reciente
        mes_inicio = mes_reciente - 3
    
    fecha_inicio_zoom = pd.Timestamp(year=anio_inicio, month=mes_inicio, day=1)
    fecha_fin_zoom = fecha_mas_reciente
    fecha_fin_zoom_extendida = fecha_fin_zoom + pd.DateOffset(months=1)

    fecha_max_ticks = df['fecha'].max() + pd.DateOffset(months=1)
    fecha_min_ticks = df['fecha'].min()

    if es_movil:
        fecha_ticks = pd.date_range(start=fecha_min_ticks, end=fecha_max_ticks, freq='MS')
        tick_labels = [fecha_espanol(f) for f in fecha_ticks]
        tick_font_size = 8
        legend_font_size = 9
        title_font_size = 10
        height = 320
    else:
        fecha_ticks = pd.date_range(start=fecha_min_ticks, end=fecha_max_ticks, freq='MS')
        tick_labels = [fecha_espanol(f) for f in fecha_ticks]
        tick_font_size = 10  
        legend_font_size = 12   
        title_font_size = 13   
        height = 480

    fig.update_layout(
        hovermode='x unified',
        template='plotly_white',
        height=height,
        dragmode='pan',
        hoverlabel=dict(
            bgcolor='rgba(255, 255, 255, 0.75)',
            bordercolor='rgba(189, 195, 199, 0.5)',
            font_size=12,
            font_color='#2c3e50'
        ),
        xaxis={
            'title': {'text': '<b>Meses</b>', 'font': {'size': title_font_size, 'color': '#34495e'}},
            'type': 'date',
            'tickvals': fecha_ticks,
            'ticktext': tick_labels,
            'hoverformat': '%d de %B de %Y',
            'dtick': 'M1',
            'ticklabelmode': 'period',
            'tickfont': {'size': tick_font_size, 'color': '#2c3e50', 'family': 'Arial Black'},
            'showgrid': True,
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'gridwidth': 0.5,
            'showline': True,
            'linecolor': '#2c3e50',
            'linewidth': 1.5,
            'ticks': 'outside',
            'ticklen': 6,
            'tickwidth': 1.5,
            'tickcolor': '#2c3e50',
            'fixedrange': False,
            'range': [fecha_inicio_zoom, fecha_fin_zoom_extendida],
        },
        yaxis={
            'title': {'text': '<b>Temperatura mínima (°C)</b>', 'font': {'size': title_font_size, 'color': '#34495e'}},
            'range': [y1_min, y1_max],
            'tickformat': '.1f',
            'tickfont': {'size': tick_font_size, 'color': '#2c3e50'},
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'gridwidth': 0.5,
            'zeroline': True,
            'zerolinecolor': 'rgba(128, 128, 128, 0.5)',
            'zerolinewidth': 1,
            'showline': True,
            'linecolor': '#2c3e50',
            'linewidth': 1.5,
            'ticks': 'outside',
            'ticklen': 6,
            'tickwidth': 1.5,
            'tickcolor': '#2c3e50',
            'fixedrange': False,
            'side': 'left'
        },
        yaxis2={
            'title': {'text': '<b>Precipitación / Afectación</b>', 'font': {'size': title_font_size, 'color': '#34495e'}},
            'range': [0, max_y2],
            'tickformat': 'd',
            'dtick': max(2, int(max_y2 / 8)),
            'tickfont': {'size': tick_font_size, 'color': '#2c3e50'},
            'overlaying': 'y',
            'side': 'right',
            'gridcolor': 'rgba(0, 0, 0, 0)',
            'gridwidth': 0,
            'showgrid': False,
            'showline': True,
            'linecolor': '#2c3e50',
            'linewidth': 1.5,
            'ticks': 'outside',
            'ticklen': 6,
            'tickwidth': 1.5,
            'tickcolor': '#2c3e50',
            'fixedrange': False
        },
        images=images_plotly,
        legend={
            'orientation': 'h',
            'x': 0.5,
            'y': -0.22,
            'xanchor': 'center',
            'yanchor': 'top',
            'bgcolor': 'rgba(255, 255, 255, 0.95)',
            'bordercolor': '#bdc3c7',
            'borderwidth': 1,
            'font': {'size': legend_font_size, 'color': '#2c3e50', 'family': 'Arial Black'},
            'itemwidth': 30,
            'tracegroupgap': 5
        },
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin={'t': 15, 'b': 15, 'l': 30, 'r': 30} if es_movil else {'t': 20, 'b': 20, 'l': 45, 'r': 45}
    )

    # LÍNEA HORIZONTAL EN y=0
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="gray",
        line_width=1.5,
        opacity=0.75
    )

    # LÍNEA VERTICAL DÍA 1 DE CADA MES
    fecha_min_data = df['fecha'].min()
    fecha_max_data = df['fecha'].max()

    meses_rango = pd.date_range(
        start=fecha_min_data.replace(day=1),
        end=fecha_max_data + pd.DateOffset(months=1),
        freq='MS'
    )

    for mes in meses_rango:
        fecha_dia1 = mes
        if fecha_min_data <= fecha_dia1 <= fecha_max_data:
            fig.add_vline(
                x=fecha_dia1,
                line_dash="dot",
                line_color="rgba(120, 120, 120, 0.55)",
                line_width=1.6,
                opacity=0.6
            )

    # LÍNEAS VERTICALES PUNTEADAS EN DÍAS 10 Y 20 DE CADA MES
    for mes in meses_rango:
        for dia in (10, 20):
            fecha_linea = mes.replace(day=dia)
            if fecha_min_data <= fecha_linea <= fecha_max_data:
                fig.add_vline(
                    x=fecha_linea,
                    line_dash="dot",
                    line_color="rgba(120, 120, 120, 0.6)",
                    line_width=1.2,
                    opacity=0.7
                )

    return fig

# ============================================================
# FRAGMENTO DE AUTO-REFRESH (60 SEGUNDOS EN SEGUNDO PLANO)
# ============================================================
@st.fragment(run_every="60s")
def auto_refresh_60s():
    st.cache_data.clear()

# ============================================================
# MAIN
# ============================================================
def main():
    
    mostrar_logo_senamhi()
    
    # Activar auto-refresh
    auto_refresh_60s()
    
    st.markdown("""
    <div style="text-align: center; padding: 0.5rem 0;">
        <h2 style="font-size: clamp(1.2rem, 4vw, 2rem); line-height: 1.3; margin-bottom: 0;">
            🦙 Monitoreo Diaria - Temperatura, Precipitación y Afectación de Alpacas
            <br>
            <span style="font-size: clamp(1rem, 3vw, 1.5rem); font-weight: bold; color: #555; display: block; margin-top: 8px;">
                (Sierra Sur)
            </span>
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("### 🎛️ Controles")
        st.markdown("**Seleccionar período:**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📅 1 Mes", use_container_width=True):
                st.session_state.zoom_periodo = 1
            if st.button("📅 6 Meses", use_container_width=True):
                st.session_state.zoom_periodo = 6
            if st.button("📅 Todo", use_container_width=True):
                st.session_state.zoom_periodo = None
        
        with col2:
            if st.button("📅 3 Meses", use_container_width=True):
                st.session_state.zoom_periodo = 3
            if st.button("📅 1 Año", use_container_width=True):
                st.session_state.zoom_periodo = 12
        
        st.markdown("---")
        
        with st.expander("ℹ️ Cómo interactuar", expanded=False):
            st.markdown("""
            - **🖱️ Pasa el cursor** sobre la gráfica para ver los datos diarios
            - **🖱️ Deslizar**: Arrastra el mouse ← →
            - **🔍 Zoom**: Rueda del mouse
            """)
        
        if st.button("🔄 Actualizar datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

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
    es_movil = False

    with st.spinner('🔄 Cargando datos desde Google Sheets...'):
        df = cargar_datos(GOOGLE_SHEETS_ID, SHEET_NAME_SINTOMAS, SHEET_NAME_TEMPERATURAS)

    if df is not None and not df.empty:
        with st.spinner('📊 Generando gráfica interactiva...'):
            fig = crear_grafica(df, IMAGES, zoom_meses, es_movil)

        if fig is not None:
            # 1. MUESTRA LA GRÁFICA
            st.plotly_chart(fig, use_container_width=True, config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['toImage', 'sendDataToCloud'],
                'displaylogo': False,
                'scrollZoom': True,
                'responsive': True,
                'modeBarButtonsToAdd': [
                    'zoom2d', 'pan2d', 'select2d', 'lasso2d',
                    'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'
                ]
            })

           # 2. BLOQUE CON ICONO/BOTÓN DE ESTADÍSTICAS BAJO LA LEYENDA
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("📊 **Ver Estadísticas Generales y Resumen del Período**", expanded=False):
                # ============================================================
                # MÉTRICAS POR AÑO (en lugar de acumulado total)
                # ============================================================
                df_anual_metricas = df.copy()
                df_anual_metricas['Año'] = df_anual_metricas['fecha'].dt.year
                anios_metricas = sorted(df_anual_metricas['Año'].unique().tolist())

                for anio in anios_metricas:
                    d_anio = df_anual_metricas[df_anual_metricas['Año'] == anio]
                    st.markdown(f"##### 📅 Año {anio}")
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        total_enfermas = int(d_anio['Enfermos'].sum()) if 'Enfermos' in d_anio.columns else 0
                        st.metric("🦙 Alpacas Enfermas", f"{total_enfermas:,}")

                    with col2:
                        total_muertas = int(d_anio['Muertos'].sum()) if 'Muertos' in d_anio.columns else 0
                        st.metric("💀 Alpacas Muertas", f"{total_muertas:,}")

                    with col3:
                        total_abortos = int(d_anio['Abortos'].sum()) if 'Abortos' in d_anio.columns else 0
                        st.metric("⚠️ Abortos Registrados", f"{total_abortos:,}")

                    with col4:
                        temp_min_abs = d_anio['Temperaturas minimas  (°C)'].min() if 'Temperaturas minimas  (°C)' in d_anio.columns else 0.0
                        st.metric("❄️ Temp. Mínima Absoluta", f"{temp_min_abs:.1f} °C")
                
                st.markdown("---")
                  
                # ============================================================
                # NUEVO: ESTADÍSTICAS POR AÑO Y ESTACIÓN (MOSTRAR/OCULTAR)
                # ============================================================
                st.markdown("---")
                st.markdown("#### 📅 Análisis por Año y Estación")

                mostrar_torta = st.checkbox(" Mostrar gráfica de torta por año", value=True, key="chk_torta")
                mostrar_tabla_anual = st.checkbox("📋 Mostrar tabla resumen por año", value=True, key="chk_tabla_anual")
                mostrar_comparativo = st.checkbox("📈 Mostrar gráfica comparativa años vs estaciones", value=True, key="chk_comparativo")

                df_anual = df.copy()
                df_anual['Año'] = df_anual['fecha'].dt.year

                def estacion_de_mes(mes):
                    if mes in (12, 1, 2):
                        return 'Verano'
                    elif mes in (3, 4, 5):
                        return 'Otoño'
                    elif mes in (6, 7, 8):
                        return 'Invierno'
                    else:
                        return 'Primavera'

                df_anual['Estación'] = df_anual['fecha'].dt.month.apply(estacion_de_mes)

                anios_disponibles = sorted(df_anual['Año'].unique().tolist())

                # ---------- GRÁFICA DE TORTA POR AÑO ----------
                if mostrar_torta and len(anios_disponibles) > 0:
                    st.markdown("##### 🦙 Distribución de Afectación por Año")
                    cols_torta = st.columns(min(len(anios_disponibles), 3))
                    for i, anio in enumerate(anios_disponibles):
                        df_anio = df_anual[df_anual['Año'] == anio]
                        val_enfermas = int(df_anio['Enfermos'].sum()) if 'Enfermos' in df_anio.columns else 0
                        val_muertas = int(df_anio['Muertos'].sum()) if 'Muertos' in df_anio.columns else 0
                        val_abortos = int(df_anio['Abortos'].sum()) if 'Abortos' in df_anio.columns else 0
                        total_anio = val_enfermas + val_muertas + val_abortos
                        if total_anio == 0:
                            continue
                        fig_torta = go.Figure(data=[go.Pie(
                            labels=['Enfermas', 'Muertas', 'Abortos'],
                            values=[val_enfermas, val_muertas, val_abortos],
                            hole=0.35,
                            marker=dict(colors=['#8B0000', '#555555', '#1E90FF']),
                            textinfo='percent+label',
                            textfont=dict(size=11)
                        )])
                        fig_torta.update_layout(
                            title=dict(text=f"<b>Año {anio}</b>", font=dict(size=13), x=0.5),
                            height=280,
                            margin=dict(t=40, b=10, l=10, r=10),
                            showlegend=False,
                            paper_bgcolor='white',
                            plot_bgcolor='white'
                        )
                        with cols_torta[i % len(cols_torta)]:
                            st.plotly_chart(fig_torta, use_container_width=True, key=f"torta_{anio}")

                # Resumen climático por año
                st.markdown("##### 🌦️ Resumen de Datos Climáticos por Año:")
                df_clima = df.copy()
                df_clima['Año'] = df_clima['fecha'].dt.year
                anios_clima = sorted(df_clima['Año'].unique().tolist())

                filas_clima = []
                for anio in anios_clima:
                    d = df_clima[df_clima['Año'] == anio]
                    filas_clima.append({
                        'Año': anio,
                        'Precip. Acum. Total (mm)': round(d['Precipitacion '].sum(), 1) if 'Precipitacion ' in d.columns else 0.0,
                        'Viento Prom. (km/h)': round(d['Vel. viento (Km/h)'].mean(), 1) if 'Vel. viento (Km/h)' in d.columns else 0.0,
                        'Temp. Mín. Prom. (°C)': round(d['Temperaturas minimas  (°C)'].mean(), 1) if 'Temperaturas minimas  (°C)' in d.columns else 0.0,
                        'Temp. Mín. Abs. (°C)': round(d['Temperaturas minimas  (°C)'].min(), 1) if 'Temperaturas minimas  (°C)' in d.columns else 0.0,
                        'Temp. Mín. Máx. (°C)': round(d['Temperaturas minimas  (°C)'].max(), 1) if 'Temperaturas minimas  (°C)' in d.columns else 0.0,
                        'Viento Máx. (km/h)': round(d['Vel. viento (Km/h)'].max(), 1) if 'Vel. viento (Km/h)' in d.columns else 0.0,
                        'Precip. Máx. Diaria (mm)': round(d['Precipitacion '].max(), 1) if 'Precipitacion ' in d.columns else 0.0,
                        'Días con Datos': len(d)
                    })

                tabla_clima = pd.DataFrame(filas_clima).sort_values('Año').reset_index(drop=True)
                st.dataframe(tabla_clima, use_container_width=True, hide_index=True)

                # ---------- GRÁFICA COMPARATIVA AÑOS vs ESTACIONES ----------
                if mostrar_comparativo and len(anios_disponibles) > 0:
                    st.markdown("##### 📈 Comparativo Años vs Estaciones")
                    orden_estaciones = ['Verano', 'Otoño', 'Invierno', 'Primavera']
                    df_est = df_anual.groupby(['Año', 'Estación']).agg({
                        'Enfermos': 'sum',
                        'Muertos': 'sum',
                        'Abortos': 'sum'
                    }).reset_index()

                    fig_comp = go.Figure()
                    colores_est = {'Verano': '#FFD700', 'Otoño': '#FF8C00',
                                   'Invierno': '#1E90FF', 'Primavera': '#32CD32'}
                    for est in orden_estaciones:
                        d_est = df_est[df_est['Estación'] == est]
                        if d_est.empty:
                            continue
                        fig_comp.add_trace(go.Bar(
                            x=d_est['Año'].astype(str),
                            y=d_est['Enfermos'] + d_est['Muertos'] + d_est['Abortos'],
                            name=est,
                            marker_color=colores_est[est],
                            hovertemplate=(
                                f"<b>{est}</b><br>Año: %{{x}}<br>"
                                "Total afectación: %{y}<extra></extra>"
                            )
                        ))
                    fig_comp.update_layout(
                        barmode='group',
                        height=380,
                        template='plotly_white',
                        xaxis=dict(title='<b>Año</b>', tickfont=dict(size=11)),
                        yaxis=dict(title='<b>Total Afectación (Enf+Muert+Abort)</b>', tickfont=dict(size=11)),
                        legend=dict(orientation='h', x=0.5, y=-0.18, xanchor='center', yanchor='top'),
                        margin=dict(t=20, b=60, l=50, r=20)
                    )
                    st.plotly_chart(fig_comp, use_container_width=True, key="comparativo_anual")
                       
if __name__ == '__main__':
    main()
