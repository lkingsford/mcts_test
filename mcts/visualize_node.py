import mcts.tree
import pydot


def visualize_node(node: mcts.tree.Node):
    graph = pydot.Dot("MCTS", graph_type="digraph")
    graph.add_node(pydot.Node(node.hash))
    for child in node.load_children(node.cursor):
        graph.add_node(pydot.Node(child.hash))
        graph.add_edge(pydot.Edge(node.hash, child.hash))

    return graph
