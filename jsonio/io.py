# wrapper for interactions with json
import json

def load(json_file: str):
    with open(json_file, "r") as file:
        return json.load(file)