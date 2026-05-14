"""Tự discover + đăng ký experience plugin.

Quét các package `expNN_*` trong thư mục này. Mỗi plugin export biến `EXPERIENCE`
là class implement `Experience` Protocol.

Phase 0: registry rỗng (chưa có plugin).
Phase 2: stub 3 plugin để registry discover được.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from neo_makervigate.experiences.experience_base import Experience


def discover_experiences() -> dict[str, type[Experience]]:
    """Quét các package `exp*` con và registry mỗi plugin theo `meta.id`."""
    from neo_makervigate import experiences as exp_pkg

    registry: dict[str, type[Experience]] = {}

    for pkg_info in pkgutil.iter_modules(exp_pkg.__path__):
        if not pkg_info.ispkg:
            continue
        if not pkg_info.name.startswith("exp"):
            continue

        try:
            module = importlib.import_module(f"neo_makervigate.experiences.{pkg_info.name}.logic")
            exp_class = getattr(module, "EXPERIENCE", None)
            if exp_class is None:
                logger.warning(f"Plugin {pkg_info.name} thiếu biến EXPERIENCE trong logic.py")
                continue
            registry[exp_class.meta.id] = exp_class
            logger.info(f"Registered plugin: {exp_class.meta.id}")
        except Exception as e:
            logger.error(f"Failed to load plugin {pkg_info.name}: {e}")

    return registry
