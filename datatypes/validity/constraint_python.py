from valids.dicts import *
from valids.casts import is_type_or_equivalent
from exceptions.structure_exceptions import *
from datatypes.validity.constraints import PYTHON

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
    "set": set,
    "bytes": bytes
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
