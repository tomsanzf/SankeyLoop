import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt

# Constants for canvas width
DEFAULT_CANVAS_WIDTH = 700

# Streamlit app
st.title('Sankey Loop Visualization')

# Control for canvas width
def control_canvas_width():
    canvas_width = st.slider('Canvas Width', min_value=500, max_value=1200, value=DEFAULT_CANVAS_WIDTH)
    st.write(f"Canvas Width: {canvas_width}")
    return canvas_width

# Real-time slider updates with on_change callbacks
def update_params():
    # Update parameters based on slider changes...
    st.write("Parameters updated!")

# Preserve node positions during parameter changes
# Assuming a function to render nodes is defined
def render_graph(G, positions):
    plt.figure(figsize=(10, 7))
    nx.draw(G, pos=positions, with_labels=True)
    plt.show()

# Main logic
canvas_width = control_canvas_width()

# Example of a graph
G = nx.Graph()  
G.add_edges_from([(1, 2), (2, 3), (3, 1)])  
positions = nx.spring_layout(G)

# Use Streamlit to display the graph
update_params()
render_graph(G, positions)