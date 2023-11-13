from pathlib import Path
from random import choice, choices, randint
from shutil import copy, copytree, rmtree


NUM_COPIES_DISTRIBUTION = tuple([1] * 70 + [2] * 20 + [3] * 10)


base_path = Path(__file__).parent
samples_path = base_path / "samples" / "images"
samples = [path for path in samples_path.iterdir() if path.is_file()]
testing_grounds_path = base_path / "testing-grounds"
sample_directories = [testing_grounds_path / str(i) for i in range(3)]
for directory in sample_directories:
	if directory.exists():
		rmtree(directory, ignore_errors=True)
	copytree(samples_path, directory, dirs_exist_ok=True)
	duplicates = choices(samples, k=randint(0, len(samples) // 3 + 1))
	for duplicate in duplicates:
		for i in range(choice(NUM_COPIES_DISTRIBUTION)):
			copy(duplicate, directory / (duplicate.stem + f"-COPY{i}" + duplicate.suffix))