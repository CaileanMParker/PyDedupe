from imagehash import average_hash
from PIL import Image

from .base_classes import classproperty, File, IFileComparator


class ImageComparator(IFileComparator):
    """A file comparator for image files"""

    _file_types = (
        ".jpeg", ".jpg", ".png",
        ".gif", ".tiff", ".raw",
        ".bmp", ".webp", ".svg"
    )

    @classproperty
    def file_types(cls) -> tuple[str, ...]:  # pylint: disable=no-self-argument
        return cls._file_types

    @staticmethod
    def compare(
        file1: File,
        file2: File,
        threshold: float = 0.0
    ) -> bool:
        with Image.open(file1.path) as image1, Image.open(file2.path) as image2:
            diff = average_hash(image1) - average_hash(image2)
        return diff <= threshold


def exact_compare(file1: File, file2: File) -> bool:
    """Compare two files and return whether they match exactly

    Parameters
    ----------
    file1: The first file to compare
    file2: The second file to compare

    Returns
    -------
    Whether the files match exactly
    """
    return file1.path.read_bytes() == file2.path.read_bytes()