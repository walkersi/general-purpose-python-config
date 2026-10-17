from datatypes.types import parse_type_file
from jsonio.io import load

type_dict = load("datatypes/built_in.json")
parse_type_file(type_dict)