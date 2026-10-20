import sqlite3
import json
import tech_tree_builder
import networkx as nx
import matplotlib.pyplot as plt




def build_networkx_tech_graph(tree: tech_tree_builder.Civ4TechTreeBuilder) -> nx.DiGraph:
    G = nx.DiGraph()
    
    for node in tree.nodes.values():
        G.add_node(node.tech_id, name=node.tech_type, x=node.grid_x, y=node.grid_y, status=node.status)
    
    # Connect lower grid_x column nodes to higher grid_x column nodes in adjacent tracks
    for node in tree.nodes.values():
        downstream = [
            other for other in tree.get_column_tier(node.grid_x + 1)
            if abs(other.grid_y - node.grid_y) <= 2
        ]
        for child in downstream:
            G.add_edge(node.tech_id, child.tech_id, weight=child.cost)
            
    return G

def draw_digraph(digraph: nx.DiGraph):
    # Position nodes using a spring layout algorithm
    #pos = nx.spring_layout(digraph)
    pos = nx.nx_agraph.graphviz_layout(digraph, prog="dot")
    # Draw the graph showing arrows for edge direction
    nx.draw(digraph, pos, with_labels=True, node_color='skyblue', edge_color='gray', arrows=True)
    plt.savefig('network_graph.png', dpi=300, bbox_inches='tight')
    print("Graph saved successfully as network_graph.png!")
    #plt.show()
    

# 1. Fetch latest onTechTreeScan payload from SQLite
conn = sqlite3.connect("civ4_telemetry_json.db")
cur = conn.cursor()
cur.execute("""
    SELECT payload_json FROM server_turn_events 
    WHERE event_type = 'onTechTreeScan' 
    ORDER BY id DESC LIMIT 1
""")
row = cur.fetchone()



if row:
    payload_dict = json.loads(row[0])
    
    # 2. Build the Tech Tree Graph
    tree = tech_tree_builder.Civ4TechTreeBuilder(payload_dict)
    
    print(f"=== TECH TREE ANALYSIS ({tree.civilization}) ===")
    print(f"Available Options ({len(tree.available_techs)}):")
    for tech in tree.get_research_frontier():
        print(f"  -> [{tech.tech_type}] Grid: ({tech.grid_x}, {tech.grid_y}) | Cost: {tech.beakers_left} Beakers")
    
    # 3. Decision recommendation
    fastest_tech = tree.find_shortest_cost_tech()
    if fastest_tech:
        print(f"\nRecommended Quick Tech: {fastest_tech.tech_type} ({fastest_tech.beakers_left} beakers left)")

    digraph = build_networkx_tech_graph(tree)
    draw_digraph(digraph)


