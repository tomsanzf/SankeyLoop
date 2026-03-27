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
    
    theme_mode = st.radio("Background Theme", ["Light", "Dark"])
    bg_color = "white" if theme_mode == "Light" else "#121212"
    default_text_color = "#1e293b" if theme_mode == "Light" else "#f8fafc"
    
    st.divider()
    
    st.subheader("🔥 Thermal Gradient")
    col_h1, col_h2 = st.columns(2)
    with col_h1: high_val = st.number_input("High Value", value=200)
    with col_h2: high_col = st.color_picker("High Color", "#FF0000") 
    
    col_m1, col_m2 = st.columns(2)
    with col_m1: mid_val = st.number_input("Mid Value", value=40)
    with col_m2: mid_col = st.color_picker("Mid Color", "#FFA500") 
    
    col_l1, col_l2 = st.columns(2)
    with col_l1: low_val = st.number_input("Low Value", value=0)
    with col_l2: low_col = st.color_picker("Low Color", "#0000FF") 

    st.divider()
    
    st.subheader("Flow & Node")
    node_opacity = st.slider("Link Opacity", 0.1, 1.0, 0.45)
    node_spacing = st.slider("Vertical Spacing", 0, 100, 40)
    node_thickness = st.slider("Node Thickness", 5, 50, 20)
    arrow_size = st.slider("Arrow Head Size", 0, 30, 15)

    st.subheader("Labels")
    label_color = st.color_picker("Font Color", value=default_text_color)
    label_size = st.slider("Font Size", 8, 30, 12)
    
    st.subheader("Config")
    value_unit = st.text_input("Value Unit", "kW")
    fig_width = st.number_input("Width (px)", value=1200)
    fig_height = st.number_input("Height (px)", value=700)

# -- 4. Interpolation & Color Keyword Logic --
def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    if len(hex_code) == 3: hex_code = ''.join([c*2 for c in hex_code])
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def interpolate_rgb(val, min_v, max_v, color1, color2):
    if max_v == min_v: return color1
    f = (val - min_v) / (max_v - min_v)
    f = max(0, min(1, f)) 
    rgb1, rgb2 = hex_to_rgb(color1), hex_to_rgb(color2)
    res = tuple(int(rgb1[i] + (rgb2[i] - rgb1[i]) * f) for i in range(3))
    return f"rgba({res[0]}, {res[1]}, {res[2]}, {node_opacity})"

def get_final_color(input_val):
    if not input_val: return f"rgba(150, 150, 150, {node_opacity})"
    
    # 1. NEW: Keyword Exceptions (Elec and Black)
    clean_val = str(input_val).strip().lower()
    if clean_val == "elec":
        return f"rgba(0, 255, 0, {node_opacity})" # Pure Green
    if clean_val == "black":
        return f"rgba(0, 0, 0, {node_opacity})" # Pure Black
    
    # 2. Hex Code Logic
    if clean_val.startswith('#'):
        rgb = hex_to_rgb(clean_val)
        return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {node_opacity})"
    
    # 3. Numeric Gradient Logic
    try:
        v = float(input_val)
        if v >= mid_val:
            return interpolate_rgb(v, mid_val, high_val, mid_col, high_col)
        else:
            return interpolate_rgb(v, low_val, mid_val, low_col, mid_col)
    except:
        return f"rgba(150, 150, 150, {node_opacity})"

# -- 5. Data Input Section --
st.subheader("Data Input")
input_mode = st.radio("Input Method:", ["Interactive Table", "Text Input"], horizontal=True)

# Default data optimized for launch
default_rows = [
    {"Source": "Natural Gas", "Target": "Boiler", "Value": 100, "Color": "Black"},
    {"Source": "Steam", "Target": "Process", "Value": 88, "Color": "150"},
    {"Source": "Process", "Target": "Return", "Value": 88, "Color": "65"},
    {"Source": "Elec Grid", "Target": "Chiller", "Value": 50, "Color": "Elec"},
    {"Source": "Chilled Water", "Target": "HVAC", "Value": 45, "Color": "7"}
]

if input_mode == "Text Input":
    text_repr = "\n".join([f"{d['Source']} [{d['Value']}] {d['Target']} {d['Color']}" for d in default_rows])
    sankey_input_text = st.text_area("Paste Flow Data", value=text_repr, height=300)
    
    lines = sankey_input_text.strip().split('\n')
    src, tgt, val, labels, link_colors = [], [], [], [], []
    l2i = {}
    for line in lines:
        match = re.match(r'(.+?)\s*\[(\d+)\]\s*(.+?)(?:\s*(\S+))?$', line.strip())
        if match:
            s_n, v, t_n, color_val = match.group(1).strip(), int(match.group(2)), match.group(3).strip(), match.group(4)
            for n in [s_n, t_n]:
                if n not in l2i: l2i[n] = len(labels); labels.append(n)
            src.append(l2i[s_n]); tgt.append(l2i[t_n]); val.append(v)
            link_colors.append(get_final_color(color_val))

else:
    edited_df = st.data_editor(pd.DataFrame(default_rows), num_rows="dynamic", use_container_width=True)
    
    active_df = edited_df.dropna(subset=['Source', 'Target', 'Value'])
    if not active_df.empty:
        labels = list(pd.concat([active_df['Source'], active_df['Target']]).unique())
        l2i = {label: i for i, label in enumerate(labels)}
        src = [l2i[s] for s in active_df['Source']]
        tgt = [l2i[t] for t in active_df['Target']]
        val = active_df['Value'].tolist()
        link_colors = [get_final_color(c) for c in active_df['Color']]
    else:
        src, tgt, val, labels, link_colors = [], [], [], [], []

# -- 6. Drawing --
if labels:
    node_in, node_out = [0]*len(labels), [0]*len(labels)
    for i in range(len(src)):
        node_out[src[i]] += val[i]
        node_in[tgt[i]] += val[i]
    u_labels = [f"{l}<br>{max(node_in[i], node_out[i])} {value_unit}" for i, l in enumerate(labels)]

    fig = go.Figure(data=[go.Sankey(
        textfont = dict(color = label_color, size = label_size),
        node = dict(pad = node_spacing, thickness = node_thickness, label = u_labels,
                    color = "#2563eb" if theme_mode == "Light" else "#60a5fa",
                    line = dict(color = bg_color, width = 1)),
        link = dict(source = src, target = tgt, value = val, color = link_colors, arrowlen = arrow_size)
    )])
    fig.update_layout(width=fig_width, height=fig_height, paper_bgcolor=bg_color, margin=dict(l=40, r=40, t=40, b=40))
    st.plotly_chart(fig, use_container_width=False)
