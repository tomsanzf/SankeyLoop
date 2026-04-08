import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import re
import io
import dataclasses
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
# MODULE 2: DEFAULTS
# ==========================================
DEFAULT_FLOWS = [
    {"Source": "Gas",               "Target": "Boiler",               "Value": "78",  "Color": "Black"},
    {"Source": "Boiler",            "Target": "Steam",                "Value": "67",  "Color": "200"},
    {"Source": "Boiler",            "Target": "Purge",                "Value": "1",   "Color": "170"},
    {"Source": "Boiler",            "Target": "Stack",                "Value": "10",  "Color": "Black"},
    {"Source": "Steam",             "Target": "Deaerator",            "Value": "2",   "Color": "200"},
    {"Source": "Deaerator",         "Target": "Boiler",               "Value": "-4",  "Color": "105"},
    {"Source": "Feedwater",         "Target": "Deaerator",            "Value": "60",  "Color": "20"},
    {"Source": "Steam",             "Target": "Process",              "Value": "0",   "Color": "200"},
    {"Source": "Process",           "Target": "Condensate Return",    "Value": "0",   "Color": "90"},
    {"Source": "Process",           "Target": "Cndnste Not Returned", "Value": "0",   "Color": "Black"},
    {"Source": "Condensate Return", "Target": "Deaerator",            "Value": "60",  "Color": "90"},
    {"Source": "Process",           "Target": "Chilled Water",        "Value": "60",  "Color": "20"},
    {"Source": "Chilled Water",     "Target": "Chiller",              "Value": "20",  "Color": "10"},
    {"Source": "Elec",              "Target": "Chiller",              "Value": "80",  "Color": "Elec"},
    {"Source": "Chiller",           "Target": "HP",                   "Value": "27",  "Color": "30"},
    {"Source": "Elec",              "Target": "HP",                   "Value": "107", "Color": "Elec"},
    {"Source": "HP",                "Target": "Process",              "Value": "0",   "Color": "90"},
]


# ==========================================
# MODULE 3: SESSION STATE INITIALISATION
# ==========================================
# All mutable app state lives in st.session_state so it survives reruns
# and can be bulk-replaced by the CSV importer.

def _init_session_state():
    """Seed session_state with defaults on first run only."""
    defaults = dataclasses.asdict(SankeyConfig())
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if "flows_df" not in st.session_state:
        st.session_state["flows_df"] = pd.DataFrame(DEFAULT_FLOWS)
    if "node_colors_raw" not in st.session_state:
        # dict: {node_name: color_string} — populated after flows are parsed
        st.session_state["node_colors_raw"] = {}

_init_session_state()


# ==========================================
# MODULE 4: IMPORT / EXPORT HELPERS
# ==========================================
CONFIG_FIELDS = [f.name for f in dataclasses.fields(SankeyConfig)]


def build_export_csv(flows_df: pd.DataFrame, node_colors_raw: dict) -> str:
    """
    Produce a two-section CSV string:
      [config]   — one key,value row per SankeyConfig field
      [flows]    — the flow data table
      [nodes]    — per-node color overrides
    """
    lines = ["[config]", "key,value"]
    for field in CONFIG_FIELDS:
        lines.append(f"{field},{st.session_state.get(field, '')}")

    lines += ["", "[flows]"]
    lines.append(flows_df.to_csv(index=False).strip())

    lines += ["", "[nodes]", "Node,Color"]
    for node, color in node_colors_raw.items():
        lines.append(f"{node},{color}")

    return "\n".join(lines)


