class FileMissingException(Exception):
    def __init__(self):
        super().__init__("Could not find config file")

class FileInvalidException(Exception):
    def __init__(self):
        super().__init__("Config file could not be parsed")

class FieldMissingException(Exception):
    def __init__(self, field): # TODO data types here
        super().__init__(f"Required field {field} not included")

class FieldValueInvalidException(Exception):
    def __init__(self, field, type):
        super().__init__(f"Value for field {field} was invalid: {type.get_desc()}")