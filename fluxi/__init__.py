"""Package for LabFluxi."""

import sys

__project__ = 'LabFluxi'
__version__ = '0.9.5dev'
__url__='https://github.com/fluxiresearch/fluxi'

VERSION = __project__ + '-' + __version__

PYTHON_VERSION = 3, 4

if not sys.version_info >= PYTHON_VERSION:  # pragma: no cover (manual test)
    exit("Python {}.{}+ is required.".format(*PYTHON_VERSION))

from fluxi.fluxi import Fluxi