def parse_import_csv(content: str) -> dict:
    """
    Parse a SankeyLoop CSV export back into a dict of session_state updates.
    Returns a dict with keys: config (dict), flows (DataFrame), node_colors (dict).
    Raises ValueError with a descriptive message on malformed input.
    """
    sections = {"config": [], "flows": [], "nodes": []}
    current = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ("[config]", "[flows]", "[nodes]"):
            current = stripped[1:-1]
        elif current and stripped:
            sections[current].append(stripped)

    # --- config ---
    config_out = {}
    defaults = dataclasses.asdict(SankeyConfig())
    for row in sections["config"][1:]:   # skip header "key,value"
        parts = row.split(",", 1)
        if len(parts) != 2:
            continue
        key, raw_val = parts[0].strip(), parts[1].strip()
        if key not in defaults:
            continue
        default_val = defaults[key]
        try:
            if isinstance(default_val, bool):
                config_out[key] = raw_val.lower() == "true"
            elif isinstance(default_val, int):
                config_out[key] = int(float(raw_val))
            elif isinstance(default_val, float):
                config_out[key] = float(raw_val)
            else:
                config_out[key] = raw_val
        except (ValueError, TypeError):
            config_out[key] = default_val   # fall back silently

    # --- flows ---
    if not sections["flows"]:
        raise ValueError("No [flows] section found in the imported file.")
    flows_csv = "\n".join(sections["flows"])
    try:
        flows_df = pd.read_csv(io.StringIO(flows_csv), dtype=str)
        for col in ("Source", "Target", "Value", "Color"):
            if col not in flows_df.columns:
                raise ValueError(f"Missing column '{col}' in [flows] section.")
    except Exception as e:
        raise ValueError(f"Could not parse [flows] section: {e}")

    # --- node colors ---
    node_colors = {}
    for row in sections["nodes"][1:]:   # skip header "Node,Color"
        parts = row.split(",", 1)
        if len(parts) == 2:
            node_colors[parts[0].strip()] = parts[1].strip()

    return {"config": config_out, "flows": flows_df, "node_colors": node_colors}


# ==========================================
# MODULE 5: SETUP & SIDEBAR (THE CONTROLS)
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

# Sidebar reads from AND writes to session_state via widget keys.
# Using the `key=` parameter means Streamlit automatically syncs the
# widget value into session_state[key] on every interaction.
with st.sidebar:
    st.header("Parameters")

    # --- Import ---
    st.subheader("💾 Import / Export")
    uploaded = st.file_uploader("Import Config CSV", type="csv",
                                 label_visibility="collapsed")
    if uploaded is not None:
        try:
            parsed = parse_import_csv(uploaded.read().decode("utf-8"))
            # Push config values into session_state
            for k, v in parsed["config"].items():
                st.session_state[k] = v
            # Push flows and node colors
            st.session_state["flows_df"]       = parsed["flows"]
            st.session_state["node_colors_raw"] = parsed["node_colors"]
            st.success("Configuration imported successfully.")
            st.rerun()
        except ValueError as e:
            st.error(f"Import failed: {e}")

    st.divider()
    st.subheader("UI Theme")
    st.radio("Theme", ["Light", "Dark"],
             key="theme_mode")

    st.divider()
    st.subheader("Flow Orientation")
    st.radio("Direction", ["Horizontal", "Vertical"],
             horizontal=True, key="_orientation_label")

    st.divider()
    st.subheader("🔥 Thermal Gradient")
    col_h1, col_h2 = st.columns(2)
    with col_h1: st.number_input("High Threshold", key="high_val")
    with col_h2: st.color_picker("High Color",     key="high_col")
    col_m1, col_m2 = st.columns(2)
    with col_m1: st.number_input("Mid Threshold",  key="mid_val")
    with col_m2: st.color_picker("Mid Color",      key="mid_col")
    col_l1, col_l2 = st.columns(2)
    with col_l1: st.number_input("Low Threshold",  key="low_val")
    with col_l2: st.color_picker("Low Color",      key="low_col")

    st.divider()
    st.subheader("Layout & Scaling")
    st.radio("Node Alignment", ["Justify", "Left", "Center", "Right"],
             horizontal=True, key="_node_alignment_label")
    st.selectbox("Node Arrangement", ["Snap", "Perpendicular", "Freeform"],
                 key="_node_arrangement_label")
    st.slider("Vertical Margin (Scaling)",  0, 500, key="v_margin")
    st.slider("Horizontal Margin (Padding)", 0, 500, key="h_margin")

    st.divider()
    st.subheader("Visual Geometry")
    st.slider("Node Pad (Gap)",    0, 200, key="node_spacing")
    st.slider("Node Width",        5,  50, key="node_thickness")
    st.slider("Link Opacity",      0.1, 1.0, key="node_opacity")
    st.slider("Arrow Head Size",   0,  50, key="arrow_size")

    st.divider()
    st.subheader("Typography & Canvas")
    st.slider("Font Size",         8,  30, key="label_size")
    st.color_picker("Font Color",         key="label_color")
    st.color_picker("Default Node Color", key="default_node_color")
    st.number_input("Canvas Width (px)",  key="fig_width")
    st.number_input("Canvas Height (px)", key="fig_height")
    st.text_input("Value Unit",           key="value_unit")


