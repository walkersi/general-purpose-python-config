# parses arbitrary type definitions from dict (from json)
from valids.dicts import *
from valids.lists import *
from abstracts.tree import Tree
from datatypes.constraints import *
from exceptions.structure_exceptions import BadTypeDefinition
from collections import deque

TYPES = {} # mappings of type name to Type
RESERVED_NAMES = set() # set of all names reserved as types or aliases

# comments can be in string/array fields under this name
COMMENT = "__comment"

class Type:
    # where valid is a predicate on a given value that returns true if the given value
    # is of this type (incorporating parent predicates)
    # where yield as is a function in form f(value) which returns what value should be passed up
    # to the application from a given config value (e.g. to resolve aliases to a default)
    # by default, pass up the value as-is
    def __init__(self, name: str, parent: Type, 
                 valid, yield_as = None, description = None, aliases: list = None):
        # system uses this name, users can use aliases if they want to
        self.name = name
        # store parent (which may be the default root, data)
        self.parent = parent
        # store as method-like
        self.is_valid = valid
        self.yield_as = (lambda value: value) if yield_as == None else yield_as
        # use the name as the default description if not provided
        self.description = description if description else name
        # there may be no aliases
        self.aliases = set(aliases) if aliases else set()
        self.aliases.add(name)
        # add the name-Type mapping and update the set of reserved name/aliases
        global RESERVED_NAMES, TYPES
        for alias in self.aliases:
            TYPES[alias] = self
        RESERVED_NAMES |= self.aliases

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
    recognised.add(COMMENT)
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

    reject_unrecognised_keys(validity, set(CONSTRAINT_FIELDS.keys()))

    # get the correct constraint handler function
    handler = classify_constraint_handler(validity)
    # process constraint according to handler
    child_is_valid, yield_as = handler(validity)
    # combine with parent's constraints
    is_valid = lambda value: parent_valid(value) and child_is_valid(value)
    
    # return constraint pair
    return is_valid, yield_as
        

# parse an the header fields of a type definition (name/description/parent)
# and throw an error if any are wrong, else return
# name, aliases, parent type name, description
def parse_type_header(definition: dict):
    # all types need a name (or group of aliases)
    if not is_dict_with_typed_keys(definition, {"name": {list, str}}, only=False):
        raise BadTypeDefinition(f"Type has no name field in type {definition}")

    # get the main type name and its aliases
    type_name, aliases = head_and_tail(definition["name"])
    # check there are no conflicts
    reserved = check_reserved_names(type_name, aliases)
    if reserved:
        raise BadTypeDefinition(f"Type name(s) must be unique - {reserved} are already in use")

    print("Parsing type header:", type_name)

    # get parent type name (do not validate yet, since field is read sequentially)
    parent_type_name = default_or_of_type(definition, "parent", str, DATA.get_name())

    # get the description or leave blank
    type_description = default_or_of_type(definition, "description", str, None)

    return type_name, aliases, parent_type_name, type_description

# having parsed the header successfully and constructed a parent tree, use
# this to construct all Types from the root down
def parse_type_body(definition, name, aliases, parent_name, description):
    print("Parsing type body:", name)
    # validate the parent type exists
    parent_type = get_or_error(TYPES, parent_name, 
                               exception=BadTypeDefinition(f"Parent type {parent_name} could not be found for type {name}"))
    
    # get the validity field and parse into constraint functions
    type_valid = default_or_of_type(definition, "valid", dict, {})
    is_valid, yield_as = construct_validity_constraints(type_valid, parent_type)

    # create the type
    defined_type = Type(name, parent_type, is_valid, yield_as=yield_as, 
                        description=description, aliases=aliases)

    print("Created type:", name)

    return defined_type

def parse_type_files(*type_files: dict):
    # get the datatypes container for each
    type_definitions = []
    for type_file in type_files:
        type_definitions.append(get_as_type_or_error(type_file, "data_types", list))

    # if they all were valid arrays, combine them into an overall type spec
    type_definition = []
    for definition_group in type_definitions:
        type_definition += definition_group
    # header parsing will automatically handle name conflicts.

    # parse all headers to construct heritage tree
    # this prevents data_types from being order sensitive
    # i.e. you can define the parent later in the file
    stubs_by_parent = {} # map parent name to set of children
    stubs_by_name = {} # map type name to stub

    for definition in type_definitions:
        # validate the header
        name, aliases, parent_name, description = parse_type_header(definition)
        # construct type stub as tuple 
        stub = (definition, name, aliases, parent_name, description)
        # file it under its parent
        put_no_replace(stubs_by_parent, parent_name, [])
        stubs_by_parent[parent_name].append(stub)
        stubs_by_name[name] = stub


    # everything descends from DATA
    heritage_tree = Tree(DATA.get_name())
    nodes = deque([heritage_tree.value])
    # add all children to tree
    while True:
        # until all groups dealt with
        if not stubs_by_parent:
            break
        # get the next group of children
        node = nodes.popleft()
        children = stubs_by_parent[node]
        del stubs_by_parent[node]
        # add them to the tree
        for child in children:
            heritage_tree.add_child_to(node, child[1])
            # and queue their children to now be added (if not a leaf)
            if child[1] in stubs_by_parent:
                nodes.append(child[1])
    print("Generated type hierarchy tree")
    
    # tree now constructed, generate parsing order
    parse_order = heritage_tree.breadth_first()
    # pop 'data' from parsing as it is fully built it
    parse_order.pop(0)

    for stub_name in parse_order:
        parse_type_body(*(stubs_by_name[stub_name]))

    print("Parsed type file")

# returns all unique types
def get_all_types():
    return set(TYPES.values())

# returns set of all canonical names of types
def get_all_type_names():
    return set([type.name for type in get_all_types()])

# returns set of all type names AND aliases
def get_all_type_aliases():
    return RESERVED_NAMES

# returns type given its canonical name or alias
def get_type(name: str):
    return get_or_error(TYPES, name, UndefinedType(f"Type {name} does not exist."))

def print_all_types():
    for name in get_all_type_names():
        print(f"Type: {name}")