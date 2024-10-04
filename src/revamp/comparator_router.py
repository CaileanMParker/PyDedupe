from typing import Callable

from pdd_defaultcomparators.base_classes import classproperty, IFileComparator


class ComparatorRouter:
    __routing_map: dict[str, dict[str, list[Callable]]] = {}

    @classproperty
    def routing_map(cls) -> dict[str, dict[str, list[Callable]]]:  # pylint: disable=no-self-argument
        return cls.__routing_map

    @classmethod
    def register_comparator(cls, comparator: IFileComparator) -> None:
        for file_type in comparator.file_types:
            if file_type not in cls.__routing_map:
                cls.__routing_map[file_type] = {}
            for file_type2 in comparator.file_types:
                # if file_type == file_type2:
                #     continue
                if file_type2 not in cls.__routing_map[file_type]:
                    cls.__routing_map[file_type][file_type2] = []
                cls.__routing_map[file_type][file_type2].append(
                    comparator.compare
                )

    @classmethod
    def route(cls, file_type1: str, file_type2: str) -> list[Callable]:
        return cls.__routing_map.get(file_type1, {}).get(file_type2, [])