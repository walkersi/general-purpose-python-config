from exceptions.structure_exceptions import *
from datatypes.validity.constraint_enum import create_enum_constraint
from datatypes.validity.constraint_python import create_pythonic_constraint
from datatypes.validity.constraint_units import create_units_constraint
from datatypes.validity.constraint_range import create_range_constraint
from datatypes.validity.constraint_regex import create_regex_constraint 
from datatypes.validity.constraint_structure import create_structure_constraint
from datatypes.validity.constraints import *

# pairs constraints to their handler function, to be checked in the specified order
SEQUENTIAL_HANDLER_PAIRINGS = [
    (PYTHON, create_pythonic_constraint),
    (REGEX, create_regex_constraint),
    (ENUM, create_enum_constraint),
    (STRUCTURE, create_structure_constraint),
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
