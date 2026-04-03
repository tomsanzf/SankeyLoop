import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import re
from dataclasses import dataclass

# ==========================================
# MODULE 1: CONFIGURATION DATACLASS
# ==========================================
@dataclass
class SankeyConfig:
    """Centralizes all sidebar/UI state into a single object."""
    theme_mode: str = "Light"
    orientation: str = "h"
    high_val: float = 180.0
    high_col: str = "#FF0000"
    mid_val: float = 45.0
    mid_col: str = "#FFA500"
    low_val: float = 5.0
    low_col: str = "#0000FF"
    node_alignment: str = "center"
    node_arrangement: str = "snap"
    v_margin: int = 100
    h_margin: int = 50
    node_spacing: int = 50
    node_thickness: int = 20
    node_opacity: float = 0.7
    ghost_opacity: float = 0.25
    arrow_size: int = 15
    label_size: int = 12
    label_color: str = "#1e293b"
    default_node_color: str = "#2563eb"
    fig_width: int = 1200
    fig_height: int = 800
    value_unit: str = "kW"

    @property
    def bg_color(self) -> str:
        return "white" if self.theme_mode == "Light" else "#121212"


# ==========================================
# MODULE 2: SETUP & SIDEBAR (THE CONTROLS)
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

cfg = SankeyConfig()

with st.sidebar:
    st.header("Parameters")
    cfg.theme_mode = st.radio("UI Theme", ["Light", "Dark"])
    cfg.label_color = "#1e293b" if cfg.theme_mode == "Light" else "#f8fafc"

    st.divider()
    st.subheader("Flow Orientation")
    orientation_label = st.radio("Direction", ["Horizontal", "Vertical"], horizontal=True)
    cfg.orientation = "h" if orientation_label == "Horizontal" else "v"

    st.divider()
    st.subheader("🔥 Thermal Gradient")
    col_h1, col_h2 = st.columns(2)
    with col_h1: cfg.high_val = st.number_input("High Threshold", value=cfg.high_val)
    with col_h2: cfg.high_col = st.color_picker("High Color", cfg.high_col)
    col_m1, col_m2 = st.columns(2)
    with col_m1: cfg.mid_val = st.number_input("Mid Threshold", value=cfg.mid_val)
    with col_m2: cfg.mid_col = st.color_picker("Mid Color", cfg.mid_col)
    col_l1, col_l2 = st.columns(2)
    with col_l1: cfg.low_val = st.number_input("Low Threshold", value=cfg.low_val)
    with col_l2: cfg.low_col = st.color_picker("Low Color", cfg.low_col)

    st.divider()
    st.subheader("Layout & Scaling")
    _align_options = ["Justify", "Left", "Center", "Right"]
    align_ui = st.radio("Node Alignment", _align_options,
                        index=_align_options.index(cfg.node_alignment.capitalize()),
                        horizontal=True)
    cfg.node_alignment = align_ui.lower()
    _arrangement_options = ["Snap", "Perpendicular", "Freeform"]
    arrangement_ui = st.selectbox("Node Arrangement", _arrangement_options,
                                  index=_arrangement_options.index(cfg.node_arrangement.capitalize()))
    cfg.node_arrangement = arrangement_ui.lower()

    cfg.v_margin = st.slider("Vertical Margin (Scaling)", 0, 500, cfg.v_margin)
    cfg.h_margin = st.slider("Horizontal Margin (Padding)", 0, 500, cfg.h_margin)

    st.divider()
    st.subheader("Visual Geometry")
    cfg.node_spacing   = st.slider("Node Pad (Gap)", 0, 200, cfg.node_spacing)
    cfg.node_thickness = st.slider("Node Width", 5, 50, cfg.node_thickness)
    cfg.node_opacity   = st.slider("Link Opacity", 0.1, 1.0, cfg.node_opacity)
    cfg.arrow_size     = st.slider("Arrow Head Size", 0, 50, cfg.arrow_size)

    st.divider()
    st.subheader("Typography & Canvas")
    cfg.label_size         = st.slider("Font Size", 8, 30, cfg.label_size)
    cfg.label_color        = st.color_picker("Font Color", value=cfg.label_color)
    cfg.default_node_color = st.color_picker("Default Node Color", value=cfg.default_node_color)
    cfg.fig_width          = st.number_input("Canvas Width (px)", value=cfg.fig_width)
    cfg.fig_height         = st.number_input("Canvas Height (px)", value=cfg.fig_height)
    cfg.value_unit         = st.text_input("Value Unit", cfg.value_unit)


