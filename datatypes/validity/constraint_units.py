from valids.dicts import *
from valids.casts import is_type_or_equivalent
from exceptions.structure_exceptions import *
from datatypes.validity.alias_handler import read_aliases
from abstracts.graph import Node, Edge, Graph
from datatypes.validity.constraints import UNITS, TARGET_UNIT, CONVERSION, RANGE
from datatypes.validity.constraint_range import create_range_constraint
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


# returns true if the expression is a valid unit expression for the given unit alias set
def unit_expr_valid(expression: str, allowed_names: set[str]):
    value, unit = get_unit_from_expression(expression)
    print(value, unit)
    return unit in allowed_names and value != None

# assuming the expression is valid, converts its value to the target unit and returns as value
def unit_expr_to_target_number(expression: str|float, graph: UnitConversionGraph, alias_map: dict[str,str], target_unit: str):
    # case: no conversion, leave as is
    if is_type_or_equivalent(expression, float):
        return expression
    # do unit conversion using graph
    n, unit = get_unit_from_expression(expression)
    # alias the unit so the graph gets the canonical symbol
    return graph.convert_to(float(n), alias_map[unit], target_unit)

def create_units_constraint(validity: dict):
    units = UNITS.validate(validity)

    if is_type_or_equivalent(units, str):
        # there is only one unit - we always coerce to this unit, it's basically
        # just for visual clarity in the config (it may have aliases)
        units = {units}

    # strip whitespace from units sides
    units = set([u.strip() for u in units])

    # check all units are valid characters only
    # use regex
    unit_pattern = f"^[^0-9\\.].*$"
    for unit in units:
        # units can include digits (e.g. ms-1) but must not start with them
        if not re.search(unit_pattern, unit):
            raise BadTypeDefinition(
                f"Invalid unit {unit} in {validity} - must be alphanumeric (some symbols allowed), leading with a non-digit")

    # look for a target unit for yield
    if TARGET_UNIT.name in validity:
        target_unit = TARGET_UNIT.get_from_definition(validity)
    elif len(units) > 1:
        # no target unit specified when one is needed
        raise BadTypeDefinition(f"target_unit was not specified for type with multiple possible units {validity}")
    else:
        # with just one unit, target unit is the unit itself
        target_unit = list(units)[0]

    # if there is more than one unit, conversion must be specified
    if CONVERSION.name in validity:
        conversions = CONVERSION.get_from_definition(validity)
    else:
        # arbitary conversion dict instead
        conversions = {f"1{target_unit}": f"1{target_unit}"}

    # conversion dict is invalid if it describes conversions for nonexistent units
    for conversion in conversions:
        equivalent = conversions[conversion]
        conversion_units = {get_unit_from_expression(conversion)[1], 
                            get_unit_from_expression(equivalent)[1]}
        # check validity by set subtraction
        if conversion_units - units:
            raise BadTypeDefinition(f"Invalid unit in conversions: {conversion} = {equivalent}")

    # make a graph from conversion dict
    graph = UnitConversionGraph(units, conversions)
    # conversion dict is incomplete if there are any units 
    # which cannot be reached by target unit
    if unreachable := graph.get_unreachable_nodes(graph.get_node_by_value(target_unit)):
        # i.e. not fully connected graph
        raise BadTypeDefinition(f"Missing unit conversions for {unreachable}")

    # get aliases if they are included
    allowed_names, inverted_aliases = read_aliases(validity, units)

    # check if a numerical range is specified
    if RANGE.name in validity:
        # validate it and generate a checker function
        range_valid, _ = create_range_constraint(validity)

    convert_to_target = lambda value: unit_expr_to_target_number(value, graph, inverted_aliases, target_unit)

    # valid if combines a number with a unit, or is just a number
    is_valid = lambda value: (
        # it's already a <target unit> and is in required range
        (is_type_or_equivalent(value, float) and range_valid(value)) or
        # we can convert it to target unit and it will be in range
        (unit_expr_valid(value, allowed_names) 
         and range_valid(convert_to_target(value))) 
    )
    # always pass up converted to the target units
    yield_as = convert_to_target

    return is_valid, yield_as
