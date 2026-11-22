# defines constraint handlers for collections - ALL and SIZE
from datatypes.validity.constraints import COLLECTION
from datatypes.validity.constraint_range import create_range_constraint
from valids.casts import is_type_or_equivalent
from datatypes.parameterised_types import PARAMETER_SYMBOL
from datatypes.type_maps import get_type
from datatypes.type_dependency import register_dependent_constraint

ALL = "all"
SIZE = "size"

register_dependent_constraint([COLLECTION.name, ALL])

# only call if COLLECTION constraint present
def create_collection_constraint(validity: dict, specialised_parameters: dict):
    collection = validity[COLLECTION.name]
    # all and size are both optional - technically, collection can be empty

    # default for unspecified size
    size_valid = lambda v: True
    if SIZE in collection:
        # size can be a single integer, or a range dict
        size = collection[SIZE]
        if is_type_or_equivalent(size, int):
            # simple == length check
            size_valid = lambda v, size=size: len(v) == size
        elif is_type_or_equivalent(size, dict):
            # range dict - defer
            # this will raise error if its not a range
            length_accessor = lambda vs: len(vs)
            size_valid, _ = create_range_constraint(size, access_function=length_accessor)

    # yield pythonically by default
    yield_each = lambda v, p: v
    # true if contents of list obey type constraints
    all_valid = lambda v, p: True
    if ALL in collection:
        # all members of collection must be the given type
        # which may be a parameter lookup
        all_of_type_name = collection[ALL]
        parameter_lookup = None
        if all_of_type_name[0] == PARAMETER_SYMBOL:
            # param lookup
            parameter_lookup = all_of_type_name[1:]
            all_of_type = specialised_parameters[parameter_lookup]
        else:
            # check named type exists
            all_of_type = get_type(all_of_type_name)

        all_valid = (lambda values, params, type=all_of_type, param_lookup=parameter_lookup:
            all([
                # select correct type (may be runtime param)
                (type if not param_lookup else params[param_lookup])
                .is_valid(v) for v in values # check type holds for all values in collection
            ])
        )

        # yield each as the type (which may be a param lookup)
        yield_each = (lambda value, params, type=all_of_type, param_lookup=parameter_lookup:
                      (type if not param_lookup else params[param_lookup]).yield_as(value))
    
    # validity and yield is computed for each type
    is_valid = lambda vs, p: size_valid(vs) and all_valid(vs, p)
    yield_as = lambda vs, p: [yield_each(v, p) for v in vs]

    # ignore the parent yield - yield as the subtype
    # so that most-specialised type for collection contents is used
    arbitrary_combinator = lambda as_child, as_parent: as_child

    return is_valid, yield_as, arbitrary_combinator