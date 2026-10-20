from exceptions.structure_exceptions import *
from exceptions.config_exceptions import *
from valids.dicts import *
from valids.casts import is_type_or_equivalent
from datatypes.units import get_unit_from_expression, UnitConversionGraph
import re
# define rules for interpretting validity dictionaries into constraint checking functions
# and rejecting mis-formatted ones
# all assume that validity is a dictionary made up of ONLY some subset of constrain fields
# all handlers assume that the main field itself is present
# handlers return two functions in form f(value)
#  - first is is_valid function (determine if value exists in this type's domain)
#  - second is yield_as function (what value to pass up to application given config value)
#  - second may be None, in which case just yield as value itself


CONSTRAINTS = set() # collect all possible constraints
CONSTRAINT_FIELDS = dict() # map field name to constraint

class Constraint:
    def __init__(self, name: str, *types: type):
        self.name = name
        # the *python* type(s) that the constraint's value must match or coerce to
        self.types = types
        self.required_coconstraints = set()
        self.incompatible_coconstraints = set()
        # add this to the overall constraint list and map
        CONSTRAINTS.add(self)
        CONSTRAINT_FIELDS[self.name] = self

    # define which other constraints must be present for this type to be valid
    def set_required_coconstraints(self, *constraints: Constraint):
        self.required_coconstraints = set(constraints)

    # define which other constraints must not be present for this type to be valid
    def set_incompatible_coconstraints(self, *constraints: Constraint):
        self.incompatible_coconstraints = set(constraints)

    # define which constraints are allowed to be present to be valid
    # implicitly, disallows anything else (that isn't marked as required)
    def set_compatible_cocostraints(self, *constraints: Constraint):
        self.incompatible_coconstraints = CONSTRAINTS - set(constraints) - set([self]) - self.required_coconstraints

    # given a validity dict that meets the minimum assumptions (described above)
    # return the value of this constraint or throw an error
    def get_from_definition(self, validity: dict):
        # try each type and report the first error if none work
        error = None
        for type in self.types:
            try:
                # if successful, yield the value of constraint's type
                return get_as_type_or_error(validity, self.name, type)
            except TypeError as exc:
                error = exc if not error else error
        raise BadTypeDefinition(error.args)

    # given a validity dict, confirms that:
    # 1) value of this constraint is of correct type
    # 2) dict is acceptable given this constraint's relationship to *other* constraints
    # that may be present
    # then returns the value of this constraint if successful (errors otherwise)
    def validate(self, validity: dict):
        # validate type of this constraint's value
        value = self.get_from_definition(validity)
        # get set of other constraints
        other_constraints = set(map(get_constraint_by_name, set(validity.keys()) - set([self])))
        # check if any incompatible constraints are present
        incompatible = other_constraints & self.incompatible_coconstraints
        if incompatible:
            raise BadTypeDefinition(f"Constraint {self.name} incompatible with constraints: {[c.name for c in incompatible]}")
        # check that all required constraints are present
        missing_required = self.required_coconstraints - other_constraints
        if missing_required:
            raise BadTypeDefinition(f"Constraint {self.name} missing required constraints {[c.name for c in missing_required]}")
        # success - general constraints on this constraint are met
        return value

# define the constraints and their relationships to each other
PYTHON = Constraint("python", str)
REGEX = Constraint("regex", str)
ENUM = Constraint("enum", list)
UNITS = Constraint("units", set, str)
RANGE = Constraint("range", str, dict)
TARGET_UNIT = Constraint("target_unit", str)
ALIASES = Constraint("aliases", dict)
CONVERSION = Constraint("conversion", dict)
CASE_SENSITIVE = Constraint("case_sensitive", bool)

PYTHON.set_compatible_cocostraints()
REGEX.set_compatible_cocostraints()
UNITS.set_compatible_cocostraints(TARGET_UNIT, CONVERSION, ALIASES, RANGE)
RANGE.set_compatible_cocostraints(CASE_SENSITIVE)
ENUM.set_compatible_cocostraints(CASE_SENSITIVE, ALIASES)

# define possible subfields for constraints
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

def get_constraint_by_name(name: str):
    return get_or_error(CONSTRAINT_FIELDS, name, BadTypeDefinition(f"Validity constraint {name} does not exist"))
    
# maps string names of python types to actual types
PYTHON_TYPE_MAPPING = {
    "int": int,
    "str": str,
    "float": float,
    "real": float,
    "bool": bool,
    "boolean": bool,
    "list": list,
    "dict": dict,
    "object": dict,
    "set": set
}

def create_pythonic_constraint(validity: dict):
    # get the requested type as a string and validate coconstraint structure
    python_type_name = PYTHON.validate(validity)
    # lookup the actual type and reject if nonexistent
    python_type = get_or_error(PYTHON_TYPE_MAPPING, python_type_name, 
            exception=BadTypeDefinition(f"Python type {python_type_name} could not be found"))
    # a type is valid under pythonic constraints if it is that type or can be *directly* cast to it
    # type is yielded by casting
    return lambda value: is_type_or_equivalent(value, python_type), lambda value: python_type(value)
    