# ==========================================
# MODULE 3: LOGIC FUNCTIONS (THE BRAIN)
# ==========================================
def safe_float(val) -> tuple[float, bool]:
    """
    Parse a value to float.
    Returns (parsed_float, success_bool).
    Callers can check the flag and warn the user on failure.
    """
    if val is None:
        return 0.0, False
    try:
        return float(str(val).replace(',', '.').strip()), True
    except (ValueError, TypeError):
        return 0.0, False


def hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    hex_code = hex_code.lstrip('#')
    if len(hex_code) == 3:
        hex_code = ''.join([c * 2 for c in hex_code])
    return tuple(int(hex_code[i:i + 2], 16) for i in (0, 2, 4))


def interpolate_rgb(val: float, min_v: float, max_v: float,
                    color1: str, color2: str, opacity: float) -> str:
    if max_v == min_v:
        return color1
    f = max(0.0, min(1.0, (val - min_v) / (max_v - min_v)))
    rgb1, rgb2 = hex_to_rgb(color1), hex_to_rgb(color2)
    res = tuple(int(rgb1[i] + (rgb2[i] - rgb1[i]) * f) for i in range(3))
    return f"rgba({res[0]}, {res[1]}, {res[2]}, {opacity})"


def get_link_color(input_val, cfg: SankeyConfig, opacity_override: float = None) -> str:
    """Resolve a user-supplied color/value token to an rgba string.
    Pass opacity_override to use a different opacity (e.g. for ghost links)."""
    opacity = opacity_override if opacity_override is not None else cfg.node_opacity
    if not input_val:
        return f"rgba(150, 150, 150, {opacity})"
    clean_str = str(input_val).strip().lower()
    if clean_str == "elec":
        return f"rgba(0, 200, 0, {opacity})"
    if clean_str == "black":
        return f"rgba(0, 0, 0, {opacity})"
    if clean_str.startswith('#'):
        try:
            r, g, b = hex_to_rgb(clean_str)
            return f"rgba({r}, {g}, {b}, {opacity})"
        except Exception:
            return f"rgba(150, 150, 150, {opacity})"
    v, ok = safe_float(input_val)
    if not ok:
        return f"rgba(150, 150, 150, {opacity})"
    if v >= cfg.mid_val:
        return interpolate_rgb(v, cfg.mid_val, cfg.high_val,
                               cfg.mid_col, cfg.high_col, opacity)
    return interpolate_rgb(v, cfg.low_val, cfg.mid_val,
                           cfg.low_col, cfg.mid_col, opacity)


def get_node_colors(labels: list, node_color_map: dict, cfg: SankeyConfig) -> list:
    """
    Build the per-node color list for Plotly.
    Uses the per-node override from node_color_map if present and valid,
    otherwise falls back to cfg.default_node_color.
    """
    return [
        node_color_map.get(label, cfg.default_node_color)
        for label in labels
    ]


