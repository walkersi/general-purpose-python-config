# parses arbitrary type definitions from dict (from json)
from valids.dicts import *
from valids.lists import *
from datatypes.constraints import *
from exceptions.structure_exceptions import BadTypeDefinition

TYPES = {} # mappings of type name to Type
RESERVED_NAMES = {} # set all names reserved as types or aliases

# comments can be in string/array fields under this name
COMMENT = "__comment"

class Type:
    # where valid is a predicate on a given value that returns true if the given value
    # is of this type (incorporating parent predicates)
    def __init__(self, name: str, parent: Type, valid, description = None, aliases: list = None):
        # system uses this name, users can use aliases if they want to
        self.name = name
        # store parent (which may be the default root, data)
        self.parent = parent
        # store as method-like
        self.is_valid = valid
        # use the name as the default description if not provided
        self.description = description if description else name
        # there may be no aliases
        self.aliases = set(aliases) if aliases else {}
        self.aliases.add(name)
        # add the name-Type mapping and update the set of reserved name/aliases
        TYPES[self.name] = self
        RESERVED_NAMES |= aliases

    def get_parent(self):
        return self.parent

    # returns a human-readable description of the constraints of this type
    # typically in the form "Must be ..."
    # for error reporting
    def get_description(self):
        return self.description

    # returns the *main* name for this type (other aliases may be accepted)
    def get_name(self):
        return self.name

# arbitrary parent type for which any information is valid
DATA = Type("data", None, lambda _: True)

# returns the set of names from given name/aliases that are already in use
def check_reserved_names(type_name: str, aliases: list):
    aliases = set(aliases) if aliases else {}
    aliases.add(type_name)    
    return aliases & RESERVED_NAMES

def default_or_of_type(definition: dict, field: str, desired_type: type, default):
    return get_as_type_error_default(definition, field, desired_type, default,
                type_exception=BadTypeDefinition(f"Field {field} must be a {desired_type} in entry {definition}"))

def reject_unrecognised_keys(dictionary: dict, recognised: set[str]):
    # always allow comments
    recognised |= COMMENT
    # check for unknown keys
    excess = has_excess_keys(dictionary, recognised)
    if excess:
        raise BadTypeDefinition(f"Keys {excess} are unrecognised in {dictionary}")

# returns a function in form f(value) -> bool which is true if a value is valid for a given type
# note that this should ALWAYS be evaluated in inheritance order to be correct
def construct_validity_constraints(validity: dict, parent_type):
    if parent_type:
        # get the parent type's constraints
        parent_valid = parent_type.is_valid

    reject_unrecognised_keys(validity, CONSTRAINT_FIELDS)

    if "python" in validity:
        validity = create_pythonic_constraint(validity)


    # combine with the parent's constraints
    return lambda value: parent_valid(value) and validity(value)
        

# parse an individual type definition entry and return a Type or throw an error
def parse_type(definition: dict):
    # all types need a name (or group of aliases)
    if not is_dict_with_typed_keys(definition, {"name": {list, str}}, only=False):
        raise BadTypeDefinition(f"Type has no name field in type {definition}")

    # get the main type name and its aliases
    type_name, aliases = head_and_tail(definition["name"])
    # check there are no conflicts
    reserved = check_reserved_names(type_name, aliases)
    if reserved:
        raise BadTypeDefinition(f"Type name(s) must be unique - {reserved} are already in use")

    # check for an existing parent type
    parent_type_name = default_or_of_type(definition, "parent", str, DATA.get_name())
    parent_type = get_or_error(TYPES, parent_type_name, 
                               exception=BadTypeDefinition(f"Parent type {parent_type_name} could not be found for type {type_name}"))
    # TODO if user defined type is child of type later in file, this will error. fix.

    # get the description or leave blank
    type_description = default_or_of_type(definition, "description", str, None)

    # get the validity field
    type_valid = default_or_of_type(definition, "valid", dict, {})
    construct_validity_constraints



def parse_type_file(type_file: dict):
    type_definitions = get_as_type_or_error(type_file, "data_types", list)

    for defintion in type_definitions:
        parse_type(defintion)

    