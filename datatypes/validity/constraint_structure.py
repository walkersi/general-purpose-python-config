# constraint used to specify the structure of dictionaries
from exceptions.structure_exceptions import *
from exceptions.config_exceptions import FieldMissingException, FieldValueInvalidException
from datatypes.validity.constraints import STRUCTURE, EXTENSIBLE
from valids.casts import is_type_or_equivalent
from valids.dicts import *
from datatypes.type_maps import get_type

# sub fields in structure field clarification dicts
STRUCTURE_TYPE_NAME = "name"
STRUCTURE_REQUIRED = "required"
STRUCTURE_DEFAULT = "default"

# arbitrary sentinel: represents No default (do not use None; that could be a default value)
NO_DEFAULT_VALUE = object()

# returns the value of given field from value descriptor or throws error
# use require/default to permit omitted values
def get_substructure_field(value_descriptor: dict, field:str, type: type, require=True, default=NO_DEFAULT_VALUE):
    # the type exception to throw if field value is wrong type
    type_exception = BadTypeDefinition(f"Field {field} must be of type {type} in structure descriptor {value_descriptor}")
    # handle required/default
    if require:
        return get_as_type_or_error(value_descriptor, field, type,
            field_exception=BadTypeDefinition(f"Field {field} is required in structure descriptor {value_descriptor}"),
            type_exception=type_exception)
    else:
        return get_as_type_error_default(value_descriptor, field, type, default=default,
            type_exception=type_exception)


# TODO support for list & set structures

def create_structure_constraint(validity: dict):
    # extract the desired structure
    desired_structure = STRUCTURE.validate(validity)
    # get the keys in this object, as they are written (not necessarily final names)
    keys_as_written = set(desired_structure.keys())

    # check whether this struct is extensible (can have more keys than just those described)
    extensible = False if EXTENSIBLE.name not in validity else EXTENSIBLE.validate(validity)

    # make a list to hold a series of predicates that match for this structure
    # all in form p(structure) = True | False
    validator = []
    # map of field -> values to add when yielding, only if not present already
    default_fields = {}
    # map of fields -> app-types to yield recursively
    field_types = {}
    # check each key's value has a valid type
    for key in keys_as_written:
        # check what the descriptor format is - a type string, or a dict
        value_descriptor = desired_structure[key]
        # string descriptor is just a type
        if is_type_or_equivalent(value_descriptor, str):
            value_type_name = value_descriptor
            # by default assume it is required
            value_required = True
            value_default = NO_DEFAULT_VALUE
        elif is_type_or_equivalent(value_descriptor, list):
            # if the descriptor is a list, denotes non-required type [type, default]
            if len(value_descriptor) != 2:
                raise BadTypeDefinition(f"Descriptor {value_descriptor} for key {key} in {validity} not valid: must be in form [type, default]")
            # extract / infer properties
            value_type_name = value_descriptor[0]
            value_required = False
            value_default = value_descriptor[1]
        elif is_type_or_equivalent(value_descriptor, dict):
            # otherwise, should be a dict clarifying structure
            value_type_name = get_substructure_field(value_descriptor, STRUCTURE_TYPE_NAME, str)
            value_required = get_substructure_field(value_descriptor, STRUCTURE_REQUIRED, bool, required=False, default=True)
            # check for a default value present
            value_default = get_or_default(value_descriptor, STRUCTURE_DEFAULT, NO_DEFAULT_VALUE)
        else:
            raise BadTypeDefinition(f"Value for key {key} in structure for {validity} must be type string or full dict")

        # can't require a value and give a default, doesn't make sense
        if value_required and value_default != NO_DEFAULT_VALUE:
            raise BadTypeDefinition(f"Key {key} in structure {validity} is required so must not provide a default value")

        # check app-type actually exists
        value_type = get_type(value_type_name)
        # app-type check the default value if it was specified
        if value_default != NO_DEFAULT_VALUE:
            if not value_type.is_valid(value_default):
                raise BadTypeDefinition(f"Default value {value_default} for {key} was not a member of specified type {value_type_name} in {validity}")

        # map this field to its type
        field_types[key] = value_type

        # create this key-value's constraint
        if value_required:
            # true only if field present and value valid
            is_valid = (lambda struct, field=key, type=value_type: 
                value_type.is_valid(get_or_error(struct, field, FieldMissingException(f"{struct} requires field {field}"))))
        else:
            # true if field is present with value valid, or field not present
            is_valid = (lambda struct, field=key, type=value_type:
                        True if field not in struct else type.is_valid(struct[field])
                        )

        # add the valid predicate to the list
        validator.append(is_valid)
            
        if not value_required and value_default != NO_DEFAULT_VALUE:
            # not required, default specified, so add to the defaults map
            default_fields[key] = value_default

    # this structure is valid only when all field constraints hold
    is_valid = (lambda value, valids=validator: 
                is_type_or_equivalent(value, dict) and
                all([p(value) for p in valids])
                )
    if not extensible:
        # inextensible structures have the extra constraint of NO OTHER KEYS
        # other than those described
        is_valid = (lambda value, keys=keys_as_written, valids=is_valid:
                    valids(value) and not (set(value.keys()) - keys)
                    )

    # structure yields as itself with sub-types yielded accordingly
    yield_as = (lambda value, default_fields=default_fields, field_types=field_types:
                apply_function_dict((
                    merge(value, default_fields) # add any missing defaults
                ), field_types, lambda v1, v2: v2.yield_as(v1)) # get yield value of each field
                )

    return is_valid, yield_as