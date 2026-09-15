# app.py - VERSIÓN PANTALLA COMPLETA OPTIMIZADA
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
    page_title="Gráfica afectación alpaca",
    page_icon="🦙",
    layout="wide",
    initial_sidebar_state="collapsed"  # Minimiza la barra lateral para dar prioridad a la gráfica
)

# ============================================================
# ESTILOS PARA MAXIMIZAR A PANTALLA COMPLETA
# ============================================================
st.markdown("""
<style>
    /* 1. Eliminar paddings y márgenes del contenedor principal de Streamlit */
    .main .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0.2rem !important;
        padding-right: 0.2rem !important;
        max-width: 100% !important;
    }
    
    header { display: none !important; }
    footer { display: none !important; }
    
    /* 2. Forzar que el gráfico ocupe la altura máxima del Viewport (pantalla) */
    .stPlotlyChart {
        width: 100% !important;
        height: 92vh !important; /* Maximiza la altura en pantalla */
        min-height: 500px !important;
    }
    
    .stPlotlyChart > div, .js-plotly-plot, .plot-container {
        width: 100% !important;
        height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    .logo-senamhi {
        position: fixed;
        top: 8px;
        left: 8px;
        z-index: 999999;
        width: 65px;
        height: auto;
        opacity: 0.9;
        border-radius: 6px;
        background: rgba(255, 255, 255, 0.85);
        padding: 3px;
    }

    @media only screen and (max-width: 768px) {
        .stPlotlyChart {
            height: 88vh !important;
        }
        .logo-senamhi {
            width: 45px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# FUNCIONES DE CARGA Y LOGO
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
                 alt="Logo SENAMHI">
            """, unsafe_allow_html=True)
        except:
            pass

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

        df_sintomas = estandarizar_columnas(df_sintomas, {
            'Enfermos': ['enfermos', 'enfermo', 'enfermas'],
            'Muertos': ['muertos', 'muerto', 'muertas', 'fallecidos'],
            'Abortos': ['abortos', 'aborto', 'abortadas']
        })

        df_temperaturas = estandarizar_columnas(df_temperaturas, {
            'Temperaturas minimas  (°C)': ['temperatura minima', 'temp min', 'tmin'],
            'Vel. viento (Km/h)': ['viento', 'velocidad viento', 'wind'],
            'Precipitacion ': ['precipitacion', 'precipitación', 'lluvia']
        })

        df_sintomas['fecha'] = pd.to_datetime(df_sintomas[col_fecha_sintomas], errors='coerce')
        df_temperaturas['fecha'] = pd.to_datetime(df_temperaturas[col_fecha_temp], errors='coerce')

        df_sintomas = df_sintomas.dropna(subset=['fecha'])
        df_temperaturas = df_temperaturas.dropna(subset=['fecha'])

        df = pd.merge(df_sintomas, df_temperaturas, on='fecha', how='outer').sort_values('fecha').reset_index(drop=True)
        df = df[df['fecha'] <= pd.Timestamp.now().normalize()]

        columnas_numericas = ['Enfermos', 'Muertos', 'Abortos', 'Temperaturas minimas  (°C)', 'Vel. viento (Km/h)', 'Precipitacion ']
        for col in columnas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                if col in ['Enfermos', 'Muertos', 'Abortos']:
                    df[col] = df[col].fillna(0)

        agg_dict = {col: 'sum' for col in ['Enfermos', 'Muertos', 'Abortos'] if col in df.columns}
        agg_dict.update({col: 'mean' for col in ['Temperaturas minimas  (°C)', 'Precipitacion ', 'Vel. viento (Km/h)'] if col in df.columns})
        
        df = df.groupby('fecha').agg(agg_dict).reset_index()

        fecha_smooth, enfermos_smooth = np.array([]), np.array([])
        df_filtrado = df[(df['Enfermos'] > 0) & (df['Enfermos'].notna())]
        if len(df_filtrado) >= 3:
            try:
                x_tiempo = df_filtrado['fecha'].map(pd.Timestamp.to_julian_date).values
                y = df_filtrado['Enfermos'].values
                x_suave = np.linspace(x_tiempo.min(), x_tiempo.max(), 500)
                
                spline = make_interp_spline(x_tiempo, y, k=4)
                y_suave = spline(x_suave)
                
                spline_extra = UnivariateSpline(x_tiempo, y, s=len(y)*1.5, k=4)
                y_suave_extra = spline_extra(x_suave)
                
                y_suave_final = np.clip(0.7 * y_suave_extra + 0.3 * y_suave, 0.1, None)
                if min(5, len(y_suave_final) // 10) > 1:
                    y_suave_final = uniform_filter1d(y_suave_final, size=min(5, len(y_suave_final) // 10), mode='nearest')
                
                fecha_smooth = pd.to_datetime(x_suave, unit='D', origin='julian')
                enfermos_smooth = y_suave_final
            except:
                pass
        
        df.attrs['fecha_smooth'] = fecha_smooth
        df.attrs['enfermos_smooth'] = enfermos_smooth
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None

# ============================================================
# CREACIÓN DE GRÁFICA AJUSTADA
# ============================================================
def crear_grafica(df, images_paths):
    if df is None or df.empty:
        return go.Figure()

    fecha_smooth = df.attrs.get('fecha_smooth', np.array([]))
    enfermos_smooth = df.attrs.get('enfermos_smooth', np.array([]))

    fig = go.Figure()

    if 'Precipitacion ' in df.columns and not df['Precipitacion '].dropna().empty:
        fig.add_trace(go.Bar(
            x=df['fecha'], y=df['Precipitacion '], name='Precipitación',
            marker=dict(color='#87CEEB', opacity=0.5), yaxis='y2', hoverinfo='skip'
        ))

    if 'Temperaturas minimas  (°C)' in df.columns and not df['Temperaturas minimas  (°C)'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['fecha'], y=df['Temperaturas minimas  (°C)'], mode='lines+markers',
            name='Temperatura mínima', line=dict(color='#2563EB', width=2.5),
            marker=dict(size=4, color='#2563EB'), hoverinfo='skip'
        ))

    if 'Vel. viento (Km/h)' in df.columns and not df['Vel. viento (Km/h)'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['fecha'], y=df['Vel. viento (Km/h)'], mode='lines',
            name='Viento', line=dict(color='#808080', width=2, dash='dash'), hoverinfo='skip'
        ))

    if len(enfermos_smooth) > 0:
        fig.add_trace(go.Scatter(
            x=fecha_smooth, y=enfermos_smooth, mode='lines', name='Alpacas enfermas',
            line=dict(color='#8B0000', width=2.5), fill='tozeroy',
            fillgradient=dict(type='vertical', colorscale=[[0, 'rgba(139, 0, 0, 0)'], [1, 'rgba(139, 0, 0, 0.15)']]),
            yaxis='y2', hoverinfo='skip'
        ))

    if 'Muertos' in df.columns:
        df_m = df[df['Muertos'] > 0]
        if not df_m.empty:
            fig.add_trace(go.Scatter(
                x=df_m['fecha'], y=[0.2] * len(df_m), mode='markers', name='Alpacas muertas',
                marker=dict(size=12, color='#555555', line=dict(color='black', width=0.5)),
                yaxis='y2', hoverinfo='skip'
            ))

    if 'Abortos' in df.columns:
        df_a = df[df['Abortos'] > 0]
        if not df_a.empty:
            fig.add_trace(go.Scatter(
                x=df_a['fecha'], y=[0.25] * len(df_a), mode='markers', name='Abortos',
                marker=dict(size=12, color='#1E90FF', line=dict(color='#87CEEB', width=1)),
                yaxis='y2', hoverinfo='skip'
            ))

    # Trace hover único
    df_hover = df.copy()
    for col in ['Precipitacion ', 'Temperaturas minimas  (°C)', 'Vel. viento (Km/h)', 'Enfermos', 'Muertos', 'Abortos']:
        if col not in df_hover.columns:
            df_hover[col] = np.nan

    hover_texts = []
    for _, row in df_hover.iterrows():
        texto = f"<b>📅 {row['fecha'].strftime('%d/%m/%Y')}</b><br>"
        if pd.notna(row['Precipitacion ']): texto += f"<b>💧 Precipitación:</b> {row['Precipitacion ']:.0f} mm<br>"
        if pd.notna(row['Temperaturas minimas  (°C)']): texto += f"<b>🌡️ Temperatura mínima:</b> {row['Temperaturas minimas  (°C)']:.1f} °C<br>"
        if pd.notna(row['Vel. viento (Km/h)']): texto += f"<b>💨 Viento:</b> {row['Vel. viento (Km/h)']:.0f} Km/h<br>"
        if pd.notna(row['Enfermos']) and row['Enfermos'] > 0: texto += f"<b>🦙 Alpacas enfermas:</b> {row['Enfermos']:.0f}<br>"
        if pd.notna(row['Muertos']) and row['Muertos'] > 0: texto += f"<b>💀 Alpacas muertas:</b> {row['Muertos']:.0f}<br>"
        if pd.notna(row['Abortos']) and row['Abortos'] > 0: texto += f"<b>⚠️ Abortos:</b> {row['Abortos']:.0f}<br>"
        hover_texts.append(texto)

    fig.add_trace(go.Scatter(
        x=df_hover['fecha'], y=[0] * len(df_hover), mode='markers', name='',
        marker=dict(size=0.1, color='rgba(0,0,0,0)'), yaxis='y2', showlegend=False,
        hoverinfo='text', text=hover_texts
    ))

    # Rangos de ejes
    min_temp = df['Temperaturas minimas  (°C)'].min() if 'Temperaturas minimas  (°C)' in df.columns else 0
    max_temp = df['Temperaturas minimas  (°C)'].max() if 'Temperaturas minimas  (°C)' in df.columns else 10
    max_wind = df['Vel. viento (Km/h)'].max() if 'Vel. viento (Km/h)' in df.columns else 0

    y1_min = min_temp * 1.2 if min_temp < 0 else -5
    y1_max = max(max_temp, max_wind) * 1.3 if max(max_temp, max_wind) > 0 else 15

    max_y2 = 1
    if len(enfermos_smooth) > 0: max_y2 = max(max_y2, max(enfermos_smooth) * 1.3)
    if 'Precipitacion ' in df.columns: max_y2 = max(max_y2, df['Precipitacion '].max() * 1.1)
    max_y2 = max(max_y2, 2)

    fecha_max = df['fecha'].max()
    fecha_inicio_zoom = fecha_max - pd.DateOffset(months=3)
    fecha_fin_zoom_extendida = fecha_max + pd.DateOffset(months=1)

    fecha_ticks = pd.date_range(start=df['fecha'].min(), end=fecha_max + pd.DateOffset(months=1), freq='MS')
    tick_labels = [fecha_espanol(f) for f in fecha_ticks]

    # Layout optimizado para pantalla completa
    fig.update_layout(
        autosize=True,
        hovermode='x unified',
        template='plotly_white',
        dragmode='pan',
        xaxis={
            'title': {'text': 'Meses', 'font': {'size': 12}},
            'type': 'date',
            'tickvals': fecha_ticks,
            'ticktext': tick_labels,
            'dtick': 'M1',
            'tickfont': {'size': 11},
            'showgrid': True,
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'range': [fecha_inicio_zoom, fecha_fin_zoom_extendida]
        },
        yaxis={
            'title': {'text': 'Temperatura mínima (°C)', 'font': {'size': 12}},
            'range': [y1_min, y1_max],
            'tickfont': {'size': 11},
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'side': 'left'
        },
        yaxis2={
            'title': {'text': 'Precipitación / Afectación', 'font': {'size': 12}},
            'range': [0, max_y2],
            'tickfont': {'size': 11},
            'overlaying': 'y',
            'side': 'right',
            'showgrid': False
        },
        legend={
            'orientation': 'h',
            'x': 0.5,
            'y': -0.12,
            'xanchor': 'center',
            'yanchor': 'top',
            'bgcolor': 'rgba(255, 255, 255, 0.9)',
            'bordercolor': '#bdc3c7',
            'borderwidth': 1,
            'font': {'size': 12}
        },
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin={'t': 10, 'b': 85, 'l': 40, 'r': 40}
    )
    return fig

# ============================================================
# MAIN
# ============================================================
def main():
    mostrar_logo_senamhi()
    
    GOOGLE_SHEETS_ID = '11UWULdTZL2tKKpeGRETXOHvQt_3jHxIMgap2lfkDpro'
    df = cargar_datos(GOOGLE_SHEETS_ID, 'sintomas', 'temperaturas')

    if df is not None and not df.empty:
        fig = crear_grafica(df, {})
        st.plotly_chart(fig, use_container_width=True, config={
            'displayModeBar': True,
            'displaylogo': False,
            'scrollZoom': True,
            'responsive': True
        })

if __name__ == '__main__':
    main()
