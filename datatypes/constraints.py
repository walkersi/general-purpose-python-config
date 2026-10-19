from exceptions.structure_exceptions import *
from valids.dicts import *
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
UNITS = Constraint("units", list, str)
RANGE = Constraint("range", str, dict)
TARGET_UNIT = Constraint("target_unit", str)
ALIASES = Constraint("aliases", dict)
CONVERSION = Constraint("conversion", dict)
CASE_SENSITIVE = Constraint("case_sensitive", bool)

PYTHON.set_compatible_cocostraints()
REGEX.set_compatible_cocostraints()
UNITS.set_required_coconstraints(TARGET_UNIT, CONVERSION)
UNITS.set_compatible_cocostraints(ALIASES, RANGE)
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

def create_enum_constraint(validity: dict):
    # get the possible values and remove repeats
    enum = ENUM.validate(validity)
    enum = set(enum)
    # check for aliases
    aliases = get_or_default(validity, ALIASES.name, {})
    # map from aliases to the canonical name
    inverted_aliases = {}
    for name, equivalents in aliases:
        # these values are also acceptable
        enum |= set(equivalents)
        # but will be normalised to the name when passing up to application
        # add all to the alias to name map
        for equivalent in equivalents:
            # error if duplicate alias
            if not put_no_replace(inverted_aliases, equivalent, name):
                raise BadTypeDefinition(f"Duplicate alias {equivalent} for {name} is not allowed")
        # also map name to name for convenience
        inverted_aliases[name] = name
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
        left_side = "(?P<id>[a-z|A-Z]+[\\d|_|a-z|A-Z]*)[ \\t]*(?P<sign>[<|>]=?)[ \\t]*(?P<bound>(?:\\d+(?:\\.\\d*)?|\\.\\d+))$"
        right_side = "^(?P<bound>(?:\\d+(?:\\.\\d*)?|\\.\\d+))[ \\t]*(?P<sign>[<|>]=?)[ \\t]*(?P<id>[a-z|A-Z]+[\\d|_|a-z|A-Z]*)"
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

            range[range_field] = bound

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

# pairs constraints to their handler function, to be checked in the specified order
SEQUENTIAL_HANDLER_PAIRINGS = [
    (PYTHON, create_pythonic_constraint),
    (REGEX, create_regex_constraint),
    (ENUM, create_enum_constraint),
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