# Derive the two enum-style fields from their radio/selectbox widgets
st.session_state["orientation"] = (
    "h" if st.session_state.get("_orientation_label", "Horizontal") == "Horizontal" else "v"
)
st.session_state["node_alignment"] = (
    st.session_state.get("_node_alignment_label", "Center").lower()
)
st.session_state["node_arrangement"] = (
    st.session_state.get("_node_arrangement_label", "Snap").lower()
)

# Build cfg from session_state for use downstream
cfg = SankeyConfig(**{f: st.session_state[f] for f in CONFIG_FIELDS})


# ==========================================
# MODULE 6: LOGIC FUNCTIONS (THE BRAIN)
# ==========================================
def safe_float(val) -> tuple[float, bool]:
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


def get_link_color(input_val, cfg: SankeyConfig,
                   opacity_override: float = None) -> str:
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


NAMED_COLORS: dict = {
    "red": "#FF0000", "green": "#008000", "blue": "#0000FF",
    "yellow": "#FFFF00", "orange": "#FFA500", "purple": "#800080",
    "pink": "#FFC0CB", "brown": "#A52A2A", "black": "#000000",
    "white": "#FFFFFF", "grey": "#808080", "gray": "#808080",
    "cyan": "#00FFFF", "magenta": "#FF00FF", "lime": "#00FF00",
    "navy": "#000080", "teal": "#008080", "maroon": "#800000",
    "olive": "#808000", "coral": "#FF7F50", "salmon": "#FA8072",
    "gold": "#FFD700", "indigo": "#4B0082", "violet": "#EE82EE",
    "turquoise": "#40E0D0", "silver": "#C0C0C0", "beige": "#F5F5DC",
    "lavender": "#E6E6FA", "khaki": "#F0E68C", "crimson": "#DC143C",
}


def resolve_node_color(color_str: str, fallback: str) -> str:
    s = color_str.strip().lower()
    if not s:
        return fallback
    if s.startswith("#") and len(s) in (4, 7):
        return s.upper()
    if s in NAMED_COLORS:
        return NAMED_COLORS[s]
    return fallback


def get_node_colors(labels: list, node_color_map: dict,
                    cfg: SankeyConfig) -> list:
    return [node_color_map.get(label, cfg.default_node_color)
            for label in labels]


def process_row(
    source: str, target: str, value_str, color_val,
    cfg: SankeyConfig, labels: list, l2i: dict,
    src: list, tgt: list, val: list,
    link_colors: list, is_ghost: list, parse_warnings: list,
) -> None:
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
    if v < 0:
        source, target, v = target, source, abs(v)
    ghost = (v == 0)
    for node in (source, target):
        if node not in l2i:
            l2i[node] = len(labels)
            labels.append(node)
    src.append(l2i[source])
    tgt.append(l2i[target])
    val.append(v if not ghost else 0.001)
    is_ghost.append(ghost)
    link_colors.append(
        get_link_color(color_val, cfg,
                       opacity_override=cfg.ghost_opacity if ghost else None)
    )


# ==========================================
# MODULE 7: DATA INPUT
# ==========================================
st.subheader("Data Input")
input_mode = st.radio("Input Method:", ["Interactive Table", "Text Input"],
                      horizontal=True)

