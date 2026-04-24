from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

_src_service_path = Path(__file__).resolve().parent.parent / "src" / "service"
if _src_service_path.is_dir():
    _resolved = str(_src_service_path)
    if _resolved not in __path__:
        __path__.append(_resolved)
