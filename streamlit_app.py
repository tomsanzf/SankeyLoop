import streamlit as st
import plotly.graph_objects as go
import re

# -- 1. Page Configuration --
st.set_page_config(layout="wide", page_title="SankeyLoop")

# -- 2. Theme & Title --
# Custom CSS to handle the background toggle and hide standard UI clutter
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

st.title("SankeyLoop")

# -- 3. Sidebar Parameters --
with st.sidebar:
    st.header("Settings")
    
    # Theme Toggle
    theme_mode = st.radio("Background Theme", ["Light", "Dark"])
    bg_color = "white" if theme_mode == "Light" else "#121212"
    text_color = "#1e293b" if theme_mode == "Light" else "white"
    
    st.divider()
    
    # Flow & Node Settings
    node_opacity = st.slider("Link Opacity", 0.1, 1.0, 0.45)
    node_spacing = st.slider("Node Spacing", 0, 100, 40) # Renamed from Padding
    node_thickness = st.slider("Node Thickness", 5, 50, 20)
    arrow_size = st.slider("Arrow Head Size", 0, 20, 10)
    
    st.divider()
    
    # Orientation & Units
    orientation_label = st.radio("Flow Direction", ["Horizontal", "Vertical"])
    orientation_setting = "h" if orientation_label == "Horizontal" else "v"
    value_unit = st.text_input("Value Unit", "kW")
    
    st.divider()
    
    # Figure Size
    st.subheader("Canvas Size")
    fig_height = st.number_input("Figure Height (px)", min_value=300, max_value=2000, value=700)

# -- 4. Default Data & Input Area --
default_data = """Steam [88] HX1 #FF0000
HX1 [88] Tank1 #FFD700
Steam [50] HX2 #FF0000
Tank1 [200] Tank2 #FFD700
HX2 [50] Tank2 #FFA100
Tank2 [250] HX3 #FFCC00
HX3 [250] Chiller #C812BF
Elec [100] Chiller #00FF00
Chiller [263] Cooling Tower #2858B4
Tank3 [100] Cooling Tower #05B1EA
Chiller [88] HP #2858B4
Elec [25] HP #00FF00
HP [113] Tank1 #FFD700"""

sankey_input_text = st.text_area(
    "Data Input (Format: Source [Value] Target #Hex)", 
    value=default_data,
    height=300,
    help="Diagram updates automatically when you click outside this box or hit Ctrl+Enter."
)

# -- 5. Helper Functions --
def hex_to_rgba(hex_code, opacity):
    hex_code = hex_code.lstrip('#')
    # Support 3-digit hex
    if len(hex_code) == 3:
        hex_code = ''.join([c*2 for c in hex_code])
    r, g, b = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

def parse_sankey_data(text, opacity):
    lines = text.strip().split('\n')
    sources, targets, values, colors = [], [], [], []
    unique_labels = []
    label_to_index = {}

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'): continue

        # Regex: Source [Value] Target #Hex
        match = re.match(r'(.+?)\s*\[(\d+)\]\s*(.+?)(?:\s*#([0-9a-fA-F]{3,6}))?$', line)
        if match:
            s_name, val, t_name, hex_c = match.group(1).strip(), int(match.group(2)), match.group(3).strip(), match.group(4)

            for name in [s_name, t_name]:
                if name not in label_to_index:
                    label_to_index[name] = len(unique_labels)
                    unique_labels.append(name)

            sources.append(label_to_index[s_name])
            targets.append(label_to_index[t_name])
            values.append(val)
            colors.append(hex_to_rgba(hex_c, opacity) if hex_c else f'rgba(150,150,150,{opacity})')

    return sources, targets, values, unique_labels, colors

# -- 6. Processing & Drawing --
if sankey_input_text:
    try:
        src, tgt, val, labels, link_colors = parse_sankey_data(sankey_input_text, node_opacity)

        # Calculate Flow Labels
        node_in, node_out = [0]*len(labels), [0]*len(labels)
        for i in range(len(src)):
            node_out[src[i]] += val[i]
            node_in[tgt[i]] += val[i]

        updated_labels = [f"{l}<br>{max(node_in[i], node_out[i])} {value_unit}" for i, l in enumerate(labels)]

        # Build Figure
        fig = go.Figure(data=[go.Sankey(
            orientation = orientation_setting,
            node = dict(
                pad = node_spacing,
                thickness = node_thickness,
                label = updated_labels,
                color = "#2563eb" if theme_mode == "Light" else "#3b82f6",
                line = dict(color = bg_color, width = 1)
            ),
            link = dict(
                source = src,
                target = tgt,
                value = val,
                color = link_colors,
                arrowlen = arrow_size,
                hovertemplate = f'%{{source.label}} → %{{target.label}}<br>Value: %{{value}} {value_unit}<extra></extra>'
            )
        )])

        fig.update_layout(
            height=fig_height,
            paper_bgcolor=bg_color,
            plot_bgcolor=bg_color,
            font_color=text_color,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"⚠️ Error parsing data: {e}")
