from importlib import import_module
from inspect import isclass
from pkgutil import iter_modules, walk_packages
from types import ModuleType

from comparator_router import ComparatorRouter
from pdd_defaultcomparators.base_classes import IFileComparator


def __get_modules() -> list[ModuleType]:
    plugin_modules = [
        import_module(name)
        for _, name, ispkg
        in iter_modules()
        if name.startswith('pdd_') and not ispkg
    ]
    packages = [
        import_module(name)
        for _, name, ispkg
        in iter_modules()
        if name.startswith('pdd_') and ispkg
    ]
    for package in packages:
        plugin_modules.extend([
            import_module(name)
            for _, name, ispkg
            in walk_packages(package.__path__, f'{package.__name__}.')
            if not ispkg
        ])
    return plugin_modules


def get_plugins(modules: list[ModuleType]) -> list[IFileComparator]:
    plugins = []
    for module in modules:
        for _, cls in module.__dict__.items():
            if isclass(cls) and issubclass(cls, IFileComparator) \
                and cls != IFileComparator:
                plugins.append(cls)
    return plugins


def load_plugins() -> None:
    modules = __get_modules()
    plugins = get_plugins(modules)
    for plugin in plugins:
        ComparatorRouter.register_comparator(plugin)