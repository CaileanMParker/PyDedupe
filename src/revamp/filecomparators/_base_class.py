from abc import ABC, abstractmethod
from collections.abc import Callable
from multiprocessing import Lock
from pathlib import Path
from typing import Any, Self


# Settled: discovery process will maintain master dict of file types and their corresponding file paths

# Should comparators be small classes (either Singleton (why? probably not), static classes, or stateless instances), or should they just be functions?
# Either needs to be registered against the "factory", so instead of just registering the class, the registration could entail passing in the other metadata...

# Necessary comparison metadata: 1. 2x file types, 2. comparison type (diff or equal), 3. comparison function, 4. threshold (if applicable)

# It **IS** necessary to differentiate between exact and approximate comparisons. For example, an exact picture hash is file1.read() == file2.read(), but an approximate picture hash is a perceptual hash comparison, which can "match" even slightly different files on a threshold of 0. The same goes for text files, where an exact comparison is file1.read() == file2.read(), but an approximate comparison is a Levenshtein distance comparison.

# configs: overall threshold, file-type specific threshold, use only exact match, file-type specific exact match, skip hidden or system files (best guess), disable comparisons for specific file types, match only based on extension not magic identification, comparators to disable, root paths to search down, blacklisted paths, etc.

# Have service to discover plugins and generate configs accordingly (such as being able to disable comparators)

class Singleton:
    __instance = None
    __lock = Lock()

    def __new__(cls, *args, **kwargs) -> Self:  # pylint: disable=unused-argument
        """Make this class (and its subclasses) singleton"""
        if cls.__instance is None:
            with cls.__lock:
                if not cls.__instance:
                    cls.__instance = super().__new__(cls)
        return cls.__instance


class classproperty:
    def __init__(self, function: Callable) -> None:
        self.__getter = function

    def __get__(self, _, owner) -> Any:
        return self.__getter(owner)


class IFileComparator(ABC):
    @classproperty
    @abstractmethod
    def file_types(cls) -> tuple[str, str]:
        """The file types supported by this comparator"""

    @classproperty
    @abstractmethod
    def exact(cls) -> bool:
        """Whether the comparison is exact or approximate"""

    @staticmethod
    @abstractmethod
    def compare(file1: Path, file2: Path) -> float: ...












from magic import from_buffer, from_file, MagicException
from typing import Generator

# class FileComparator:
#     def __init__(self, file_types: tuple[str], files: list[Path] | None = None) -> None:
#         self._file_types = file_types
#         self._files = [] if not files else files
#         self._comparables: dict[str, Callable] = {}

#     @property
#     def comparables(self) -> dict[str, Callable]:
#         """The file types which can be compared to"""
#         return self._comparables

#     @property
#     def files(self) -> list[Path]:
#         """The paths to files whose types are supported by this comparator"""
#         return self._files

#     @property
#     def file_types(self) -> tuple[str, ...]:
#         """The file types supported by this comparator"""
#         return self._file_types

#     def __repr__(self) -> str:
#         return f"FileComparator(\n\tfile_types={self.file_types},\n\tcomparables={self.comparables},\n\tfiles={self.files})"


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

from threading import Thread, Event
from time import time

def run(kill: Event, files) -> None:
    root = Path(r"C:\Users\caiparker")
    for file in walk(root):
        if kill.is_set():
            break
        file_type = file.suffix
        if file_type not in files:
            files[file_type] = []
        files[file_type].append(file)
        try:
            file_type = from_file(str(file), mime=True)
        except MagicException:
            try:
                file_type = from_buffer(file.open().read(4096), mime=True)
            except Exception:
                continue
        except PermissionError:
            continue
        if file_type not in files:
            files[file_type] = []
        files[file_type].append(file)
        print(file)

files: dict[str, list[Path]] = {}
event = Event()
t = Thread(target=run, args=(event, files))
t0 = time()
t.start()
input("Press enter to stop")
event.set()
t.join()
print((time() - t0)/60, "minutes")
print("\n".join([f"{k}: {len(v)}" for k, v in files.items()]))

# def diff1(file1: Path, file2: Path, threshold: float = 0) -> float:
#     print("diff1")
#     return 0.0

# def diff2(file1: Path, file2: Path, threshold: float = 0) -> float:
#     print("diff2")
#     return 0.0

# def diff3(file1: Path, file2: Path, threshold: float = 0) -> float:
#     print("diff3")
#     return 0.0

# def diff4(file1: Path, file2: Path, threshold: float = 0) -> float:
#     print("diff4")
#     return 0.0

# registers = [
#     ('text/plain', 'text/plain', diff1),
#     ('text/plain', 'application/x-dosexec', diff2),
#     ('image/png', 'image/png', diff3),
#     ('text/x-msdos-batch', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', diff4)
# ]

# file_comparators: list[FileComparator] = []

# for file_type1, file_type2, comparison in registers:
#     for comparator in file_comparators:
#         if file_type1 in comparator.file_types:
#             comparator.comparables[file_type2] = comparison
#             break
#     else:
#         file_comparators.append(FileComparator(file_types=(file_type1,), files=[]))
#         file_comparators[-1].comparables[file_type2] = comparison

# root = Path(r"C:\Users\caiparker\Documents")
# for file in walk(root):
#     file_type = from_file(str(file), mime=True)
#     for comparator in file_comparators:
#         if file_type in comparator.file_types:
#             comparator.files.append(file)
#             break
#     else:
#         file_comparators.append(FileComparator(file_types=(file_type,), files=[file]))


# for comparator in file_comparators:
#     print(comparator)
#     print()


# for source in file_comparators:
#     for dest in file_comparators:
#         for comp_types in dest.comparables.keys():
#             if comp_types not in source.file_types:
#                 continue
#             for file in source.files:
#                 for file2 in dest.files:
#                     if file == file2:
#                         continue
#                     print(from_file(str(file), mime=True), from_file(str(file2), mime=True), end=' ')
#                     dest.comparables[comp_types](file, file2)
#                     print(file, file2)
#                     print()