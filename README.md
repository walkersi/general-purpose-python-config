# general-purpose-python-config
GPPC is a library for defining json config structures in json files and interacting with said config at runtime

## Config... for config
Define the structure, types, and semantics of a config in a JSON file, then use that to validate application config files according to that structure (that are also JSONs).

Also:
- automatically generate a default configuration file
- automatically generate python code to programmatically access config through constants
- deliver useful errors to the user/programmer who is using the config
  - useful enough to pass up to application / GUI settings!
- manipulate conifg at runtime and subscribe to changes if polling doesn't suit you
- types with flexible structure, validation, unit conversion
- autogeneration of config defined enums as code

## Dependencies
- Python3
- functools (https://docs.python.org/3/library/functools.html)
