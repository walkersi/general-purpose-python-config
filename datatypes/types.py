# represents a type with a given domain and yield process
from valids.dicts import *
from valids.lists import *
from exceptions.structure_exceptions import BadTypeDefinition
from datatypes.type_maps import RESERVED_NAMES, TYPES


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
        self.__is_valid = valid
        self.__yield_as = (lambda value: value) if yield_as == None else yield_as
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

    # returns true only if the given value is a member of this type
    def is_valid(self, value):
        return self.__is_valid(value)

    # given a value that is valid for this type, returns the value to pass up to
    # application logic derived from that value (they may match)
    def yield_as(self, value):
        return self.__yield_as(value)

# arbitrary parent type for which any information is valid
DATA = Type("data", None, lambda _: True)