from pathlib import Path
# from threading import Thread, Event
# from time import time
# from typing import Any, Generator

# from magic import from_buffer, from_file, MagicException

from file_comparators import ImageComparator, exact_compare  # type: ignore[import-not-found]


# def walk(root: Path) -> Generator[Path, Any, None]:
#     try:
#         for path in root.iterdir():
#             if path.is_dir():
#                 if path.name.startswith('.') or path.name in ("AppData", "pygame-ce", "bin") or path.is_symlink():
#                     continue
#                 yield from walk(path)
#                 continue
#             yield path
#     except PermissionError:
#         pass


# def run(kill: Event, files: dict[str, list[Path]]) -> None:
#     root = Path(r"C:\Users\caiparker")
#     for file in walk(root):
#         if kill.is_set():
#             break
#         file_type = file.suffix
#         if file_type not in files:
#             files[file_type] = []
#         files[file_type].append(file)
#         try:
#             file_type = from_file(str(file), mime=True)
#         except MagicException:
#             try:
#                 file_type = from_buffer(file.open().read(4096), mime=True)
#             except Exception:
#                 continue
#         except PermissionError:
#             continue
#         if file_type not in files:
#             files[file_type] = []
#         files[file_type].append(file)
#         print(file)


# files_dict: dict[str, list[Path]] = {}
# event = Event()
# t = Thread(target=run, args=(event, files_dict))
# t0 = time()
# t.start()
# input("Press enter to stop")
# event.set()
# t.join()
# print((time() - t0)/60, "minutes")
# print("\n".join([f"{k}: {len(v)}" for k, v in files_dict.items()]))

# root = Path(r"D:\duplicate_file_cleaner\src\revamp\filecomparators")
root = Path(r"C:\Users\caiparker.REDMOND\Downloads")
f1 = root / "20170716_150905.jpg"
f2 = root / "20170716_150907.jpg"
f3 = root / "20170707_180137.jpg"

print(exact_compare(f1, f1))
print(exact_compare(f1, f2))
print(exact_compare(f1, f3))
print(exact_compare(f2, f3))
print()
print(ImageComparator.compare(f1, f1))
print(ImageComparator.compare(f1, f2))
print(ImageComparator.compare(f1, f3))
print(ImageComparator.compare(f2, f3))
print()
print(ImageComparator.compare(f1, f1, 5))
print(ImageComparator.compare(f1, f2, 5))
print(ImageComparator.compare(f1, f3, 5))
print(ImageComparator.compare(f2, f3, 5))
