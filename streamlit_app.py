import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import re

# -- 1. Page Configuration --
st.set_page_config(layout="wide", page_title="SankeyLoop", page_icon="🔄")

# -- 2. UI Styling --
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: visible;}
    .stTitle { font-size: 2.5rem !important; font-weight: 800 !important; color: #1e293b; }
    </style>
    """, unsafe_allow_html=True)

st.title("SankeyLoop")

# -- 3. Sidebar Parameters --
with st.sidebar:
    st.header("Settings")
    theme_mode = st.radio("Theme", ["Light", "Dark"])
    bg_color = "white" if theme_mode == "Light" else "#121212"
    default_text_color = "#1e293b" if theme_mode == "Light" else "#f8fafc"
    
    st.divider()
    st.subheader("🔥 Thermal Gradient")
    col_h1, col_h2 = st.columns(2)
    with col_h1: high_val = st.number_input("High", value=180.0)
    with col_h2: high_col = st.color_picker("H-Col", "#FF0000") 
    col_m1, col_m2 = st.columns(2)
    with col_m1: mid_val = st.number_input("Mid", value=45.0)
    with col_m2: mid_col = st.color_picker("M-Col", "#FFA500") 
    col_l1, col_l2 = st.columns(2)
    with col_l1: low_val = st.number_input("Low", value=5.0)
    with col_l2: low_col = st.color_picker("L-Col", "#0000FF") 

    st.divider()
    st.subheader("Layout")
    arrangement_ui = st.selectbox("Arrangement", ["Snap", "Perpendicular", "Freeform"], index=0)
    node_arrangement = arrangement_ui.lower()
    align_ui = st.radio("Alignment", ["Justify", "Left", "Center", "Right"], horizontal=True)
    node_alignment = align_ui.lower()

    st.divider()
    st.subheader("Visuals")
    node_opacity = st.slider("Opacity", 0.1, 1.0, 0.45)
    node_spacing = st.slider("Spacing", 0, 100, 40)
    node_thickness = st.slider("Thickness", 5, 50, 20)
    label_size = st.slider("Font Size", 8, 30, 12)
    label_color = st.color_picker("Font Color", value=default_text_color)
    
    value_unit = st.text_input("Unit", "kW")
    fig_width = st.number_input("Width (px)", value=1200)
    fig_height = st.number_input("Height (px)", value=800)

# -- 4. Core Logic --
def safe_float(val):
    if val is None: return 0.0
    try:
        clean_val = str(val).replace(',', '.').strip()
        return float(clean_val)
    except: return 0.0

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    if len(hex_code) == 3: hex_code = ''.join([c*2 for c in hex_code])
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def interpolate_rgb(val, min_v, max_v, color1, color2):
    if max_v == min_v: return color1
    f = max(0, min(1, (val - min_v) / (max_v - min_v)))
    rgb1, rgb2 = hex_to_rgb(color1), hex_to_rgb(color2)
    res = tuple(int(rgb1[i] + (rgb2[i] - rgb1[i]) * f) for i in range(3))
    return f"rgba({res[0]}, {res[1]}, {res[2]}, {node_opacity})"

def get_final_color(input_val):
    if not input_val: return f"rgba(150, 150, 150, {node_opacity})"
    clean_str = str(input_val).strip().lower()
    if clean_str == "elec": return f"rgba(0, 200, 0, {node_opacity})"
    if clean_str == "black": return f"rgba(0, 0, 0, {node_opacity})"
    if clean_str.startswith('#'):
        try:
            rgb = hex_to_rgb(clean_str)
            return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {node_opacity})"
        except: return f"rgba(150, 150, 150, {node_opacity})"
    v = safe_float(input_val)
    if v >= mid_val: return interpolate_rgb(v, mid_val, high_val, mid_col, high_col)
    else: return interpolate_rgb(v, low_val, mid_val, low_col, mid_col)

# -- 5. Data Input --
st.subheader("Data Input")
input_mode = st.radio("Method:", ["Interactive Table", "Text Input"], horizontal=True)

hero_data = [
    {"Source": "Natural Gas", "Target": "Boiler", "Value": "400", "Color": "Black"},
    {"Source": "Steam", "Target": "HX1", "Value": "88,333", "Color": "160"},
    {"Source": "HX1", "Target": "Tank1", "Value": "88,333", "Color": "85"},
    {"Source": "Elec Grid", "Target": "Chiller", "Value": "100", "Color": "Elec"}
]

if input_mode == "Text Input":
    text_repr = "\n".join([f"{d['Source']} [{d['Value']}] {d['Target']} {d['Color']}" for d in hero_data])
    sankey_input_text = st.text_area("Flow Data", value=text_repr, height=300)
    lines = sankey_input_text.strip().split('\n')
    src, tgt, val, labels, link_colors = [], [], [], [], []
    l2i = {}
    for line in lines:
        match = re.match(r'(.+?)\s*\[(.+?)\]\s*(.+?)(?:\s*(\S+))?$', line.strip())
        if match:
            s_n, v_str, t_n, color_val = match.group(1).strip(), match.group(2), match.group(3).strip(), match.group(4)
            for n in [s_n, t_n]:
                if n not in l2i: l2i[n] = len(labels); labels.append(n)
            src.append(l2i[s_n]); tgt.append(l2i[t_n])
            val.append(safe_float(v_str))
            link_colors.append(get_final_color(color_val))
else:
    c_config = {"Value": st.column_config.TextColumn("Value"), "Source": st.column_config.TextColumn("Source"), "Target": st.column_config.TextColumn("Target"), "Color": st.column_config.TextColumn("Color/Temp")}
    edited_df = st.data_editor(pd.DataFrame(hero_data), num_rows="dynamic", use_container_width=True, column_config=c_config)
    active_df = edited_df.dropna(subset=['Source', 'Target', 'Value'])
    if not active_df.empty:
        labels = list(pd.concat([active_df['Source'], active_df['Target']]).unique())
        l2i = {label: i for i, label in enumerate(labels)}
        src = [l2i[s] for s in active_df['Source']]
        tgt = [l2i[t] for t in active_df['Target']]
        val = [safe_float(v) for v in active_df['Value']]
        link_colors = [get_final_color(c) for c in active_df['Color']]
    else: src, tgt, val, labels, link_colors = [], [], [], [], []

# -- 6. Polished Rendering --
if labels:
    try:
        # Calculate sums for hover logic
        node_in, node_out = [0]*len(labels), [0]*len(labels)
        for i in range(len(src)):
            node_out[src[i]] += val[i]
            node_in[tgt[i]] += val[i]
        
        # 1. Rounding labels to 0 decimals for the diagram
        u_labels = [f"{l}<br>{int(round(max(node_in[i], node_out[i]), 0))} {value_unit}" for i, l in enumerate(labels)]
        
        # 2. Store metadata in customdata for clean hovers
        # Structure: [Clean Name, Total In, Total Out]
        node_metadata = [[labels[i], node_in[i], node_out[i]] for i in range(len(labels))]

        fig = go.Figure(data=[go.Sankey(
            arrangement = node_arrangement,
            textfont = dict(color = label_color, size = label_size),
            node = dict(
                pad = node_spacing, thickness = node_thickness, label = u_labels,
                align = node_alignment, color = "#2563eb" if theme_mode == "Light" else "#60a5fa",
                line = dict(color = bg_color, width = 1),
                customdata = node_metadata,
                # Hover on Nodes: Name, Sum In, Sum Out
                hovertemplate = '<b>%{customdata[0]}</b><br>Incoming: %{customdata[1]:.0f} ' + value_unit + '<br>Outgoing: %{customdata[2]:.0f} ' + value_unit + '<extra></extra>'
            ),
            link = dict(
                source = src, target = tgt, value = val, color = link_colors,
                # Hover on Links: Clean Names (Source -> Target) and the specific flow value
                customdata = labels, # To help link template access names
                hovertemplate = '<b>%{source.customdata[0]}</b> → <b>%{target.customdata[0]}</b><br>Flow Value: %{value:.0f} ' + value_unit + '<extra></extra>'
            )
        )])
        
        fig.update_layout(width=fig_width, height=fig_height, paper_bgcolor=bg_color, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig, use_container_width=False)
        if input_mode == "Interactive Table":
            st.download_button("📥 Download CSV", active_df.to_csv(index=False), "sankey_data.csv", "text/csv")
    except Exception as e:
        st.error(f"⚠️ App logic error: {e}")
