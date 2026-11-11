from exceptions.structure_exceptions import *
from datatypes.validity.constraint_enum import create_enum_constraint
from datatypes.validity.constraint_python import create_pythonic_constraint
from datatypes.validity.constraint_units import create_units_constraint
from datatypes.validity.constraint_range import create_range_constraint
from datatypes.validity.constraint_regex import create_regex_constraint 
from datatypes.validity.constraint_structure import create_structure_constraint
from datatypes.validity.constraint_collections import create_collection_constraint
from datatypes.validity.constraints import *

# pairs constraints to their handler function, to be checked in the specified order
SEQUENTIAL_HANDLER_PAIRINGS = [
    (PYTHON, create_pythonic_constraint),
    (REGEX, create_regex_constraint),
    (COLLECTION, create_collection_constraint), # collection size, and member types
    (ENUM, create_enum_constraint),
    (STRUCTURE, create_structure_constraint),
    (UNITS, create_units_constraint),
    (RANGE, create_range_constraint)
]

DEFAULT_VALID = lambda _v, _p: True
DEFAULT_YIELD = lambda _v, _p: _v
DEFAULT_COMBINATOR = lambda _as_child, _as_parent: _as_child

# generic constraints take the extra arg of 'specialised parameters' to construct
GENERIC_CONSTRAINTS = set([STRUCTURE, COLLECTION])
# constraints that are 'yield with' (rather than yield as) yield dependent on parent
# behaviour too. to do this, they return a 3rd 'combinator' function that,
# given a parent's yielded value and the child's yielded value, combines into a final yielded value
# combinator function is in form: f(yield_as_child, yield_as_parent) -> (value, params) where those inputs are both functions

# matches the validity description to a specific constraint handler based on fields present
def classify_constraint_handler(validity: dict):
    print("Matching constraint handler for validity dictionary:", validity)
    # if validity is empty dict, there are no constraints for this type
    # (i.e. it is just an alias of a parent)
    if len(validity) == 0:
        # unconstrained valid/yield
        return lambda _v, _p=None: (DEFAULT_VALID, DEFAULT_YIELD)
    # check all existing handlers, in priority order
    for field, handler in SEQUENTIAL_HANDLER_PAIRINGS:
        if field.name in validity:
            if field in GENERIC_CONSTRAINTS:
                return handler
            else:
                # discard specialised params for non generics
                return (lambda valid_dict, _, h=handler: h(valid_dict))
    # otherwise, this is not formatted correctly
    raise BadTypeDefinition("Constraints could not be constructed due to lack of primary constraint specified.")
