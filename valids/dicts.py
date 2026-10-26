from valids.casts import is_type_or_equivalent
# functions for working with uncertain dicts more conveniently
# - especially with respect to validation and specific error reporting

# checks if field is a key in dict - if it is, returns the corresponding value.
# if not, throws an exception - either the one provided, or a standard
#  KeyError for this field.
def get_or_error(dictionary: dict, field: str, exception: Exception=None):
    if field in dictionary:
        return dictionary[field]
    # select default exception
    if exception == None:
        exception = KeyError(field)
    raise exception

# checks if field is in dict - if it is, returns corresponding value.
# if not, returns the provided default value
def get_or_default(dictionary: dict, field: str, default):
    if field in dictionary:
        return dictionary[field]
    return default

# tries to put value into dict under field key - returns True if key not already present
# if already present, does not replace original value, returns False
def put_no_replace(dictionary: dict, field: str, value):
    if field in dictionary:
        return False
    dictionary[field] = value
    return True

# tries to put value into dict under field key - errors if key already in dict
# (i.e. does not replace)
# raises a key error (by default)
def put_or_error(dictionary: dict, field: str, value, exception: Exception=None):
    if not put_no_replace(dictionary, field, value):
        raise exception if exception != None else KeyError(f"{field} already has value")

# checks if field is a key in dict AND that its value exactly or losslessly is the given type
# returns it if it is, as the desired type
# if not, raises either KeyError or TypeError accordingly (or the relevant specified exception)
def get_as_type_or_error(dictionary: dict, field: str, desired_type: type, 
                         field_exception: Exception = None, type_exception: Exception = None):
    # check field exists
    value = get_or_error(dictionary, field, exception=field_exception)
    # check if type is valid
    if is_type_or_equivalent(value, desired_type):
        # if it is, cast it (in case type is distinct but coercible)
        return desired_type(value)
    # select default exception
    if type_exception == None:
        type_exception = TypeError(f"Field {field} with value {value} was not of type {desired_type} - actual type was {type(value)}")
    raise type_exception


# checks if field is key in dictionary - if it is, check its type is acceptable
# and return it or throw an error. if it isn't in dict, return default value
def get_as_type_error_default(dictionary: dict, field: str, desired_type: type, default = None, type_exception: Exception = None):
    try:
        # delegate error behaviour
        value_as_type = get_as_type_or_error(dictionary, field, desired_type, 
                                             field_exception=ValueError(), 
                                             type_exception=type_exception)
        return value_as_type
    except ValueError:
        # return the default cos the field isn't present
        return default
    # don't catch the type error

# returns false if the given dictionary's keys all exist in the given key set
# otherwise, returns set of problematic keys
def has_excess_keys(dictionary: dict, keys: set[str]):
    # check excess by set difference
    existing_keys = set(dictionary.keys())
    extra_keys = existing_keys - keys
    if extra_keys:
        return extra_keys
    return False    

# returns true iff the given possible dict is a dict, and has the keys given
# if 'only' is True, returns false if the dict has any keys other than those specified
def is_dict_with_keys(possibly_dict, desired_keys: set[str], only: bool = True):
    # if it isn't a dict, can't have these keys
    if not isinstance(possibly_dict, dict):
        return False
    # get keys in the dict as a set
    present_keys = set(possibly_dict.keys())
    # use set difference to check all are present
    if desired_keys - present_keys:
        return False
    # and that only those keys are present, if this is required
    if only and (present_keys - desired_keys):
        return False
    return True

def is_dict_with_typed_keys(possibly_dict, desired_typed_keys: dict[str, type|set[type]], only: bool = True):
    # check it is a dict with the required keys present
    desired_keys = set(desired_typed_keys.keys())
    if not is_dict_with_keys(possibly_dict, desired_keys, only=only):
        return False
    # check types of the values of each key
    for key in desired_keys:
        # get all possible types of this field
        desired_types = desired_typed_keys[key]
        if type(desired_types) != set:
            desired_types = set(desired_types)
        # see if the value is any of those types
        # flag to track valid option
        valid = False
        for desired_type in desired_types:
            value = possibly_dict[key]
            if is_type_or_equivalent(value, desired_type):
                valid = True
                break
        # dict fails constraints if this field's value does not match any legal types
        if not valid:
            return False
                    
    return True

# all key-values from dict other added to dict main provided that they do not overlap
def merge(dict_main: dict, dict_other: dict):
    for key in dict_other:
        put_no_replace(dict_main, key, dict_other[key])
    return dict_main

# assuming dictionary's VALUES are all unique, 
# returns the values as keys matched to the original keys
def invert(dict: dict):
    for key, value in set(dict.items()):
        del dict[key]
        dict[value] = key
    return dict

# assuming dictionary's values are unique
# and are not equal to any keys
# returns the key-value inversion of the dict merged with the current dict
def and_invert(dict: dict):
    for key, value in set(dict.items()):
        dict[value] = key
    return dict

# given two dicts and a function,
# applies function to all values in dict1 and replaces values with result
# function in form f(v, v2) where v2 is the value under corresponding key in dict2
# assumes dict2 has all keys that are in dict1, does not check!
def apply_function_dict(dict1: dict, dict2: dict, function):
    for key in dict1:
        val = dict1[key]
        val2 = dict2[key]
        dict1[key] = function(val, val2)

    return dict1