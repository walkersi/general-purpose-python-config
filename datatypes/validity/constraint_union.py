from valids.dicts import get_as_type_or_error, get_as_type_error_default
from valids.casts import all_of_type_or_equivalent
from datatypes.validity.constraints import UNION
from datatypes.parameterised_types import resolve_type_name
from exceptions.structure_exceptions import BadTypeDefinition
from datatypes.type_dependency import register_dependent_constraint

# union types are valid if their value is valid for any of the types in the union
# they yield_like some other arbitrary type (which may be in the union)
# -- typically, the yield_like type should be in the union or a parent of one of the union types

# union validity dict should be structured like:
# "union": {
#    "types": ["some type name", "another type"],
#    "yields_like": "another type"
# }



UNION_TYPES = "types"
YIELDS_LIKE = "yields_like"
register_dependent_constraint([UNION.name, UNION_TYPES])
register_dependent_constraint([UNION.name, YIELDS_LIKE])

# these can be parameterised, because the union types can be like @param_name
def create_union_constraint(validity: dict, specialised_parameters: dict):
    union = validity[UNION.name]
    # get the type names, which may be param lookups
    union_of_type_names = get_as_type_or_error(union, UNION_TYPES, list, 
        field_exception=BadTypeDefinition(f"Union {union} requires a {UNION_TYPES} field containing a list of type names."),
        type_exception=BadTypeDefinition(f"{UNION_TYPES} in {union} field must be a list of type names."))

    # reject empty unions (unions of 1 are allowed - used for casting the yield of a type)
    if not union_of_type_names:
        raise BadTypeDefinition(f"Union {UNION_TYPES} field in {union} must not be empty")

    # must all be strings
    if not all_of_type_or_equivalent(union_of_type_names, str):
        raise BadTypeDefinition(f"Union {UNION_TYPES} field in {union} must be a list of string type names, which may be parameter lookups.")

    # contains tuples either referencing a runtime parameter or a concrete type
    # in form: parameter name or None, Type instance or none
    type_lookups = []
    # check type names are valid
    for type_name in union_of_type_names:
        type_lookups.append(resolve_type_name(type_name))

    # collect the is_valids of each type together 
    # is_valid(value) must be true for at least one type in union
    union_valids = (lambda value, params=None, types=type_lookups:
        any([
            # select correct type (may be runtime param)
            (type[1] if not type[0] else params[type[0]])
            .is_valid(value) for type in types
        ])
    )

    # if 'yield_like' field specified, it must be a type name or param
    # default to just the first type in the union
    yield_like_type = get_as_type_error_default(union, YIELDS_LIKE, str, union_of_type_names[0],
        type_exception=BadTypeDefinition(f"{YIELDS_LIKE} field in {union} must be a string type or parameter lookup."))
    parameter_lookup, actual_type = resolve_type_name(yield_like_type)

    yield_as = (lambda value, params=None, type=actual_type, parameter_lookup=parameter_lookup:
                (type if not parameter_lookup else params[parameter_lookup])
                .yield_as(value))
    
    arbitrary_combinator = lambda as_child, as_parent: as_child

    return union_valids, yield_as, arbitrary_combinator