src, tgt, val, labels, link_colors = [], [], [], [], []
l2i: dict = {}
is_ghost: list = []
parse_warnings: list = []
active_df = None

if input_mode == "Text Input":
    text_repr = "\n".join(
        [f"{d['Source']} [{d['Value']}] {d['Target']} {d['Color']}"
         for d in st.session_state["flows_df"].to_dict("records")]
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
    edited_flows = st.data_editor(
        st.session_state["flows_df"],
        num_rows="dynamic",
        use_container_width=True,
        column_config=col_config,
        key="flows_editor",
    )
    # Persist any edits back into session_state
    st.session_state["flows_df"] = edited_flows
    active_df = edited_flows.dropna(subset=["Source", "Target", "Value"])
    for _, row in active_df.iterrows():
        process_row(
            source=row["Source"], target=row["Target"],
            value_str=row["Value"], color_val=row.get("Color"),
            cfg=cfg, labels=labels, l2i=l2i,
            src=src, tgt=tgt, val=val,
            link_colors=link_colors, is_ghost=is_ghost,
            parse_warnings=parse_warnings,
        )

for w in parse_warnings:
    st.warning(w)


# ==========================================
# MODULE 7b: NODE COLOR TABLE (OPTIONAL)
# ==========================================
node_color_map: dict = {}

if labels:
    with st.expander("🎨 Node Colors (optional)", expanded=False):
        st.caption(
            "Override the color of individual nodes. "
            "Accepts hex codes (e.g. #FF0000) or color names (e.g. red, green, navy). "
            "Rows left at the default color will use the Default Node Color set in the sidebar."
        )
        # Pre-populate from session_state overrides; fall back to default for new nodes
        saved_colors = st.session_state.get("node_colors_raw", {})
        node_color_df = pd.DataFrame([
            {"Node": label,
             "Color": saved_colors.get(label, cfg.default_node_color)}
            for label in labels
        ])
        edited_color_df = st.data_editor(
            node_color_df,
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "Node":  st.column_config.TextColumn("Node", disabled=True),
                "Color": st.column_config.TextColumn("Color (hex or name)"),
            },
            key="node_color_editor",
        )
        # Resolve and store overrides
        new_colors_raw = {}
        for _, row in edited_color_df.iterrows():
            node_name = str(row["Node"]).strip()
            color_str = str(row["Color"]).strip()
            resolved  = resolve_node_color(color_str, fallback="")
            if resolved:
                node_color_map[node_name]  = resolved
                new_colors_raw[node_name]  = color_str   # store raw for re-display
        st.session_state["node_colors_raw"] = new_colors_raw


# ==========================================
# MODULE 8: RENDERING
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
        link_customdata = [
            [labels[s], labels[t], 0 if is_ghost[i] else val[i]]
            for i, (s, t) in enumerate(zip(src, tgt))
        ]
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
                source=src, target=tgt, value=val,
                color=link_colors, arrowlen=cfg.arrow_size,
                customdata=link_customdata,
                hovertemplate=(
                    '<b>%{customdata[0]}</b> → <b>%{customdata[1]}</b><br>'
                    'Flow: %{customdata[2]:.0f} ' + cfg.value_unit + '<extra></extra>'
                ),
            ),
        )])

        fig.update_layout(
            width=cfg.fig_width, height=cfg.fig_height,
            paper_bgcolor=cfg.bg_color, plot_bgcolor=cfg.bg_color,
            margin=dict(l=cfg.h_margin, r=cfg.h_margin,
                        t=cfg.v_margin,  b=cfg.v_margin),
        )
        st.plotly_chart(fig, use_container_width=False)

        # --- Export button (always visible once diagram exists) ---
        export_csv = build_export_csv(
            st.session_state["flows_df"],
            st.session_state.get("node_colors_raw", {}),
        )
        st.download_button(
            "⬇️ Export Full Configuration (CSV)",
            data=export_csv,
            file_name="sankeyloop_config.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Execution Error: {e}")
else:
    st.info("Add at least one valid flow to render the diagram.")
