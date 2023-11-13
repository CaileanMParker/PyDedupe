from pathlib import Path
from shutil import copytree


def backup(path: Path) -> None:
	"""Make a backup of the target directory

	Parameters
	----------
	path: Path to the target directory
	"""
	backup_path = Path(str(path) + "_backup")
	if not backup_path.exists():
		copytree(path, backup_path)