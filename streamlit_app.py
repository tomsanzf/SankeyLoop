import streamlit as st
import plotly.graph_objects as go
import re

# -- Page Setup --
st.set_page_config(layout="wide", page_title="Sankey Gen 2.0")
st.title("📊 Sankey Gen 2.0")

# 1. SIDEBAR FOR UI
with st.sidebar:
    st.header("Settings")
    
    # Connect these to the variables below
    node_opacity = st.slider("Link Opacity", 0.1, 1.0, 0.4)
    orientation_label = st.radio("Orientation", ["Horizontal", "Vertical"])
    orientation_setting = "h" if orientation_label == "Horizontal" else "v"
    
    st.divider()
    st.subheader("Node Styling")
    node_pad = st.slider("Node Padding", 10, 100, 40)
    node_thickness = st.slider("Node Thickness", 10, 50, 20)
    value_unit = st.text_input("Value Unit", "kW")

# 2. INPUT AREA
sankey_input_text = st.text_area(
    "Paste your data here (Source [Value] Target #Hex)", 
    placeholder="Wages [5000] Budget #22c55e",
    height=300
)

# 3. HELPER FUNCTIONS
def hex_to_rgba(hex_code, opacity):
    """Converts #RRGGBB to rgba(r, g, b, opacity)"""
    hex_code = hex_code.lstrip('#')
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
        match = re.match(r'(.+?)\s*\[(\d+)\]\s*(.+?)(?:\s*#([0-9a-fA-F]{6}))?$', line)
        if match:
            s_name, val, t_name, hex_c = match.group(1).strip(), int(match.group(2)), match.group(3).strip(), match.group(4)

            for name in [s_name, t_name]:
                if name not in label_to_index:
                    label_to_index[name] = len(unique_labels)
                    unique_labels.append(name)

            sources.append(label_to_index[s_name])
            targets.append(label_to_index[t_name])
            values.append(val)
            
            # Apply the opacity slider to the colors
            if hex_c:
                colors.append(hex_to_rgba(hex_c, opacity))
            else:
                colors.append(f'rgba(0,0,0,{opacity/2})') # Default dim gray

    return sources, targets, values, unique_labels, colors

# 4. LOGIC & RENDERING
if sankey_input_text:
    try:
        src, tgt, val, labels, link_colors = parse_sankey_data(sankey_input_text, node_opacity)

        # Calculate flows for labels
        node_in = [0] * len(labels)
        node_out = [0] * len(labels)
        for i in range(len(src)):
            node_out[src[i]] += val[i]
            node_in[tgt[i]] += val[i]

        updated_labels = [
            f"{l}<br>{max(node_in[i], node_out[i])} {value_unit}" 
            for i, l in enumerate(labels)
        ]

        # Build Plotly Figure
        fig = go.Figure(data=[go.Sankey(
            orientation = orientation_setting,
            node = dict(
                pad = node_pad,
                thickness = node_thickness,
                label = updated_labels,
                color = "#1e293b", # Professional dark nodes
                line = dict(color = "white", width = 0.5)
            ),
            link = dict(
                source = src,
                target = tgt,
                value = val,
                color = link_colors,
                hovertemplate = f'<b>%{{source.label}}</b> → <b>%{{target.label}}</b><br>Value: %{{value}} {value_unit}<extra></extra>'
            )
        )])

        fig.update_layout(height=700, margin=dict(l=10, r=10, t=10, b=10))
        
        # Display in Streamlit
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Check your data format! Error: {e}")
else:
    st.info("Waiting for data... Paste your Sankeymatic code above to generate the diagram.")
