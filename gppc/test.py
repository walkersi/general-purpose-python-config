from datatypes.types import parse_type_files, print_all_types, get_type
from jsonio.io import load

type_dict = load("datatypes/built_in_primitive.json")
type_dict2 = load("datatypes/built_in_complex.json")
parse_type_files(type_dict, type_dict2)
print_all_types()

# test type values
integer = get_type("int")
string = get_type("string")
float = get_type("real")
char = get_type("character")
positive_number = get_type("positive number")
boolean = get_type("boolean")
duration = get_type("duration")

while True:
    value = input(":: ")
    valid = duration.is_valid(value)
    print(valid)
    if valid:
        print("Yield as: ", duration.yield_as(value))