def process_row(
    source: str,
    target: str,
    value_str,
    color_val,
    cfg: SankeyConfig,
    labels: list,
    l2i: dict,
    src: list,
    tgt: list,
    val: list,
    link_colors: list,
    is_ghost: list,
    parse_warnings: list,
) -> None:
    """
    Shared logic for both input modes:
    - Parses and validates the value
    - Inverts direction for negative values
    - Zero-value flows are rendered as ghost links (thin, faded)
    - Updates label index, src/tgt/val/link_colors in-place
    - Appends a warning message if the value could not be parsed
    """
    source, target = str(source).strip(), str(target).strip()
    if not source or not target:
        return

    v, ok = safe_float(value_str)
    if not ok:
        parse_warnings.append(
            f"⚠️ Could not parse value **'{value_str}'** "
            f"for flow `{source} → {target}`. Row skipped."
        )
        return

    # Negative value inversion: flip direction
    if v < 0:
        source, target, v = target, source, abs(v)

    ghost = (v == 0)

    for node in (source, target):
        if node not in l2i:
            l2i[node] = len(labels)
            labels.append(node)

    src.append(l2i[source])
    tgt.append(l2i[target])
    # Ghost links use a tiny epsilon so Plotly renders them as hairlines
    val.append(v if not ghost else 0.001)
    is_ghost.append(ghost)
    link_colors.append(
        get_link_color(color_val, cfg,
                       opacity_override=cfg.ghost_opacity if ghost else None)
    )


# ==========================================
# MODULE 4: DATA HANDLING (THE INPUT)
# ==========================================
st.subheader("Data Input")
input_mode = st.radio("Input Method:", ["Interactive Table", "Text Input"], horizontal=True)

default_dataset = [
    {"Source": "Natural Gas", "Target": "Boiler",  "Value": "400",   "Color": "Black"},
    {"Source": "Tank1",       "Target": "Tank2",   "Value": "-50,5", "Color": "60"},
    {"Source": "Steam",       "Target": "Process", "Value": "88,3",  "Color": "160"},
    {"Source": "Elec Grid",   "Target": "Chiller", "Value": "100",   "Color": "Elec"},
]

src, tgt, val, labels, link_colors = [], [], [], [], []
l2i: dict = {}
is_ghost: list = []
parse_warnings: list = []
active_df = None   # kept for CSV export

if input_mode == "Text Input":
    text_repr = "\n".join(
        [f"{d['Source']} [{d['Value']}] {d['Target']} {d['Color']}"
         for d in default_dataset]
    )
    raw_input = st.text_area("Flow Specification", value=text_repr, height=300)
    for line in raw_input.strip().split('\n'):
        m = re.match(r'(.+?)\s*\[(.+?)\]\s*(.+?)(?:\s*(\S+))?$', line.strip())
        if m:
            process_row(
                source=m.group(1), target=m.group(3),
                value_str=m.group(2), color_val=m.group(4),
                cfg=cfg, labels=labels, l2i=l2i,
                src=src, tgt=tgt, val=val,
                link_colors=link_colors, is_ghost=is_ghost,
                parse_warnings=parse_warnings,
            )
else:
    col_config = {
        "Value":  st.column_config.TextColumn("Value"),
        "Source": st.column_config.TextColumn("Source Node"),
        "Target": st.column_config.TextColumn("Target Node"),
        "Color":  st.column_config.TextColumn("Color/Temp"),
    }
    df = st.data_editor(
        pd.DataFrame(default_dataset),
        num_rows="dynamic",
        use_container_width=True,
        column_config=col_config,
    )
    active_df = df.dropna(subset=['Source', 'Target', 'Value'])
    for _, row in active_df.iterrows():
        process_row(
            source=row['Source'], target=row['Target'],
            value_str=row['Value'], color_val=row.get('Color'),
            cfg=cfg, labels=labels, l2i=l2i,
            src=src, tgt=tgt, val=val,
            link_colors=link_colors, is_ghost=is_ghost,
            parse_warnings=parse_warnings,
        )

# Surface any parse warnings to the user
for w in parse_warnings:
    st.warning(w)


# ==========================================
# MODULE 4b: NODE COLOR TABLE (OPTIONAL)
# ==========================================
# Auto-populated with one row per unique node from the flow data.
# Pre-filled with cfg.default_node_color; user can override per node.
# Collapsed by default so it stays out of the way.
node_color_map: dict = {}

