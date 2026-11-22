from datatypes.type_maps import print_all_types, get_type
from datatypes.type_generation import parse_type_files
from jsonio.io import load
import json

type_dict = load("datatypes/built_in_primitive.json")
type_dict2 = load("datatypes/built_in_complex.json")
type_dict3 = load("datatypes/built_in_poly.json")
type_dict4 = load("datatypes/built_in_collection.json")
type_dict5 = load("datatypes/built_in_application.json")
parse_type_files(type_dict, type_dict2, type_dict3, type_dict4, type_dict5)
print_all_types()

# test type values
integer = get_type("int")
string = get_type("string")
float = get_type("real")
char = get_type("character")
positive_number = get_type("positive number")
boolean = get_type("boolean")
duration = get_type("duration")
percent = get_type("percent")
obj = get_type("object")
keyed_obj = get_type("keyed object")
sub = get_type("test sub object")
set_type = get_type("set")
set_of = get_type("set of")
at_least_one = get_type("set of at least one")
set_of_strings = get_type("set of three strings")
ip_address = get_type("ip")

"""
while True:
    value = input(":: ")
    valid = percent.is_valid(value)
    print(valid)
    if valid:
        print("Yield as: ", percent.yield_as(value))
"""

def valid_yield(value, type):
    valid = type.is_valid(value)
    print(valid, "for", type.name)
    if valid:
        print("Yield as: ", type.yield_as(value))


while True:
    try:
        value = json.loads(input(":: "))
        valid_yield(value, ip_address)
    except json.JSONDecodeError:
        print("Bad Json")