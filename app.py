# app.py - VERSIÓN CON IMÁGENES FORZADAS
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import make_interp_spline, UnivariateSpline
from scipy.ndimage import uniform_filter1d
import warnings
import base64
import os
from PIL import Image
import io

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
# ESTILOS RESPONSIVE CON LOGO SENAMHI
# ============================================================
st.markdown("""
<style>
    /* ESTILOS GENERALES */
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
# FUNCIÓN ROBUSTA PARA CARGAR IMÁGENES
# ============================================================
def cargar_imagen_robusta(filepath):
    """
    Carga una imagen de forma robusta con múltiples intentos
    y formatos alternativos
    """
    # Lista de posibles extensiones
    extensiones = ['', '.png', '.PNG', '.jpg', '.JPG', '.jpeg', '.JPEG', '.gif', '.GIF']
    
    # Lista de posibles rutas
    rutas_posibles = [
        filepath,
        filepath.replace('.png', '.PNG'),
        filepath.replace('.png', '.jpg'),
        filepath.replace('.png', '.jpeg'),
        os.path.join('imagenes', os.path.basename(filepath)),
        os.path.join('assets', os.path.basename(filepath)),
        os.path.join('static', os.path.basename(filepath)),
    ]
    
    # Intentar con diferentes extensiones
    for ext in extensiones:
        for ruta in rutas_posibles:
            ruta_completa = ruta if ruta.endswith(ext) else ruta + ext
            if os.path.exists(ruta_completa):
                try:
                    # Intentar leer como imagen
                    with open(ruta_completa, 'rb') as f:
                        img_data = f.read()
                        # Verificar que sea una imagen válida
                        try:
                            Image.open(io.BytesIO(img_data))
                            return base64.b64encode(img_data).decode()
                        except:
                            continue
                except:
                    continue
    
    # Si no se encuentra la imagen, crear una imagen por defecto
    return crear_imagen_por_defecto(filepath)

def crear_imagen_por_defecto(tipo):
    """
    Crea una imagen por defecto si no se encuentra el archivo
    """
    # Crear una imagen simple con texto
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Crear imagen de 64x64
        img = Image.new('RGB', (64, 64), color=(200, 200, 200))
        d = ImageDraw.Draw(img)
        
        # Texto según el tipo
        if 'enferma' in tipo:
            texto = "🦙"
            color = (139, 0, 0)
        elif 'muerta' in tipo:
            texto = "💀"
            color = (80, 80, 80)
        elif 'aborto' in tipo:
            texto = "⚠️"
            color = (30, 144, 255)
        else:
            texto = "📷"
            color = (100, 100, 100)
        
        # Dibujar fondo
        d.rectangle([0, 0, 63, 63], fill=(240, 240, 240), outline=color, width=2)
        
        # Dibujar texto (emoticon)
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except:
            font = ImageFont.load_default()
        
        d.text((16, 16), texto, fill=color, font=font)
        
        # Convertir a base64
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        return base64.b64encode(img_byte_arr).decode()
        
    except:
        # Si todo falla, crear un cuadro simple
        import hashlib
        hash_str = hashlib.md5(tipo.encode()).hexdigest()[:8]
        return f"iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAAXNSR0IArs4c6QAAAARzQklUCAgICHwIZAAAAAlwSFlzAAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAcGFpbnQubmV0IDQuMC4xMkMEa+wAAAI2SURBVHic7Zu9jtNAFIW/GUdOShSJAgEBQrRIUFAg0VDR8AgUPAGIimdAookEDUJIQqSgQNpUIEGRApD4WdfeGzuTxI6Tae14zkcqpNj2+Zk7Z2aucS3T+XxOJpMh0zRNkiTZqKMv7r7Ovu6Pl5EjZjN0f+Sji+Vp8nK+oyiKzdMEWgFsAW4Bt5OqlhVJsv/XgPcAb4FfAJeOEMvnXrT6CHADcAPct1fAATADFgPLF/lCwjWlEk2FABaPyQHw7w4n7zt0AbwCuAX4cAcC20IUS6l8nv4Cn3b9cCbAAZgB4wNs3KGKv9v3iv/2k8vgnhXf9ggW8UuTuwR4CeASgW3hxxbL/z9K5QvgT2epvLrgKjAHi0d4r/jVS1b25FcM58AMmAzYxg1j/PmYHn8f07V7+H3M+hDx0kqeYT6fT00CaiXqkE/v+uF1HgLcv5wgw8kbwBvgR8dHl98LAmLAtwBvCz5JAVuW9B7wNtdexi8/cwA4AA4Sh0yBkZOM4YXfGfBqnIxT10c5T94C3gTv3hh+kgK2LGk38O6N4SeYApFjz2cRjdNZ4R14CZmzU1cGOmCSB5iQf4jPsHGNk5+IFD7Cbbjr6qCk+i8SPSw7wI2uDjAAI/8z7fY0vX/nh0TfvCUp4hJjAd8FbQFfA7zMkD3gRwN/AXxO94BPDeDafXzg9wmzAfeADw1gXlXwUSLkO8Anr2r0O5pCB88Wky9r6QA3S/e4O+dHfZ9zfLpnp8/3+7cAfgM8AHh9mvYcjwAAAABJRU5ErkJggg=="

def image_to_base64_robusta(filepath):
    """
    Versión robusta de image_to_base64 con múltiples intentos
    """
    # Primero intentar con la ruta normal
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                img_data = f.read()
                # Verificar que sea una imagen válida
                try:
                    Image.open(io.BytesIO(img_data))
                    return base64.b64encode(img_data).decode()
                except:
                    pass
        except:
            pass
    
    # Si falla, usar la función robusta
    return cargar_imagen_robusta(filepath)

# ============================================================
# MOSTRAR LOGO SENAMHI
# ============================================================
def mostrar_logo_senamhi():
    """Muestra el logo de SENAMHI en la esquina superior izquierda"""
    
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
            
        except Exception as e:
            st.markdown("""
            <div style="position: fixed; top: 10px; left: 10px; z-index: 999999; 
                        background: rgba(255,255,255,0.9); padding: 6px 12px; 
                        border-radius: 8px; font-size: 12px; 
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <b>🌤️ SENAMHI</b>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="position: fixed; top: 10px; left: 10px; z-index: 999999; 
                    background: rgba(255,255,255,0.9); padding: 6px 12px; 
                    border-radius: 8px; font-size: 12px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <b>🌤️ SENAMHI</b>
        </div>
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

# ============================================================
# FUNCIONES DE PROCESAMIENTO
# ============================================================
@st.cache_data(ttl=10)
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
# FUNCIÓN PARA CREAR LA GRÁFICA CON IMÁGENES FORZADAS
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

    fecha_smooth = df.attrs.get('fecha_smooth', np.array([]))
    enfermos_smooth = df.attrs.get('enfermos_smooth', np.array([]))

    # ============================================================
    # CARGAR IMÁGENES CON FUNCIÓN ROBUSTA
    # ============================================================
    img_enferma = image_to_base64_robusta(images_paths.get('enferma', ''))
    img_muerta = image_to_base64_robusta(images_paths.get('muerta', ''))
    img_aborto = image_to_base64_robusta(images_paths.get('aborto', ''))

    # DEBUG: Verificar si se cargaron las imágenes
    st.sidebar.write("### 🖼️ Estado de imágenes:")
    st.sidebar.write(f"🦙 Enferma: {'✅' if img_enferma else '❌'}")
    st.sidebar.write(f"💀 Muerta: {'✅' if img_muerta else '❌'}")
    st.sidebar.write(f"⚠️ Aborto: {'✅' if img_aborto else '❌'}")

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

    # ============================================================
    # IMÁGENES FORZADAS CON MÚLTIPLES VERIFICACIONES
    # ============================================================
    images_plotly = []
    y_offset = 0.2

    # FORZAR IMAGEN ENFERMA
    if img_enferma and len(enfermos_smooth) > 0:
        try:
            for idx in [0, -1]:
                if len(fecha_smooth) > abs(idx):
                    images_plotly.append({
                        'source': f"data:image/png;base64,{img_enferma}",
                        'xref': 'x',
                        'yref': 'y2',
                        'x': fecha_smooth[idx],
                        'y': float(enfermos_smooth[idx]) if idx >= 0 else float(enfermos_smooth[len(enfermos_smooth)-1]),
                        'sizex': 8,
                        'sizey': 8,
                        'xanchor': 'center',
                        'yanchor': 'middle',
                        'layer': 'above'
                    })
        except Exception as e:
            st.sidebar.warning(f"Error con imagen enferma: {e}")

    # FORZAR IMAGEN MUERTA
    if img_muerta and 'Muertos' in df.columns:
        try:
            df_muertos_varios = df[df['Muertos'] >= 1].copy()  # Cambiado de >=3 a >=1 para forzar más apariciones
            if not df_muertos_varios.empty:
                for _, row in df_muertos_varios.iterrows():
                    images_plotly.append({
                        'source': f"data:image/png;base64,{img_muerta}",
                        'xref': 'x',
                        'yref': 'y2',
                        'x': row['fecha'],
                        'y': y_offset,
                        'sizex': 8,
                        'sizey': 8,
                        'xanchor': 'center',
                        'yanchor': 'middle',
                        'layer': 'above'
                    })
        except Exception as e:
            st.sidebar.warning(f"Error con imagen muerta: {e}")

    # FORZAR IMAGEN ABORTO
    if img_aborto and 'Abortos' in df.columns:
        try:
            df_abortos_pos = df[df['Abortos'] >= 1].copy()  # Cambiado de >0 a >=1
            if not df_abortos_pos.empty:
                for idx in range(min(3, len(df_abortos_pos))):  # Mostrar hasta 3 abortos
                    images_plotly.append({
                        'source': f"data:image/png;base64,{img_aborto}",
                        'xref': 'x',
                        'yref': 'y2',
                        'x': df_abortos_pos['fecha'].iloc[idx],
                        'y': y_offset + 0.05,
                        'sizex': 8,
                        'sizey': 8,
                        'xanchor': 'center',
                        'yanchor': 'middle',
                        'layer': 'above'
                    })
        except Exception as e:
            st.sidebar.warning(f"Error con imagen aborto: {e}")

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

    # TICKS
    if es_movil:
        if len(df) > 30:
            freq = 'MS'
        else:
            freq = 'MS'
        fecha_ticks = pd.date_range(start=df['fecha'].min(), end=df['fecha'].max(), freq=freq)
        tick_labels = [fecha_espanol(f) for f in fecha_ticks]
        tick_font_size = 9
        legend_font_size = 10
        title_font_size = 11
        height = 500
    else:
        fecha_ticks = pd.date_range(start=df['fecha'].min(), end=df['fecha'].max(), freq='MS')
        tick_labels = [fecha_espanol(f) for f in fecha_ticks]
        tick_font_size = 11
        legend_font_size = 11
        title_font_size = 13
        height = 750

    # LAYOUT
    fig.update_layout(
        hovermode='x unified',
        template='plotly_white',
        height=height,
        dragmode='pan',
        xaxis={
            'title': {'text': 'Meses', 'font': {'size': title_font_size, 'color': '#34495e'}},
            'type': 'date',
            'tickvals': fecha_ticks,
            'ticktext': tick_labels,
            'hoverformat': '%d de %B de %Y',
            'dtick': 'M1',
            'ticklabelmode': 'period',
            'tickfont': {'size': tick_font_size, 'color': '#2c3e50'},
            'showgrid': True,
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'gridwidth': 0.5,
            'fixedrange': False,
            'range': [fecha_inicio_zoom, fecha_fin_zoom],
        },
        yaxis={
            'title': {'text': 'Temperatura mínima (°C)', 'font': {'size': title_font_size, 'color': '#34495e'}},
            'range': [y1_min, y1_max],
            'tickformat': '.1f',
            'tickfont': {'size': tick_font_size, 'color': '#2c3e50'},
            'gridcolor': 'rgba(200, 200, 200, 0.3)',
            'gridwidth': 0.5,
            'zeroline': True,
            'zerolinecolor': 'rgba(128, 128, 128, 0.5)',
            'zerolinewidth': 1,
            'fixedrange': False,
            'side': 'left'
        },
        yaxis2={
            'title': {'text': 'Precipitación / Afectación', 'font': {'size': title_font_size, 'color': '#34495e'}},
            'range': [0, max_y2],
            'tickformat': 'd',
            'dtick': max(2, int(max_y2 / 8)),
            'tickfont': {'size': tick_font_size, 'color': '#2c3e50'},
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
            'font': {'size': legend_font_size, 'color': '#2c3e50'},
            'itemwidth': 30,
            'tracegroupgap': 5
        },
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin={'t': 20, 'b': 20, 'l': 40, 'r': 40} if es_movil else {'t': 30, 'b': 30, 'l': 50, 'r': 60}
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=0.8, opacity=0.4)

    if es_movil:
        fig.update_layout(
            hoverlabel={'font_size': 12},
            dragmode='pan',
        )

    return fig

# ============================================================
# MAIN - APLICACIÓN STREAMLIT
# ============================================================
def main():
    
    # MOSTRAR LOGO SENAMHI
    mostrar_logo_senamhi()
    
    # Título
    st.markdown("""
    <div style="text-align: center; padding: 0.5rem 0;">
        <h2 style="font-size: clamp(1.2rem, 4vw, 2rem);">🦙 Monitoreo Diaria - Temperatura, Precipitación y Afectación de Alpacas</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # BARRA LATERAL
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
            - **🖱️ Deslizar**: Arrastra el mouse ← →
            - **🔍 Zoom**: Rueda del mouse o pellizcar
            - **👆 Seleccionar**: Usa botones de la barra
            - **📊 Ver valores**: Pasa el cursor sobre cualquier punto
            """)
        
        if st.button("🔄 Actualizar datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # CONFIGURACIÓN
    GOOGLE_SHEETS_ID = '11UWULdTZL2tKKpeGRETXOHvQt_3jHxIMgap2lfkDpro'
    SHEET_NAME_SINTOMAS = 'sintomas'
    SHEET_NAME_TEMPERATURAS = 'temperaturas'

    # IMÁGENES - RUTAS
    os.makedirs('imagenes', exist_ok=True)
    
    IMAGES = {
        'enferma': os.path.join('imagenes', 'enferma.png'),
        'muerta': os.path.join('imagenes', 'muerta.png'),
        'aborto': os.path.join('imagenes', 'aborto.png')
    }

    zoom_meses = st.session_state.get('zoom_periodo', None)
    es_movil = False

    with st.spinner('🔄 Cargando datos desde Google Sheets...'):
        df = cargar_datos(GOOGLE_SHEETS_ID, SHEET_NAME_SINTOMAS, SHEET_NAME_TEMPERATURAS)

    if df is not None and not df.empty:
        with st.spinner('📊 Generando gráfica interactiva...'):
            fig = crear_grafica(df, IMAGES, zoom_meses, es_movil)

        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['toImage', 'sendDataToCloud'],
                'displaylogo': False,
                'scrollZoom': True,
                'responsive': True,
                'modeBarButtonsToAdd': [
                    'zoom2d',
                    'pan2d',
                    'select2d',
                    'lasso2d',
                    'zoomIn2d',
                    'zoomOut2d',
                    'autoScale2d',
                    'resetScale2d'
                ]
            })

            with st.expander("📊 Ver estadísticas de los datos", expanded=False):
                if es_movil:
                    col1, col2, col3 = st.columns(1)
                else:
                    col1, col2, col3 = st.columns(3)
                
                if 'Enfermos' in df.columns and not df['Enfermos'].dropna().empty:
                    col1.metric("🦙 Total Enfermos", f"{df['Enfermos'].sum():.0f}")
                if 'Muertos' in df.columns and not df['Muertos'].dropna().empty:
                    col2.metric("💀 Total Muertos", f"{df['Muertos'].sum():.0f}")
                if 'Abortos' in df.columns and not df['Abortos'].dropna().empty:
                    col3.metric("⚠️ Total Abortos", f"{df['Abortos'].sum():.0f}")

                st.dataframe(df, use_container_width=True)

            st.success("✅ ¡Gráfica cargada exitosamente!")
        else:
            st.error("❌ Error al generar la gráfica")
    else:
        st.error("❌ No se pudieron cargar los datos")

if __name__ == "__main__":
    main()
