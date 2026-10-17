import json
from exceptions.config_exceptions import *
from config import Config

# after load_config is called at least once with a valid config file,
# this constant will be bound to the static config
CONFIG = None

# 
def load_config_with_structure(structure_file: str, config_file: str) -> None:
    try:
        with open(config_file, "r") as config_json:
            config_dict = json.load(config_json)
            
            CONFIG = Config(config_dict)

            
    except Config as exc:
        print(exc)
    except Exception:
        raise APIConfigFileInvalid("Error opening or reading api-config.json")