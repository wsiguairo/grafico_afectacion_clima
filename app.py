## app.py - VERSIÓN STREAMLIT
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
    layout="wide"
)

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

        # Función para encontrar columna de fecha
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
# FUNCIÓN PARA CREAR LA GRÁFICA
# ============================================================
def crear_grafica(df, images_paths):
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
            marker=dict(size=4, color='#2563EB'),
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
            line=dict(color='#808080', width=2, dash='dash'),
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
            line=dict(color='#8B0000', width=2.5),
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
                marker=dict(size=12, color='#555555', line=dict(color='black', width=0.5)),
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
                marker=dict(size=12, color='#1E90FF', line=dict(color='#87CEEB', width=1)),
                yaxis='y2',
                customdata=df_abortos['Abortos'],
                hovertemplate='<b>⚠️ Abortos:</b> %{customdata:02.0f}<extra></extra>'
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

    # ZOOM INICIAL
    año_datos = df['fecha'].max().year
    fecha_inicio_zoom = pd.Timestamp(year=año_datos, month=5, day=1)
    fecha_fin_zoom = pd.Timestamp(year=año_datos, month=8, day=31)
    
    if df[(df['fecha'] >= fecha_inicio_zoom) & (df['fecha'] <= fecha_fin_zoom)].empty:
        fecha_inicio_zoom = df['fecha'].max() - pd.DateOffset(months=6)
        fecha_fin_zoom = df['fecha'].max()

    # TICKS
    fecha_ticks = pd.date_range(start=df['fecha'].min(), end=df['fecha'].max(), freq='MS')
    tick_labels = [fecha_espanol(f) for f in fecha_ticks]

    # LAYOUT
    fig.update_layout(
        title={
            'text': 'Monitoreo Diaria - Temperatura, Precipitación y Afectación de Alpacas',
            'font': {'size': 20, 'family': 'Arial, sans-serif', 'color': '#2c3e50'},
            'x': 0.5,
            'xanchor': 'center'
        },
        hovermode='x unified',
        template='plotly_white',
        height=700,
        dragmode='pan',
        xaxis={
            'title': {'text': 'Meses', 'font': {'size': 13, 'color': '#34495e'}},
            'type': 'date',
            'tickvals': fecha_ticks,
            'ticktext': tick_labels,
            'hoverformat': '%d de %B de %Y',
            'dtick': 'M1',
            'ticklabelmode': 'period',
            'tickfont': {'size': 11, 'color': '#2c3e50'},
            'showgrid': True,
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'gridwidth': 0.5,
            'fixedrange': False,
            'range': [fecha_inicio_zoom, fecha_fin_zoom],
            'rangeselector': {
                'buttons': [
                    {'count': 1, 'label': '1 Mes', 'step': 'month', 'stepmode': 'backward'},
                    {'count': 3, 'label': '3 Meses', 'step': 'month', 'stepmode': 'backward'},
                    {'count': 6, 'label': '6 Meses', 'step': 'month', 'stepmode': 'backward'},
                    {'count': 12, 'label': '1 Año', 'step': 'month', 'stepmode': 'backward'},
                    {'step': 'all', 'label': 'Todo'}
                ],
                'font': {'size': 10, 'color': '#2c3e50'},
                'bgcolor': 'rgba(240, 240, 240, 0.9)',
                'activecolor': 'rgba(46, 134, 171, 0.4)',
                'bordercolor': '#bdc3c7',
                'borderwidth': 1,
                'x': 0.02,
                'xanchor': 'left',
                'y': 1.02,
                'yanchor': 'bottom'
            }
        },
        yaxis={
            'title': {'text': 'Temperatura mínima (°C)', 'font': {'size': 13, 'color': '#34495e'}},
            'range': [y1_min, y1_max],
            'tickformat': '.1f',
            'tickfont': {'size': 11, 'color': '#2c3e50'},
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'gridwidth': 0.5,
            'zeroline': True,
            'zerolinecolor': 'rgba(128, 128, 128, 0.5)',
            'zerolinewidth': 1,
            'fixedrange': False,
            'side': 'left'
        },
        yaxis2={
            'title': {'text': 'Precipitación / Afectación', 'font': {'size': 13, 'color': '#34495e'}},
            'range': [0, max_y2],
            'tickformat': 'd',
            'dtick': max(2, int(max_y2 / 8)),
            'tickfont': {'size': 11, 'color': '#2c3e50'},
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
            'font': {'size': 11, 'color': '#2c3e50'},
            'itemwidth': 30,
            'tracegroupgap': 5
        },
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin={'t': 80, 'b': 100, 'l': 80, 'r': 120}
    )

    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=0.8, opacity=0.4)

    return fig

# ============================================================
# MAIN - APLICACIÓN STREAMLIT
# ============================================================
def main():
    st.title("🦙 Variación Diaria - Temperatura, Precipitación y Afectación de Alpacas")
    st.caption("📊 Datos cargados automáticamente desde Google Sheets")

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

    # Cargar datos
    with st.spinner('🔄 Cargando datos desde Google Sheets...'):
        df = cargar_datos(GOOGLE_SHEETS_ID, SHEET_NAME_SINTOMAS, SHEET_NAME_TEMPERATURAS)

    if df is not None and not df.empty:
        with st.spinner('📊 Generando gráfica interactiva...'):
            fig = crear_grafica(df, IMAGES)

        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['toImage', 'sendDataToCloud'],
                'displaylogo': False,
                'scrollZoom': True,
                'responsive': True
            })

            # ESTADÍSTICAS
            with st.expander("📊 Ver estadísticas de los datos"):
                col1, col2, col3 = st.columns(3)
                
                if 'Enfermos' in df.columns and not df['Enfermos'].dropna().empty:
                    col1.metric("🦙 Total Enfermos", f"{df['Enfermos'].sum():.0f}")
                if 'Muertos' in df.columns and not df['Muertos'].dropna().empty:
                    col2.metric("💀 Total Muertos", f"{df['Muertos'].sum():.0f}")
                if 'Abortos' in df.columns and not df['Abortos'].dropna().empty:
                    col3.metric("⚠️ Total Abortos", f"{df['Abortos'].sum():.0f}")

                st.dataframe(df, use_container_width=True)

            st.info("""
            **🖱️ Cómo interactuar:**
            - **Deslizar**: Arrastra el mouse horizontalmente ← → 
            - **Zoom**: Rueda del mouse
            - **Ver valores**: Pasa el cursor sobre cualquier punto
            - **Selector de tiempo**: Botones "1 Mes", "3 Meses", etc.
            """)

            st.success("✅ ¡Gráfica cargada exitosamente!")
        else:
            st.error("❌ Error al generar la gráfica")
    else:
        st.error("❌ No se pudieron cargar los datos")

if __name__ == "__main__":
    main()
