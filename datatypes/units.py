from abstracts.graph import Node, Edge, Graph
import re

# given an expression in form numerical value - unit, e.g. "13.4ms",
# separate them and return
def get_unit_from_expression(expression):
    pattern = "^(?P<value>[\\+\\-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+))?[ ]*(?P<unit>[^0-9\\.\\-\\+].*)$"
    match = re.search(pattern, expression)
    if not match:
        return None, None
    return match.group("value"), match.group("unit")

# converts to an integer if possible, otherwise a float
# to minimise loss of precision
# assumes value is a valid float
def best_numerical_choice(value: str):
    if "." in value:
        return float(value)
    return int(value)

# enumeration of conversion types
CONVERSION_DIVISION = "division"
CONVERSION_FLOAT_MULT = "float_multiplication"
CONVERSION_INT_MULT = "int_multiplication"
CONVERSION_EQUAL = "equality"

# returns what type of conversion this is, left to right,
# and the conversion factor (i.e. what to multiply by) as tuple
def classify_conversion(left_value: float|int, right_value: float|int):
    if left_value > right_value:
        return CONVERSION_DIVISION, right_value / left_value
    elif left_value == right_value:
        return CONVERSION_EQUAL, 1
    # otherwise, must be a multiplication
    if int(right_value / left_value) == (right_value / left_value):
        return CONVERSION_INT_MULT, int(right_value / left_value)
    else:
        return CONVERSION_FLOAT_MULT, right_value / left_value

# specialised for unit conversion
# assumes that all of the conversions are for actual units in the set
class UnitConversionGraph(Graph):
    def __init__(self, units: set[str], conversions: dict[str, str]):
        super().__init__({Node(u) for u in units})

        # assign a cost value to division such that it is arbitrarily very high
        # but no path can exceed 2^32 
        # (which may be slower to process because python software ints)
        # division is higher cost, multiplication is lower
        # avoid division paths because floating point 
        longest_path = (len(self.nodes)+1)
        division_weight = int(4294967295 / longest_path)
        # multiplying by integers is better than by floats for preserving precision
        float_multiplication_weight = int(division_weight / longest_path)
        int_multiplication_weight = int(float_multiplication_weight / longest_path)
        # special weight if units are a 1:1 conversion
        equality_weight = 1

        weight_map = {CONVERSION_DIVISION: division_weight, 
                      CONVERSION_EQUAL: equality_weight,
                      CONVERSION_FLOAT_MULT: float_multiplication_weight,
                      CONVERSION_INT_MULT: int_multiplication_weight}

        # extract the corresponding units and values and add them to the graph
        for conversion, equivalent in conversions.items():
            left_value, left_unit = get_unit_from_expression(conversion)
            right_value, right_unit = get_unit_from_expression(equivalent)
            # handle empty values (these can be set to 1 implicitly)
            left_value = best_numerical_choice(left_value) if left_value else 1
            right_value = best_numerical_choice(right_value) if right_value else 1
            # find relevant nodes for these units
            left_node = self.get_node_by_value(left_unit)
            right_node = self.get_node_by_value(right_unit)
            # figure out what type of conversion this is
            # both left to right and right to left
            l2r_type, l2r_factor = classify_conversion(left_value, right_value)
            r2l_type, r2l_factor = classify_conversion(right_value, left_value)
            # lookup the weight for the edge tyoes
            l2r_weight = weight_map[l2r_type]
            r2l_weight = weight_map[r2l_type]
            # construct edges between them
            left_node.add_edge(right_node, l2r_weight, l2r_factor)
            right_node.add_edge(left_node, r2l_weight, r2l_factor) 

    # get the multiplication factor of a given edge
    def get_factor(self, edge: Edge):
        return edge.data[0]

    # TODO this uses edges_between inefficiently,
    # better to compute a full dijkstras once then store the paths to target
    # node for all nodes
    # converts n in unit to target unit
    def convert_to(self, n, unit: str, target_unit: str):
        # trace the best-precision conversion path
        source = self.get_node_by_value(unit)
        dest = self.get_node_by_value(target_unit)
        edges = self.edges_between(source, dest)
        # walk through edges and apply their multiplier
        for edge in edges:
            n *= self.get_factor(edge)

        return n
