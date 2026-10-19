# functions for casting between data types when it is uncertain if casting is possible
# e.g. JSON does not encode sets, but a JSON array COULD be a valid set

# it is 'safe' to cast from key to any of value
# in that no meaningful information will be lost
# maps key types to a function in form
# f(value) = set of safe casts
SAFE_TO_CAST = {
    int: lambda _: {float},
    set: lambda _: {list},
    # list can cast to set 'safely' if there are no duplicates
    list: lambda v: {set} if len(set(v)) == len(v) else set()
}

# returns true if value is exactly the desired type, or if it can be "losslessly" converted 
# to that type (e.g. int for float, but not float for int)
def is_type_or_equivalent(value, desired_type: type):
    # check whether type matches
    actual_type = type(value)
    if actual_type == desired_type:
        return True
    # check if its a reasonable equivalent
    legal_casts = set()
    if actual_type in SAFE_TO_CAST:
        # given the context of the value specifically
        legal_casts = SAFE_TO_CAST[actual_type](value)
    if desired_type in legal_casts:
        return True

    return False