def create_regex_constraint(validity: dict):
    # get the regex string and validate coconstraint structure
    regex = REGEX.validate(validity)
    # check the regex is valid
    try:
        re.compile(regex)
    except re.PatternError as exc:
        raise BadTypeDefinition(f"Regex {regex} is not a valid regex: {exc.msg}")
    # create the constraint function - must match regex
    # value is assumed to have to be a string too
    return lambda value: is_type_or_equivalent(value, str) and re.search(regex, value) != None, None

# given a dict that may have an aliases dict field,
# and the set of names that are being aliased
# read it if it exists and return aliasing data structures
def read_aliases(container: dict, names: set[str]):
    # set of names that are valid (i.e. names and aliases)
    # these are also *reserved* names
    acceptable_names = names.copy()
    # map from aliases to the canonical name
    inverted_aliases = {}

    # check for aliases
    aliases = get_or_default(container, ALIASES.name, {})

    for name, equivalents in aliases.items():
        # validate the entry
        if not is_type_or_equivalent(name, str):
            raise BadTypeDefinition(f"Name {name} in aliases in {container} must be a string.")
        if not is_type_or_equivalent(equivalents, set):
            if is_type_or_equivalent(equivalents, str):
                # allow single strings to be given as aliases rather than a whole set
                equivalents = set(equivalents)
            else:
                raise BadTypeDefinition(f"Aliases {equivalents} in {container} must be a set of strings without duplicates or a single string.")
        # confirm all aliases are strings
        for equivalent in equivalents:
            if not is_type_or_equivalent(equivalent, str):
                raise BadTypeDefinition(f"Alias '{equivalent}' in {container} must be a string.")

        # sanity casts
        name = str(name)
        equivalents = {str(e) for e in equivalents}

        # these values are also acceptable
        acceptable_names |= set(equivalents)
        # but will be normalised to the name when passing up to application
        # add all to the alias to name map
        for equivalent in equivalents:
            # error if duplicate alias
            if not put_no_replace(inverted_aliases, equivalent, name):
                raise BadTypeDefinition(f"Duplicate alias {equivalent} for {name} is not allowed")
        # also map name to name for convenience
        inverted_aliases[name] = name

    return acceptable_names, inverted_aliases

def create_enum_constraint(validity: dict):
    # get the possible values and reject repeats
    enum = ENUM.validate(validity)
    if len(set(enum)) != len(enum):
        raise BadTypeDefinition(f"Enum includes duplicate values {enum}")
    else:
        enum = set(enum)

    # read and enable aliases
    enum, inverted_aliases = read_aliases(validity, enum)
    
    # check if case sensitivity matters (default, yes)
    case_sensitive = get_or_default(validity, CASE_SENSITIVE.name, True)
    # construct validity checker based on whether or not case matters
    if case_sensitive:
        is_valid = lambda value: value in enum
    else:
        is_valid = lambda value: value.upper() in (map(lambda x: x.upper(), enum))

    # always normalise aliases
    yield_as = lambda value: inverted_aliases[value]

    return is_valid, yield_as
    
def create_range_constraint(validity: dict):
    range = RANGE.validate(validity)
    
    if is_type_or_equivalent(range, str):
        # if range is a string, it should be in form like 0 <= n < 2
        # so apply a regex to validate
        bounds = str(range).strip()
        left_side = "(?P<id>[a-zA-Z]+[\\d_a-zA-Z]*)[ \\t]*(?P<sign>[<>]=?)[ \\t]*(?P<bound>(?:\\d+(?:\\.\\d*)?|\\.\\d+))$"
        right_side = "^(?P<bound>(?:\\d+(?:\\.\\d*)?|\\.\\d+))[ \\t]*(?P<sign>[<>]=?)[ \\t]*(?P<id>[a-zA-Z]+[\\d_a-zA-Z]*)"
        # left matches 1 < n, right matches n < 2
        left = re.search(left_side, bounds)
        right = re.search(right_side, bounds)

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
    for constraint in range_fields:
        bound = range[constraint]
        predicate = lambda v: RANGE_FUNCTIONS[constraint](v, bound)
        predicates.append(predicate)

    # form final function, which is the intersection of all boundaries
    is_valid = lambda v: all([predicate(v) for predicate in predicates])

    return is_valid, None

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

    # TODO range compatibility

    # valid if combines a number with a unit, or is just a number
    is_valid = lambda value: is_type_or_equivalent(value, float) or unit_expr_valid(value, allowed_names)
    # always pass up converted to the target units
    yield_as = lambda value: unit_expr_to_target_number(value, graph, inverted_aliases, target_unit)

    return is_valid, yield_as


# pairs constraints to their handler function, to be checked in the specified order
SEQUENTIAL_HANDLER_PAIRINGS = [
    (PYTHON, create_pythonic_constraint),
    (REGEX, create_regex_constraint),
    (ENUM, create_enum_constraint),
    (UNITS, create_units_constraint),
    (RANGE, create_range_constraint)
]

# matches the validity description to a specific constraint handler based on fields present
def classify_constraint_handler(validity: dict):
    print("Matching constraint handler for validity dictionary:", validity)
    # if validity is empty dict, there are no constraints for this type
    # (i.e. it is just an alias of a parent)
    if len(validity) == 0:
        return lambda _: True
    # check all existing handlers, in priority order
    for field, handler in SEQUENTIAL_HANDLER_PAIRINGS:
        if field.name in validity:
            return handler
    # otherwise, this is not formatted correctly
    raise BadTypeDefinition("Constraints could not be constructed due to lack of primary constraint specified.")
