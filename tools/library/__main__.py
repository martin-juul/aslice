"""Compatibility CLI; implementation lives with the library."""

from . import _backend

main = _backend("__main__").main

if __name__ == "__main__":
    main()
