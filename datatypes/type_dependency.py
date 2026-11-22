from valids.dicts import get_as_type_or_default
from valids.casts import is_type_or_equivalent, all_of_type_or_equivalent
from datatypes.parameterised_types import PARAMETER_SYMBOL

# for a valid dictionary, check these field paths for a string
# that is a dependent type
# these are in the form ["...", "....", "...."] where an empty string signifies "all fields"
FIELD_PATHS = []

def register_dependent_constraint(dependency_path):
    if len(dependency_path) == 0:
        # ignore empty lists
        return
    elif dependency_path in FIELD_PATHS:
        # ignore re-registrations
        return
    FIELD_PATHS.append(dependency_path)


# given a root dictionary and a possible field path containing a possible type (or type set)
# returns all found type names
def follow_field_path(root: dict, path: list):
    # get next field
    field = path[0]
    path = path[1:]

    # which fields to check out
    target_fields = []
    if field == "":
        # empty string means 'all children of this'
        target_fields = [key for key in root]
    else:
        # just the stated field, if it exists
        target_fields = [field] if field in root else []

    # are we at the end of the path?
    if len(path) == 0:
        result = set()
        for field in target_fields:
            value = root[field]
            # allow strings or lists of strings for referenced type names
            # these may be param lookups, but they will be filtered out later
            if is_type_or_equivalent(value, str):
                result.add(value)
            elif is_type_or_equivalent(value, list):
                if all_of_type_or_equivalent(value, str):
                    for type_name in value:
                        result.add(type_name)
        return result

    # otherwise, keep recursing
    result = set()
    for field in target_fields:
        # go down all key's paths
        subpath = follow_field_path(root[field], path)
        for type_name in subpath:
            result.add(type_name)
    return result



# given a type definition, returns a list of names of dependent types
# uses some information already validated from header parsing
def dependent_types(type_definition: dict, parent_name: str, parent_parameter_overrides: dict):
    dependencies = set([parent_name])

    # add the parent param types as dependencies
    for _, type_name in parent_parameter_overrides.items():
        if is_type_or_equivalent(type_name, str):
            add_dependency(dependencies, type_name)

    # add any params stated in this type itself
    parameters = get_as_type_or_default(type_definition, "parameters", {}, dict)
    for _, type_name in parameters.items():
        if is_type_or_equivalent(type_name, str):
            add_dependency(dependencies, type_name)

    # grab validity dict
    validity = get_as_type_or_default(type_definition, "valid", {}, dict)
    # check all the registered validity paths
    if validity:
        for path in FIELD_PATHS:
            discovered = follow_field_path(validity, path)
            for type_name in discovered:
                add_dependency(dependencies, type_name)
            
    return dependencies

def add_dependency(dependencies: set, dependency: str):
    # ignore parameter lookups
    if dependency[0] == PARAMETER_SYMBOL:
        return
    dependencies.add(dependency)