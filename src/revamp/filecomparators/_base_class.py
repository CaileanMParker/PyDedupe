from abc import ABC, abstractmethod
from collections.abc import Callable
from multiprocessing import Lock
from pathlib import Path
from typing import Self


# Should public methods be exposed which can route to the correct private method based on the file type?
# Or should the "comparables" property be dict point to the appropriate methods for each file type?
# And if the latter, should there be any public methods at all, or just private ones referenced by the comparables dict?

# should "diff" comparison methods return a float representing the difference between the two files?
# or should they accept a threshold as an argument and return a boolean indicating whether the files within that range?

# Do I even do classes at all, or just functions that register what two file types they can compare, whether it's a diff or equal comparison, and the actual comparison function?
# In this scenario, the discovery process would maintain a master list of files (categorized by type), then iterate through them running applicable comparisons.

# Necessary comparison metadata: 1. 2x file types, 2. comparison type (diff or equal), 3. comparison function, 4. threshold (if applicable)

# Should individual file types be allowed to specify comparison type or threshold?
# Should comparisons all be "diff" type but a threshold of 0 means "equal"?


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


class IFileComparator(ABC, Singleton):
    @property
    @abstractmethod
    def files(self) -> list[Path]:
        """The paths to files whose types are supported by this comparator"""

    @property
    @abstractmethod
    def file_types(self) -> tuple[str, ...]:
        """The file types supported by this comparator"""

    @property
    @abstractmethod
    def comparables(self) -> dict[str, tuple[Callable, Callable]]:
        """A dictionary providing which methods are applicable to which file types"""

    @abstractmethod
    def diff(self, file1: Path, file2: Path) -> float: ...

    @abstractmethod
    def equal(self, file1: Path, file2: Path) -> bool: ...





class Test(IFileComparator):
    def __init__(self, x) -> None:
        self.x = x
        print('init')

    @property
    def files(self) -> list[Path]:
        return []

    @property
    def file_types(self) -> tuple[str, ...]:
        return ('.txt',)

    @property
    def comparables(self) -> dict[str, tuple[Callable, Callable]]:
        return {
            '.txt': (self.diff, self.equal)
        }

    def diff(self, file1: Path, file2: Path) -> float:
        return 0.0

    def equal(self, file1: Path, file2: Path) -> bool:
        return True


a = Test(1)
print(a.x)
b = Test(2)
print(a.x)
print(b.x)
print(a is b)
print(type(a))
print(isinstance(a, Test))
print(isinstance(a, IFileComparator))
print(isinstance(a, Singleton))