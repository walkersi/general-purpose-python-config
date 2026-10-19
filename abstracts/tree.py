from collections import deque

# basic tree data structure with breadth first search support
# note that ordering of children is not semantically relevant so may not be preserved
# expects values to be unique in the tree
class Tree:
    def __init__(self, value):
        self.value = value
        self.children = set()
    
    def add_child(self, child):
        self.children.add(Tree(child))

    # adds node of value <child> as descendent of node with value <ancestor>
    # assumes ancestor is present and unique
    def add_child_to(self, ancestor, child):
        # search
        if ancestor == self.value:
            self.add_child(child)
        else:
            # try descendants instead
            for descendant in self.children:
                descendant.add_child_to(ancestor, child)

    def breadth_first(self):
        vals = []
        q = deque([self])
        while q:
            node = q.popleft()
            vals.append(node.value)
            q.extend(node.children)

        return vals
