











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