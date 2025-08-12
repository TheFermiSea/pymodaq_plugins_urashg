import importlib
from pathlib import Path

from ...utils import set_logger

logger = set_logger("viewer0D_plugins", add_to_console=False)

path = Path(__file__)

for path_file in Path(__file__).parent.iterdir():
    try:
        if "__init__" not in str(path_file):
            importlib.import_module("." + path_file.stem, __package__)
    except Exception as e:
        logger.warning(
            "{:} plugin couldn't be loaded due to some missing packages or errors: {:}".format(
                path_file.stem, str(e)
            )
        )
        pass
