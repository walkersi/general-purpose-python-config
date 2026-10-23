import re
from valids.casts import is_type_or_equivalent
from exceptions.structure_exceptions import *
from datatypes.validity.constraints import REGEX

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
