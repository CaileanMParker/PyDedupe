from pathlib import Path
from threading import Thread, Event
from time import time
from typing import Generator, Any

from magic import from_buffer, from_file, MagicException  # type: ignore[import-untyped]

from comparator_router import ComparatorRouter  # type: ignore[import-not-found]
from pdd_defaultcomparators.default_comparators import exact_compare  # type: ignore[import-not-found]
from pdd_defaultcomparators.base_classes import File  # type: ignore[import-not-found]
from load_plugins import load_plugins  # type: ignore[import-not-found]


def walk(root: Path) -> Generator[Path, Any, None]:
    try:
        for path in root.iterdir():
            if path.is_dir():
                if path.name.startswith('.') or path.name in ("AppData", "pygame-ce", "bin") or path.is_symlink():
                    continue
                yield from walk(path)
                continue
            yield path
    except PermissionError:
        pass


def run(kill: Event, files: dict[str, list[Path]]) -> None:
    root = Path(r"C:\Users\caiparker\source\repos\duplicate_file_cleaner\tests")
    for file in walk(root):
        if kill.is_set():
            break
        file_type = file.suffix
        # try:
        #     file_type = from_file(str(file), mime=True)
        # except MagicException:
        #     try:
        #         file_type = from_buffer(file.open().read(4096), mime=True)
        #     except Exception:
        #         continue
        # except PermissionError:
        #     continue
        # if file_type not in files:
        #     files[file_type] = []
        # files[file_type].append(file)
        fp = file
        file = File(file, file_type)
        for file2 in files.get(file_type, []):
            if exact_compare(file, File(file2, file_type)):
                print("exact:", file, "==", file2)
        for file_type2 in files:
            for comparator in ComparatorRouter.route(file_type, file_type2):
                for file2 in files[file_type2]:
                    if comparator(file, File(file2, file_type2), 5.0):
                        print("approx:", fp, "==", file2)
        if file_type not in files:
            files[file_type] = []
        files[file_type].append(fp)
    print("!!!DONE!!!")


load_plugins()
files_dict: dict[str, list[Path]] = {}
event = Event()
t = Thread(target=run, args=(event, files_dict))
t0 = time()
t.start()
input("Press enter to stop")
event.set()
t.join()
print((time() - t0)/60, "minutes")
print("\n".join([f"{k}: {len(v)}" for k, v in files_dict.items()]))
