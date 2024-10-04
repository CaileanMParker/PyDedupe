from abc import ABC, abstractmethod
from collections.abc import Callable
from multiprocessing import Lock
from pathlib import Path
from typing import Any, NamedTuple, Self


# Settled: discovery process will maintain master dict of file types and their corresponding file paths
# Settled: comparators will be small static classes

# Either needs to be registered against the "factory", so instead of just registering the class, the registration could entail passing in the other metadata...

# Necessary comparison metadata: 1. 2x file types, 2. comparison type (diff or equal), 3. comparison function, 4. threshold (if applicable)

# It **IS** necessary to differentiate between exact and approximate comparisons. For example, an exact picture hash is file1.read() == file2.read(), but an approximate picture hash is a perceptual hash comparison, which can "match" even slightly different files on a threshold of 0. The same goes for text files, where an exact comparison is file1.read() == file2.read(), but an approximate comparison is a Levenshtein distance comparison.

# Could exact match or same-file-type classes be allowed to specify multiple file types to avoid redundancy?

# configs: overall threshold, file-type specific threshold, use only exact match, file-type specific exact match, skip hidden or system files (best guess), disable comparisons for specific file types, match only based on extension not magic identification, comparators to disable, root paths to search down, blacklisted paths, how to handle comparison consensus (i.e., if multiple comparators handle the same comparison set, which should run, and how many must return true to believe it?), where to house temp display directory, etc.

# Have service to discover plugins and generate configs accordingly (such as being able to disable comparators)


File = NamedTuple("File", [("path", Path), ("type", str)])


class Singleton:
    """A process-safe metaclass for singleton objects"""
    __instance = None
    __lock = Lock()

    def __new__(cls, *args, **kwargs) -> Self:  # pylint: disable=unused-argument
        """Create new instance only if one does not already exist, otherwise
        return existing instance
        """
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
    """Interface for simple a file comparator

    Abstract Class Properties
    -------------------------
    file_types: A tuple of strings representing the types of files this
    class can compare

    Abstract Methods
    ----------------
    compare: Compare two files and return whether they match
    """

    @classmethod
    def __repr__(cls) -> str:
        return f"{cls.__name__}(file_types={cls.file_types})"

    @classproperty
    @abstractmethod
    def file_types(cls) -> tuple[str, ...]:  # pylint: disable=no-self-argument
        """A tuple of strings representing the types of files this class can
        compare
        """

    @staticmethod
    @abstractmethod
    def compare(
        file1: File,
        file2: File,
        threshold: float = 0.0
    ) -> bool:
        """Compare two files and return whether they match

        Parameters
        ----------
        file1: A File object containing the path to and filetype of the first
            file to compare
        file2: A File object containing the path to and filetype of the second
            file to compare
        threshold: The threshold to determine the files a match, if comparison
            is approximate

        Returns
        -------
        Whether the files match
        """
