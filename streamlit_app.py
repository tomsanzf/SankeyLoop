import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import re
from streamlit import column_config # Modern way to access table settings

# -- 1. Page Configuration --
st.set_page_config(
    layout="wide", 
    page_title="SankeyLoop", 
    page_icon="🔄"
)

# -- 2. Theme & UI Styling --
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: visible;}
    .stTitle { font-size: 2.5rem !important; font-weight: 800 !important; }
    div[data-testid="stStatusWidget"] { background-color: #2563eb; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("SankeyLoop")

# -- 3. Sidebar Parameters --
with st.sidebar:
    st.header("Settings")
    
    theme_mode = st.radio("Background Theme", ["Light", "Dark"])
    bg_color = "white" if theme_mode == "Light" else "#121212"
    default_text = "#1e293b" if theme_mode == "Light" else "#f8fafc"
    
    st.divider()
    
    st.subheader("Flow & Node")
    node_opacity = st.slider("Link Opacity", 0.1, 1.0, 0.45)
    node_spacing = st.slider("Vertical Spacing", 0, 100, 40)
    node_thickness = st.slider("Node Thickness", 5, 50, 20)
    arrow_size = st.slider("Arrow Head Size", 0, 30, 15)

    st.divider()

    st.subheader("Labels")
    label_color = st.color_picker("Font Color", value=default_text)
    label_size = st.slider("Font Size", 8, 30, 12)
    
    st.divider()
    
    st.subheader("Layout")
    arrangement_ui = st.selectbox("Arrangement", ["Snap", "Perpendicular", "Freeform"], index=0)
    node_arrangement = arrangement_ui.lower()

    align_ui = st.radio("Horizontal Alignment", ["Justify", "Left", "Center", "Right"], horizontal=True)
    node_alignment = align_ui.lower()
    
    st.divider()
    
    st.subheader("Config")
    orientation_label = st.radio("Flow Direction", ["Horizontal", "Vertical"])
    orientation_setting = "h" if orientation_label == "Horizontal" else "v"
    value_unit = st.text_input("Value Unit", "kW")
    
    st.divider()
    
    st.subheader("Canvas Size")
    fig_width = st.number_input("Width (px)", min_value=300, max_value=3000, value=1200)
    fig_height = st.number_input("Height (px)", min_value=300, max_value=2000, value=700)

# -- 4. Helper Functions --
def hex_to_rgba(hex_code, opacity):
    if not hex_code or not isinstance(hex_code, str): return f'rgba(150,150,150,{opacity})'
    hex_code = hex_code.lstrip('#')
    if len(hex_code) == 3: hex_code = ''.join([c*2 for c in hex_code])
    try:
        r, g, b = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        return f'rgba({r}, {g}, {b}, {opacity})'
    except: return f'rgba(150,150,150,{opacity})'

def parse_sankey_text(text, opacity):
    lines = text.strip().split('\n')
    sources, targets, values, colors = [], [], [], []
    unique_labels = []
    label_to_index = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'): continue
        match = re.match(r'(.+?)\s*\[(\d+)\]\s*(.+?)(?:\s*#([0-9a-fA-F]{3,6}))?$', line)
        if match:
            s_name, val, t_name, hex_c = match.group(1).strip(), int(match.group(2)), match.group(3).strip(), match.group(4)
            for name in [s_name, t_name]:
                if name not in label_to_index:
                    label_to_index[name] = len(unique_labels); unique_labels.append(name)
            sources.append(label_to_index[s_name]); targets.append(label_to_index[t_name])
            values.append(val); colors.append(hex_to_rgba(hex_c, opacity) if hex_c else f'rgba(150,150,150,{opacity})')
    return sources, targets, values, unique_labels, colors

# -- 5. Data Input Section --
st.subheader("Data Input")
input_mode = st.radio("Input Method:", ["Interactive Table", "SankeyMatic Text"], horizontal=True)

if input_mode == "SankeyMatic Text":
    default_text = """Steam [88] HX1 #FF0000
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
    sankey_input_text = st.text_area("Paste Text", value=default_text, height=300)
    src, tgt, val, labels, link_colors = parse_sankey_text(sankey_input_text, node_opacity)

else:
    col1, col2 = st.columns([2, 1])
    with col2:
        use_picker = st.toggle("Enable Color Picker", value=True)
    
    # Starting Data
    df_init = pd.DataFrame([
        {"Source": "Steam", "Target": "HX1", "Value": 88, "Color": "#FF0000"},
        {"Source": "HX1", "Target": "Tank1", "Value": 88, "Color": "#FFD700"},
        {"Source": "Tank1", "Target": "Tank2", "Value": 200, "Color": "#FFD700"}
    ])
    
    # THE FIX: Using CamelCase (NumberColumn, TextColumn, ColorColumn)
    c_config = {
        "Value": st.column_config.NumberColumn("Value", format="%d", min_value=0),
        "Source": st.column_config.TextColumn("Source Node"),
        "Target": st.column_config.TextColumn("Target Node")
    }
    
    if use_picker:
        c_config["Color"] = st.column_config.ColorColumn("Link Color")
    else:
        c_config["Color"] = st.column_config.TextColumn("Hex Code (#)")
    
    edited_df = st.data_editor(
        df_init, 
        num_rows="dynamic", 
        use_container_width=True, 
        column_config=c_config
    )
    
    # -- Process Table Data --
    # Remove any rows that are completely empty to prevent errors
    edited_df = edited_df.dropna(subset=['Source', 'Target', 'Value'])
    
    if not edited_df.empty:
        all_nodes = pd.concat([edited_df['Source'], edited_df['Target']]).unique()
        labels = list(all_nodes)
        l2i = {label: i for i, label in enumerate(labels)}
        
        src = [l2i[s] for s in edited_df['Source']]
        tgt = [l2i[t] for t in edited_df['Target']]
        val = edited_df['Value'].tolist()
        # Handle colors safely
        link_colors = [hex_to_rgba(c, node_opacity) for c in edited_df['Color']]
    else:
        # Fallback if the table is cleared out
        src, tgt, val, labels, link_colors = [], [], [], [], []

# -- 6. Processing & Drawing --
if labels: # Only try to draw if we actually have nodes!
    try:
        node_in, node_out = [0]*len(labels), [0]*len(labels)
        for i in range(len(src)):
            node_out[src[i]] += val[i]
            node_in[tgt[i]] += val[i]

        updated_labels = [f"{l}<br>{max(node_in[i], node_out[i])} {value_unit}" for i, l in enumerate(labels)]

        fig = go.Figure(data=[go.Sankey(
            arrangement = node_arrangement,
            orientation = orientation_setting,
            textfont = dict(color = label_color, size = label_size),
            node = dict(
                pad = node_spacing, thickness = node_thickness, label = updated_labels,
                color = "#2563eb" if theme_mode == "Light" else "#60a5fa",
                line = dict(color = bg_color, width = 1), align = node_alignment
            ),
            link = dict(
                source = src, target = tgt, value = val, color = link_colors,
                arrowlen = arrow_size,
                hovertemplate = f'%{{source.label}} → %{{target.label}}<br>Value: %{{value}} {value_unit}<extra></extra>'
            )
        )])

        fig.update_layout(
            width=fig_width, height=fig_height,
            paper_bgcolor=bg_color, plot_bgcolor=bg_color,
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=False)
    except Exception as e:
        st.error(f"⚠️ App logic error: {e}")
else:
    st.info("Start adding data to the table or paste text to see your SankeyLoop!")
