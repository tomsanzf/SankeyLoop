# -- 3. Sidebar Parameters --
with st.sidebar:
    st.header("Settings")
    
    # ... (Keep Theme and Opacity settings) ...
    
    st.divider()
    
    st.write("Node Layout")
    node_spacing = st.slider("Vertical Spacing", 0, 100, 40)
    node_thickness = st.slider("Node Thickness", 5, 50, 20)
    
    # NEW: Arrangement Parameter (The 'Vertical' logic)
    arrangement_ui = st.selectbox(
        "Arrangement Logic",
        ["Snap", "Perpendicular", "Freeform"],
        index=0,
        help="Determines how nodes are packed vertically."
    )
    node_arrangement = arrangement_ui.lower()

    # Node Horizontal Alignment (Previously added)
    align_ui = st.radio(
        "Horizontal Alignment",
        ["Justify", "Left", "Center", "Right"],
        horizontal=True
    )
    node_alignment = align_ui.lower()
    
    # ... (Keep the rest of the sidebar) ...
