import streamlit as st
import plotly.graph_objects as go

# Data for Sankey diagram
node_labels = ['A', 'B', 'C', 'D']
node_values = [10, 20, 30, 40]
source_indices = [0, 1, 0, 2, 3]
destination_indices = [2, 2, 3, 3, 3]

# Initialize canvas width control
canvas_width = st.sidebar.slider('Canvas Width', min_value=400, max_value=1000, value=700)

# Function to draw Sankey diagram
def draw_sankey():
    fig = go.Figure(go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=node_labels,
            color='blue'
        ),
        link=dict(
            source=source_indices,
            target=destination_indices,
            value=node_values,
            color='orange'
        )
    ))

    # Set layout width
    fig.update_layout(width=canvas_width, height=400)
    st.plotly_chart(fig)

# Callback for real-time updates
if st.sidebar.button('Update Diagram'):
    draw_sankey()
else:
    draw_sankey()  # Initial draw
