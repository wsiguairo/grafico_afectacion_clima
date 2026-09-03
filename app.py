# ============================================================
# FUNCIÓN PARA CREAR LA GRÁFICA - FECHA ÚNICA ROBUSTA
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

    img_enferma = image_to_base64(images_paths.get('enferma', ''))
    img_muerta = image_to_base64(images_paths.get('muerta', ''))
    img_aborto = image_to_base64(images_paths.get('aborto', ''))

    fig = go.Figure()

    # ============================================================
    # PRECIPITACIÓN - SIN HOVER
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
    # TEMPERATURA - SIN HOVER
    # ============================================================
    if 'Temperaturas minimas  (°C)' in df.columns and not df['Temperaturas minimas  (°C)'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['fecha'],
            y=df['Temperaturas minimas  (°C)'],
            mode='lines+markers',
            name='Temperatura mínima',
            line=dict(color='#2563EB', width=2.5),
            marker=dict(size=4, color='#2563EB'),
            opacity=0.9,
            hoverinfo='skip'
        ))

    # ============================================================
    # VIENTO - SIN HOVER
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
    # ALPACAS ENFERMAS - CURVA SUAVIZADA (SOLO VISUAL)
    # ============================================================
    if len(enfermos_smooth) > 0:
        fig.add_trace(go.Scatter(
            x=fecha_smooth,
            y=enfermos_smooth,
            mode='lines',
            name='Alpacas enfermas',
            line=dict(color='#8B0000', width=3.5),
            opacity=0.9,
            fill='tozeroy',
            fillgradient=dict(
                type='vertical',
                colorscale=[[0, 'rgba(139, 0, 0, 0)'], [1, 'rgba(139, 0, 0, 0.15)']]
            ),
            yaxis='y2',
            hoverinfo='skip',  # SIN HOVER - SOLO VISUAL
            showlegend=True
        ))

    # ============================================================
    # ALPACAS MUERTAS - SIN HOVER
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
    # ABORTOS - SIN HOVER
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
    # TRACE INVISIBLE ROBUSTO - COINCIDENCIA EXACTA CON CURVA
    # ============================================================
    # Preparar datos para el hover
    df_hover = df.copy()
    
    # Asegurar que todas las columnas existan
    for col in ['Precipitacion ', 'Temperaturas minimas  (°C)', 'Vel. viento (Km/h)', 
                'Enfermos', 'Muertos', 'Abortos']:
        if col not in df_hover.columns:
            df_hover[col] = np.nan
    
    # Rellenar NaN con 0 para posicionamiento
    df_hover['Enfermos'] = df_hover['Enfermos'].fillna(0)
    df_hover['Muertos'] = df_hover['Muertos'].fillna(0)
    df_hover['Abortos'] = df_hover['Abortos'].fillna(0)
    
    # Crear el texto del hover con TODOS los valores REALES
    hover_texts = []
    for _, row in df_hover.iterrows():
        texto = f"<b>📅 {row['fecha'].strftime('%d/%m/%Y')}</b><br>"
        
        if pd.notna(row['Precipitacion ']) and row['Precipitacion '] > 0:
            texto += f"<b>💧 Precipitación:</b> {row['Precipitacion ']:.0f} mm<br>"
        if pd.notna(row['Temperaturas minimas  (°C)']):
            texto += f"<b>🌡️ Temperatura mínima:</b> {row['Temperaturas minimas  (°C)']:.1f} °C<br>"
        if pd.notna(row['Vel. viento (Km/h)']) and row['Vel. viento (Km/h)'] > 0:
            texto += f"<b>💨 Viento:</b> {row['Vel. viento (Km/h)']:.0f} Km/h<br>"
        if row['Enfermos'] > 0:
            texto += f"<b>🦙 Alpacas enfermas:</b> {row['Enfermos']:.0f}<br>"
        if row['Muertos'] > 0:
            texto += f"<b>💀 Alpacas muertas:</b> {row['Muertos']:.0f}<br>"
        if row['Abortos'] > 0:
            texto += f"<b>⚠️ Abortos:</b> {row['Abortos']:.0f}<br>"
        
        hover_texts.append(texto)
    
    # ✅ TRACE INVISIBLE EN LA MISMA POSICIÓN QUE LA CURVA
    # Usamos los valores REALES de enfermos como posición Y
    # Si no hay datos de enfermos, usamos un valor pequeño pero visible
    y_positions = df_hover['Enfermos'].values
    
    # Si todos los enfermos son 0, usar una posición pequeña para hover
    if y_positions.max() == 0:
        y_positions = np.ones(len(df_hover)) * 0.5
    
    # Añadir un pequeño offset para evitar que se superponga exactamente
    # y que el hover sea más fácil de activar
    y_positions = y_positions * 1.0  # Sin offset, coincide exactamente
    
    fig.add_trace(go.Scatter(
        x=df_hover['fecha'],
        y=y_positions,  # ✅ MISMA POSICIÓN QUE DATOS REALES
        mode='markers',
        name='',
        marker=dict(
            size=20,  # Tamaño grande para capturar hover fácilmente
            color='rgba(255, 0, 0, 0)',  # Completamente transparente
            opacity=0,
            line=dict(width=0)
        ),
        yaxis='y2',
        showlegend=False,
        hoverinfo='text',
        text=hover_texts,
        hoverlabel=dict(
            bgcolor='white',
            font_size=14 if not es_movil else 12,
            font_color='#2c3e50',
            bordercolor='#bdc3c7',
            borderwidth=2,
            font_family='Arial'
        ),
        hovertemplate='%{text}<extra></extra>'  # Limpia el formato extra
    ))

    # ============================================================
    # IMÁGENES PEQUEÑAS (TAMAÑO 8) - SOLO EN PC
    # ============================================================
    images_plotly = []
    y_offset = 0.2

    if not es_movil:
        if img_enferma is not None and len(enfermos_smooth) > 0:
            for idx in [0, -1]:
                images_plotly.append({
                    'source': f"data:image/png;base64,{img_enferma}",
                    'xref': 'x',
                    'yref': 'y2',
                    'x': fecha_smooth[idx],
                    'y': float(enfermos_smooth[idx]),
                    'sizex': 8,
                    'sizey': 8,
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
                        'sizex': 8,
                        'sizey': 8,
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
                            'sizex': 8,
                            'sizey': 8,
                            'xanchor': 'center',
                            'yanchor': 'middle',
                            'layer': 'above'
                        })

    # ============================================================
    # RANGOS
    # ============================================================
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

    # ============================================================
    # ZOOM INICIAL
    # ============================================================
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

    # ============================================================
    # TICKS
    # ============================================================
    if es_movil:
        fecha_ticks = pd.date_range(start=df['fecha'].min(), end=df['fecha'].max(), freq='MS')
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

    # ============================================================
    # LAYOUT
    # ============================================================
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
