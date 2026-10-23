from exceptions.structure_exceptions import *
from exceptions.config_exceptions import *
from valids.dicts import *

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
RANGE.set_compatible_cocostraints(UNITS, TARGET_UNIT, CONVERSION, ALIASES)
ENUM.set_compatible_cocostraints(CASE_SENSITIVE, ALIASES)

def get_constraint_by_name(name: str):
    return get_or_error(CONSTRAINT_FIELDS, name, BadTypeDefinition(f"Validity constraint {name} does not exist"))