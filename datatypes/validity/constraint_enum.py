from valids.dicts import *
from valids.casts import is_type_or_equivalent
from exceptions.structure_exceptions import *
from datatypes.validity.alias_handler import read_aliases
from datatypes.validity.constraints import ENUM, CASE_SENSITIVE


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
