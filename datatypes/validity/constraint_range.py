from valids.dicts import *
import re
from exceptions.structure_exceptions import *
from datatypes.validity.constraints import TARGET_UNIT, UNITS, CONVERSION, ALIASES, RANGE

# define subfields for range
RANGE_GREATER_THAN = "greater_than"
RANGE_LESS_THAN = "less_than"
RANGE_GREATER_THAN_OR_EQUAL_TO = "greater_than_or_equal_to"
RANGE_LESS_THAN_OR_EQUAL_TO = "less_than_or_equal_to"
RANGE_SUBFIELDS = [RANGE_GREATER_THAN, RANGE_LESS_THAN, 
                   RANGE_GREATER_THAN_OR_EQUAL_TO, RANGE_LESS_THAN_OR_EQUAL_TO]
# define some semantics for working with these subfields
# match range field to logical opposite
RANGE_OPPOSITES = and_invert({RANGE_GREATER_THAN: RANGE_LESS_THAN, 
                   RANGE_GREATER_THAN_OR_EQUAL_TO: RANGE_LESS_THAN_OR_EQUAL_TO})
# match mathematical symbols to the range type, ASSUMING the variable is on the right,
# i.e. 1 < x
RANGE_SYMBOLS = {"<": RANGE_GREATER_THAN, "<=": RANGE_GREATER_THAN_OR_EQUAL_TO, 
                 ">": RANGE_LESS_THAN, ">=": RANGE_LESS_THAN_OR_EQUAL_TO}
# match range fields to actual predicates in terms of value, bound
RANGE_FUNCTIONS = {RANGE_GREATER_THAN: lambda v, b: v > b,
                   RANGE_LESS_THAN: lambda v, b: v < b,
                   RANGE_GREATER_THAN_OR_EQUAL_TO: lambda v, b: v >= b,
                   RANGE_LESS_THAN_OR_EQUAL_TO: lambda v, b: v <= b}


def create_range_constraint(validity: dict):
    # validate this field and co-constraints
    range = RANGE.validate(validity)
    # additionally, if any of the unit conversion subfields are 
    # present without units itself, reject
    if UNITS.name not in validity:
        if not (incompatible := {TARGET_UNIT.name, CONVERSION.name, ALIASES.name} 
                - set(validity.keys())):
            raise BadTypeDefinition(f"Constraints {incompatible} are incompatible with 'range' without a {UNITS.name} constraint in {validity}.")
    
    if is_type_or_equivalent(range, str):
        # if range is a string, it should be in form like 0 <= n < 2
        # so apply a regex to validate
        bounds = str(range).strip()
        left_side = "(?P<id>[a-zA-Z]+[\\d_a-zA-Z]*)[ \\t]*(?P<sign>[<>]=?)[ \\t]*(?P<bound>[\\-\\+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+))$"
        right_side = "^(?P<bound>[\\-\\+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+))[ \\t]*(?P<sign>[<>]=?)[ \\t]*(?P<id>[a-zA-Z]+[\\d_a-zA-Z]*)"
        # left matches 1 < n, right matches n < 2
        left = re.search(left_side, bounds)
        right = re.search(right_side, bounds)

        # TODO support [0,1) notation

        if not (left or right):
            raise BadTypeDefinition(f"Range '{range}' is invalid - must be in form e.g. x1 <= n <= x2")

        if left and right:
            # if both matched, check the signs (<) point the same direction
            # (can ignore any = that may be present)
            if left.group("sign")[0] != right.group("sign")[0]:
                raise BadTypeDefinition(f"Range '{range}' specifies redundant bound (comparison operators should match in direction)")
            if left.start("id") != right.start("id") or left.group("id") != right.group("id"):
                raise BadTypeDefinition(f"Range '{range}' has malformed identifier - must be single alphanumeric word")
            # they point the same direction around the same ID, so we can proceed
            
        # expand range to be in dictionary form
        range = {}

        # given a regex match, adds the relevant key entry to the dict
        def expand_sign_string(range: dict, re_match: re.Match):
            sign = re_match.group("sign")
            bound = re_match.group("bound")
            # if true, ID on right (e.g. 1 < n), else (e.g. n < 2)
            id_on_right = re_match.start('id') > re_match.start('sign')
            # get the range dict field for this operator
            range_field = RANGE_SYMBOLS[sign]
            if not id_on_right:
                # flip it, because the expression is flipped
                range_field = RANGE_OPPOSITES[range_field]

            # attempt to preserve precision for range checks
            range[range_field] = float(bound) if "." in bound else int(bound)

        # generate fields from both sides of equation
        for match in [left, right]:
            if match:
                expand_sign_string(range, match)

    # validate keys present in dictionary
    range_fields = set(range.keys())
    if illegal := (range_fields - set(RANGE_SUBFIELDS)):
        raise BadTypeDefinition(f"Range expression has fields {illegal} which are not allowed")
    # can't have both greater than and great than / equal to
    if not ({RANGE_GREATER_THAN, RANGE_GREATER_THAN_OR_EQUAL_TO} - range_fields) or not ({RANGE_LESS_THAN, RANGE_LESS_THAN_OR_EQUAL_TO} - range_fields):
        raise BadTypeDefinition("Range expression must not mix conflicting boundary definitions")
    # TODO logical check of relationship between values
    
    predicates = []
    # generate the range condition for each
    for constraint in range_fields: # loop through "greater_than", "less_than" etc 
        bound = range[constraint]
        # store args via defaults so that they are not overwritten each iter
        predicate = lambda v, constraint=constraint, bound=bound: (
            RANGE_FUNCTIONS[constraint](v, bound))
        predicates.append(predicate)

    # form final function, which is the intersection of all boundaries
    is_valid = lambda v: all([predicate(v) for predicate in predicates])

    return is_valid, None