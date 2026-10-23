from valids.dicts import *
from exceptions.structure_exceptions import *
from datatypes.validity.constraints import ALIASES

# given a dict that may have an aliases dict field,
# and the set of names that are being aliased
# read it if it exists and return aliasing data structures
def read_aliases(container: dict, names: set[str]):
    # set of names that are valid (i.e. names and aliases)
    # these are also *reserved* names
    acceptable_names = names.copy()
    # map from aliases to the canonical name
    inverted_aliases = {}

    # check for aliases
    aliases = get_or_default(container, ALIASES.name, {})

    for name, equivalents in aliases.items():
        # validate the entry
        if not is_type_or_equivalent(name, str):
            raise BadTypeDefinition(f"Name {name} in aliases in {container} must be a string.")
        if not is_type_or_equivalent(equivalents, set):
            if is_type_or_equivalent(equivalents, str):
                # allow single strings to be given as aliases rather than a whole set
                equivalents = set(equivalents)
            else:
                raise BadTypeDefinition(f"Aliases {equivalents} in {container} must be a set of strings without duplicates or a single string.")
        # confirm all aliases are strings
        for equivalent in equivalents:
            if not is_type_or_equivalent(equivalent, str):
                raise BadTypeDefinition(f"Alias '{equivalent}' in {container} must be a string.")

        # sanity casts
        name = str(name)
        equivalents = {str(e) for e in equivalents}

        # these values are also acceptable
        acceptable_names |= set(equivalents)
        # but will be normalised to the name when passing up to application
        # add all to the alias to name map
        for equivalent in equivalents:
            # error if duplicate alias
            if not put_no_replace(inverted_aliases, equivalent, name):
                raise BadTypeDefinition(f"Duplicate alias {equivalent} for {name} is not allowed")
    # make sure real names map to themselves for lookup
    for name in names:
        # also map name to name for convenience
        inverted_aliases[name] = name

    return acceptable_names, inverted_aliases