if labels:
    with st.expander("🎨 Node Colors (optional)", expanded=False):
        st.caption(
            "Override the color of individual nodes. "
            "Use hex codes (e.g. #FF0000). "
            "Rows left at the default color will use the Default Node Color set in the sidebar."
        )
        node_color_df = pd.DataFrame([
            {"Node": label, "Color": cfg.default_node_color}
            for label in labels
        ])
        edited_color_df = st.data_editor(
            node_color_df,
            num_rows="fixed",       # nodes come from flow table, not user-added
            use_container_width=True,
            column_config={
                "Node":  st.column_config.TextColumn("Node", disabled=True),
                "Color": st.column_config.TextColumn("Hex Color (e.g. #FF0000)"),
            },
            key="node_color_editor",
        )
        # Build the override map; ignore blank or malformed entries
        for _, row in edited_color_df.iterrows():
            node_name = str(row["Node"]).strip()
            color_str = str(row["Color"]).strip()
            if color_str.startswith("#") and len(color_str) in (4, 7):
                node_color_map[node_name] = color_str


# ==========================================
# MODULE 5: RENDERING (THE OUTPUT)
# ==========================================
if labels:
    try:
        node_in  = [0.0] * len(labels)
        node_out = [0.0] * len(labels)
        for i in range(len(src)):
            node_out[src[i]] += val[i]
            node_in[tgt[i]]  += val[i]

        display_labels = [
            f"{l}<br>{int(round(max(node_in[i], node_out[i]), 0))} {cfg.value_unit}"
            for i, l in enumerate(labels)
        ]
        meta = [[labels[i], node_in[i], node_out[i]] for i in range(len(labels))]

        # Per-link customdata: [source_name, target_name, display_value]
        # Ghost links store 0 as display value so the tooltip shows 0, not 0.001
        link_customdata = [
            [labels[s], labels[t], 0 if is_ghost[i] else val[i]]
            for i, (s, t) in enumerate(zip(src, tgt))
        ]

        # Resolve per-node colors: override map → sidebar default
        node_colors = get_node_colors(labels, node_color_map, cfg)

        fig = go.Figure(data=[go.Sankey(
            orientation=cfg.orientation,
            arrangement=cfg.node_arrangement,
            textfont=dict(color=cfg.label_color, size=cfg.label_size),
            node=dict(
                pad=cfg.node_spacing,
                thickness=cfg.node_thickness,
                label=display_labels,
                align=cfg.node_alignment,
                color=node_colors,
                line=dict(color=cfg.bg_color, width=1),
                customdata=meta,
                hovertemplate=(
                    '<b>%{customdata[0]}</b><br>'
                    'Input: %{customdata[1]:.0f}<br>'
                    'Output: %{customdata[2]:.0f}<extra></extra>'
                ),
            ),
            link=dict(
                source=src,
                target=tgt,
                value=val,
                color=link_colors,
                arrowlen=cfg.arrow_size,
                customdata=link_customdata,
                hovertemplate=(
                    '<b>%{customdata[0]}</b> → <b>%{customdata[1]}</b><br>'
                    'Flow: %{customdata[2]:.0f} ' + cfg.value_unit + '<extra></extra>'
                ),
            ),
        )])

        fig.update_layout(
            width=cfg.fig_width,
            height=cfg.fig_height,
            paper_bgcolor=cfg.bg_color,
            plot_bgcolor=cfg.bg_color,
            margin=dict(
                l=cfg.h_margin, r=cfg.h_margin,
                t=cfg.v_margin, b=cfg.v_margin,
            ),
        )
        st.plotly_chart(fig, use_container_width=False)

        if input_mode == "Interactive Table" and active_df is not None and not active_df.empty:
            st.download_button(
                "Export Configuration (CSV)",
                active_df.to_csv(index=False),
                "sankey_audit.csv",
                "text/csv",
            )
    except Exception as e:
        st.error(f"Execution Error: {e}")
else:
    st.info("Add at least one valid flow to render the diagram.")
