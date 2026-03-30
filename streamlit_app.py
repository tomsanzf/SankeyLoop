import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import re

# ==========================================
# MODULE 1: SETUP & SIDEBAR (THE CONTROLS)
# ==========================================
st.set_page_config(layout="wide", page_title="SankeyLoop", page_icon="🔄")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: visible;}
    .stTitle { font-size: 2.2rem !important; font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("SankeyLoop")

with st.sidebar:
    st.header("Parameters")
    theme_mode = st.radio("UI Theme", ["Light", "Dark"])
    bg_color = "white" if theme_mode == "Light" else "#121212"
    default_text_color = "#1e293b" if theme_mode == "Light" else "#f8fafc"
    
    st.divider()
    st.subheader("Flow Orientation")
    orientation_label = st.radio("Direction", ["Horizontal", "Vertical"], horizontal=True)
    orientation_setting = "h" if orientation_label == "Horizontal" else "v"

    st.divider()
    st.subheader("🔥 Thermal Gradient")
    col_h1, col_h2 = st.columns(2)
    with col_h1: high_val = st.number_input("High Threshold", value=180.0)
    with col_h2: high_col = st.color_picker("High Color", "#FF0000") 
    col_m1, col_m2 = st.columns(2)
    with col_m1: mid_val = st.number_input("Mid Threshold", value=45.0)
    with col_m2: mid_col = st.color_picker("Mid Color", "#FFA500") 
    col_l1, col_l2 = st.columns(2)
    with col_l1: low_val = st.number_input("Low Threshold", value=5.0)
    with col_l2: low_col = st.color_picker("Low Color", "#0000FF") 

    st.divider()
    st.subheader("Layout & Scaling")
    align_ui = st.radio("Node Alignment", ["Justify", "Left", "Center", "Right"], index=2, horizontal=True)
    node_alignment = align_ui.lower()
    arrangement_ui = st.selectbox("Node Arrangement", ["Snap", "Perpendicular", "Freeform"], index=0)
    node_arrangement = arrangement_ui.lower()
    
    v_margin = st.slider("Vertical Margin (Scaling)", 0, 500, 100)
    h_margin = st.slider("Horizontal Margin (Padding)", 0, 500, 50)
    
    st.divider()
    st.subheader("Visual Geometry")
    node_spacing = st.slider("Node Pad (Gap)", 0, 200, 50) 
    node_thickness = st.slider("Node Width", 5, 50, 20)
    node_opacity = st.slider("Link Opacity", 0.1, 1.0, 0.45)
    arrow_size = st.slider("Arrow Head Size", 0, 50, 15)
    
    st.divider()
    st.subheader("Typography & Canvas")
    label_size = st.slider("Font Size", 8, 30, 12)
    label_color = st.color_picker("Font Color", value=default_text_color)
    fig_width = st.number_input("Canvas Width (px)", value=1200)
    fig_height = st.number_input("Canvas Height (px)", value=800)
    value_unit = st.text_input("Value Unit", "kW")

# ==========================================
# MODULE 2: LOGIC FUNCTIONS (THE BRAIN)
# ==========================================
def safe_float(val):
    if val is None: return 0.0
    try:
        return float(str(val).replace(',', '.').strip())
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

def get_link_color(input_val):
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

# ==========================================
# MODULE 3: DATA HANDLING (THE INPUT)
# ==========================================
st.subheader("Data Input")
input_mode = st.radio("Input Method:", ["Interactive Table", "Text Input"], horizontal=True)

default_dataset = [
    {"Source": "Natural Gas", "Target": "Boiler", "Value": "400", "Color": "Black"},
    {"Source": "Tank1", "Target": "Tank2", "Value": "-50,5", "Color": "60"},
    {"Source": "Steam", "Target": "Process", "Value": "88,3", "Color": "160"},
    {"Source": "Elec Grid", "Target": "Chiller", "Value": "100", "Color": "Elec"}
]

src, tgt, val, labels, link_colors = [], [], [], [], []
l2i = {}

if input_mode == "Text Input":
    text_repr = "\n".join([f"{d['Source']} [{d['Value']}] {d['Target']} {d['Color']}" for d in default_dataset])
    raw_input = st.text_area("Flow Specification", value=text_repr, height=300)
    lines = raw_input.strip().split('\n')
    for line in lines:
        match = re.match(r'(.+?)\s*\[(.+?)\]\s*(.+?)(?:\s*(\S+))?$', line.strip())
        if match:
            s_name, v_str, t_name, color_val = match.group(1).strip(), match.group(2), match.group(3).strip(), match.group(4)
            v = safe_float(v_str)
            # Negative Value Inversion Logic
            if v < 0: s_final, t_final, v_final = t_name, s_name, abs(v)
            else: s_final, t_final, v_final = s_name, t_name, v
            
            for n in [s_final, t_final]:
                if n not in l2i: l2i[n] = len(labels); labels.append(n)
            src.append(l2i[s_final]); tgt.append(l2i[t_final]); val.append(v_final)
            link_colors.append(get_link_color(color_val))
else:
    col_config = {"Value": st.column_config.TextColumn("Value"), "Source": st.column_config.TextColumn("Source Node"), "Target": st.column_config.TextColumn("Target Node"), "Color": st.column_config.TextColumn("Color/Temp")}
    df = st.data_editor(pd.DataFrame(default_dataset), num_rows="dynamic", use_container_width=True, column_config=col_config)
    active_df = df.dropna(subset=['Source', 'Target', 'Value'])
    if not active_df.empty:
        for _, row in active_df.iterrows():
            s_n, t_n, v_s, c_v = str(row['Source']).strip(), str(row['Target']).strip(), row['Value'], row['Color']
            v = safe_float(v_s)
            # Negative Value Inversion Logic
            if v < 0: s_f, t_f, v_f = t_n, s_n, abs(v)
            else: s_f, t_f, v_f = s_n, t_n, v
            
            for n in [s_f, t_f]:
                if n not in l2i: l2i[n] = len(labels); labels.append(n)
            src.append(l2i[s_f]); tgt.append(l2i[t_f]); val.append(v_f)
            link_colors.append(get_link_color(c_v))

# ==========================================
# MODULE 4: RENDERING (THE OUTPUT)
# ==========================================
if labels:
    try:
        node_in, node_out = [0]*len(labels), [0]*len(labels)
        for i in range(len(src)):
            node_out[src[i]] += val[i]
            node_in[tgt[i]] += val[i]
        
        display_labels = [f"{l}<br>{int(round(max(node_in[i], node_out[i]), 0))} {value_unit}" for i, l in enumerate(labels)]
        meta = [[labels[i], node_in[i], node_out[i]] for i in range(len(labels))]

        fig = go.Figure(data=[go.Sankey(
            orientation = orientation_setting,
            arrangement = node_arrangement,
            textfont = dict(color = label_color, size = label_size),
            node = dict(
                pad = node_spacing, thickness = node_thickness, label = display_labels,
                align = node_alignment, color = "#2563eb" if theme_mode == "Light" else "#60a5fa",
                line = dict(color = bg_color, width = 1),
                customdata = meta,
                hovertemplate = '<b>%{customdata[0]}</b><br>Input: %{customdata[1]:.0f}<br>Output: %{customdata[2]:.0f}<extra></extra>'
            ),
            link = dict(
                source = src, target = tgt, value = val, color = link_colors, arrowlen = arrow_size,
                customdata = labels,
                hovertemplate = '<b>%{source.customdata[0]}</b> → <b>%{target.customdata[0]}</b><br>Flow: %{value:.0f} ' + value_unit + '<extra></extra>'
            )
        )])
        
        fig.update_layout(width=fig_width, height=fig_height, paper_bgcolor=bg_color, plot_bgcolor=bg_color,
                          margin=dict(l=h_margin, r=h_margin, t=v_margin, b=v_margin))
        st.plotly_chart(fig, use_container_width=False)
        
        if input_mode == "Interactive Table":
            st.download_button("Export Configuration (CSV)", active_df.to_csv(index=False), "sankey_audit.csv", "text/csv")
    except Exception as e:
        st.error(f"Execution Error: {e}")
