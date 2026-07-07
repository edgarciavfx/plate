"""Compatibility alias for the ``plate`` package.

The PyPI distribution is named ``plateprep``, but the importable package is
``plate`` (see README, ``from plate.pipeline import PlatePipeline``). This
shim exists so ``import plateprep`` also works for users who reasonably
expect the import name to match the distribution name.
"""

from plate import __version__

__all__ = ["__version__"]
