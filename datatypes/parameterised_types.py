from valids.casts import is_type_or_equivalent
from datatypes.types import DATA
from valids.dicts import get_or_default, get_as_type_or_error, get_as_type_error_default, merge
from exceptions.structure_exceptions import *

# validation parsing of parameterised type definitions
# which may be in parent inheritence field, structure usage field, or structure definition field

# symbol means that value should be interpreted as 'access this parameter' rather than a literal
PARAMETER_SYMBOL = '@'

# given a type defintion (during header parse phase), 
# get a dictionary of {param name: type name}
def parse_parameters_from_header(definition: dict):
    return get_or_default(definition, "parameters", {})

# parse by type/presence checking a dict in form
# that represents an overriden / parameterised type
# {"type": "...", "params": {...}} where params is optional
def parse_parameterised_type(parameterised: dict):
    # validate dict and extract type name
    type_name = get_as_type_or_error(parameterised, "type", str, 
                        field_exception=BadTypeDefinition(f"Parent 'type' field is missing in {parameterised}"),
                        type_exception=BadTypeDefinition(f"Parent 'type' field must be string in {parameterised}"))
    # get param dict (validate later) or default to empty
    params = get_as_type_error_default(parameterised, "parameters", dict, default={},
                        type_exception=BadTypeDefinition(f"Parent 'parameters' field must be dict in {parameterised}"))
    return type_name, params


# parse a parent field, which may or may not have parameters
# assumes that this is called in an order such that the parent exists
# if it is defined anywhere in the file (i.e. use heritage tree)
# returns the parent's name (might be 'data') and any provided params
# does not validate the semantics of the types or params yet
def parse_parent_field(definition: dict):
    # get parent type name (do not validate yet, since field is read sequentially)
    parent_structure = get_or_default(definition, "parent", DATA.get_name())
    if is_type_or_equivalent(parent_structure, str):
        # it's a non parameterised parent, just return the string
        parent_name = parent_structure
        parent_params = {}
        
    elif is_type_or_equivalent(parent_structure, dict):
        # validate dict and extract parent type name and params
        parent_name, parent_params = parse_parameterised_type(parent_structure)
        
    else:
        raise BadTypeDefinition(f"Parent field in {definition} must be a string or a structure in the form" 
                + " {type: name, parameters: {param1: ..., param2: ...}} ")

    return parent_name, parent_params
