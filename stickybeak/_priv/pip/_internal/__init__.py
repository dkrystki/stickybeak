import stickybeak._priv.pip._internal.utils.inject_securetransport  # noqa
from stickybeak._priv.pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Optional, List


def main(args=None):
    # type: (Optional[List[str]]) -> int
    """This is preserved for old console scripts that may still be referencing
    it.

    For additional details, see https://github.com/pypa/pip/issues/7498.
    """
    from stickybeak._priv.pip._internal.utils.entrypoints import _wrapper

    return _wrapper(args)
