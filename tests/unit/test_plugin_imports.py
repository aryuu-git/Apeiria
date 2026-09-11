"""Guard: plugin sources only import symbols the domain packages export.

The plugin package is not type-checked (it depends on the AstrBot runtime),
so a wrong ``from anime_party import X`` previously shipped and crashed the
plugin at load time. This test parses the plugin sources and verifies every
domain import resolves against the package ``__all__``.
"""

import ast
from pathlib import Path

import anime_party
import apeiria_core

PLUGIN_DIR = Path(__file__).parents[2] / "packages" / "astrbot-plugin-apeiria"
_DOMAIN_PACKAGES = {"anime_party": anime_party, "apeiria_core": apeiria_core}


def _assert_imports_resolve(source: str) -> None:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _DOMAIN_PACKAGES:
            package = _DOMAIN_PACKAGES[node.module]
            exported = set(getattr(package, "__all__", []))
            missing = [alias.name for alias in node.names if alias.name not in exported]
            assert not missing, f"{node.module} does not export: {missing}"


def test_plugin_sources_import_only_exported_symbols() -> None:
    for source_file in PLUGIN_DIR.glob("*.py"):
        _assert_imports_resolve(source_file.read_text(encoding="utf-8"))
