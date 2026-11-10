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
        self._is_valid = valid
        self._yield_as = (lambda value: value) if yield_as == None else yield_as
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
        return self._is_valid(value)

    # given a value that is valid for this type, returns the value to pass up to
    # application logic derived from that value (they may match)
    def yield_as(self, value):
        return self._yield_as(value)

# type composed of a single scalar value
# e.g. a string, integer, or a list (without constraints on its contents)
# scalars therefore cannot be parameterised because they do not have internal subtypes
class ScalarType(Type):
    def is_valid(self, value):
        return self._is_valid(value)

    def yield_as(self, value):
        # ignore params
        return self._yield_as(value)

# a type that can be parameterised
# composed of multiple subtypes that may also be generic
# all child types of a generic are inherently GenericType (?)
class GenericType(Type):
    # where parameters is the FULL param dict (inherited/overridden from parentage)
    def __init__(self, name: str, parent: Type, parameters: dict,
                     valid, yield_as = None, description = None, aliases: list = None):
        super().__init__(name, parent, valid, 
            yield_as=yield_as, description=description, aliases=aliases)

        self.parameters = parameters
        

    # returns true if this vector has ALL given parameter names
    def has_params(self, parameters: dict):
        return not (set(parameters.keys()) - set(self.parameters.keys()))


    def get_params(self):
        return self.parameters

    # returns true if [value] is valid for this type GIVEN defined parameters
    # param values can be incomplete - defaults used instead
    def is_valid(self, value):
        return self._is_valid(value, self.parameters)

    def yield_as(self, value):
        return self._yield_as(value, self.parameters)


# arbitrary parent type for which any information is valid
DATA = Type("data", None, lambda _v, _p=None: True)