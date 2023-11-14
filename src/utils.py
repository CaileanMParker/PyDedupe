from json import load
from pathlib import Path
from shutil import copytree


BASE_DIRECTORY = Path(__file__).parent.parent
with BASE_DIRECTORY.joinpath(r"resources/config.json").open("r") as config_file:
	CONFIGS = load(config_file)


def backup(path: Path) -> None:
	"""Make a backup of the target directory

	Parameters
	----------
	path: Path to the target directory
	"""
	backup_path = Path(str(path) + "_backup")
	if not backup_path.exists():
		copytree(path, backup_path)