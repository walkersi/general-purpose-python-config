# standard undirected weighted graph
# allows arbitrary weights and additional arbitrary information on edges
import math

class Edge:
    def __init__(self, from_node, to_node, weight, *data):
        self.to_node = to_node
        self.from_node = from_node
        self.weight = weight
        self.data = data

class Node:
    def __init__(self, value):
        self.value = value
        self.edges = set()

    def add_edge(self, to_node, weight, data):
        self.edges.add(Edge(self, to_node, weight, data))

    
    # returns the set of nodes reachable from this one
    # depth search the graph, basically
    def reaches(self):
        reachable = {self}
        for edge in self.edges:
            node = edge.to_node
            # if not already traversed, go down that path
            if node not in reachable:
                reachable |= node.reaches()

        return reachable

    # assumes this node has an edge to given node
    # returns the edge to that node
    def get_edge_by_node(self, node: Node):
        for edge in self.edges:
            if edge.to_node == node:
                return edge
        

class Graph:
    def __init__(self, nodes: set[Node]):
        self.nodes = nodes
    
    # returns the node with given value
    # assumes a node with value exists
    def get_node_by_value(self, value):
        for node in self.nodes:
            if node.value == value:
                return node

    def fully_connected(self):
        if len(self.nodes) == 0:
            return True
        return self.all_reachable_from(self.nodes.__iter__().__next__())

    # returns true if all nodes can be reached from the given node
    def all_reachable_from(self, node: Node):
        if self.nodes - node.reaches():
            return False
        return True

    # assumes graph to be fully connected (see fully_connected)
    # gets the shortest path by weights from node1 to node2 and returns the weights
    def edges_between(self, source: Node, dest: Node):
        if {source, dest} - self.nodes:
            raise ArithmeticError("Node does not exist in graph")

        # do dijkstras
        visited = set()
        # start with infinite distances
        distances = dict()
        previous = dict()
        for node in self.nodes:
            distances[node] = math.inf
            previous[node] = None
        distances[source] = 0

        # while there is still unvisited nodes
        while self.nodes - visited:
            # find smallest distance
            smallest = distances.keys().__next__()
            for node, distance in distances.items():
                if distance < distances[smallest]:
                    smallest = node
            # look at neighbours
            for edge in smallest.edges:
                if edge.to_node not in visited:
                    # for unvisited neighbours, try to update their distance
                    distance_from_here = edge.weight + distances[node]
                    if distances[edge.to_node] > distance_from_here:
                        # closer, so update distance and route
                        distances[edge.to_node] = distance_from_here
                        previous[edge.to_node] = edge.from_node
            # mark as visited
            visited.add(smallest)

        # trace back from dest to source
        node_path = []
        node = dest
        while node != source:
            next = previous[node]
            node_path.insert(0, next)
            node = next

        edge_path = []
        # return edges between said nodes as the path
        for node, next in zip(node_path, node_path[1:]):
            edge_path.append(node.get_edge_by_node(next))

        return edge_path

