# static collections of all loaded types and helper methods
from exceptions.structure_exceptions import UndefinedType
from valids.dicts import get_or_error

TYPES = {} # mappings of type name to Type
RESERVED_NAMES = set() # set of all names reserved as types or aliases

# returns all unique types
def get_all_types():
    return set(TYPES.values())

# returns set of all canonical names of types
def get_all_type_names():
    return {type.name for type in get_all_types()}

# returns set of all type names AND aliases
def get_all_type_aliases():
    return RESERVED_NAMES

# returns type given its canonical name or alias
# or throws a useful error UndefinedType
def get_type(name: str):
    return get_or_error(TYPES, name, UndefinedType(f"Type {name} does not exist."))

def print_all_types():
    for name in get_all_type_names():
        print(f"Type: {name}")

# returns the set of names from given name/aliases that are already in use
def check_reserved_names(type_name: str, aliases: list):
    aliases = set(aliases) if aliases else set()
    aliases.add(type_name)    
    return aliases & RESERVED_NAMES