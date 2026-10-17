# for working easier with lists

# given a value that is either a list or a scalar, 
# return the first scalar from the list (or the scalar itself) and any remaining group
# returns the given exception (or a valueerror) with an empty list
def head_and_tail(maybe_a_list, exception: Exception = None):
    if isinstance(maybe_a_list, list):
        if len(maybe_a_list) == 1:
            return maybe_a_list[0], None
        elif len(maybe_a_list) > 1:
            return maybe_a_list[0], maybe_a_list[1:]
        if exception == None:
            # default exception 
            exception = ValueError("List is empty")
    # it's a scalar, so it is the leader
    return maybe_a_list, None