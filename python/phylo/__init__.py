"""Top-level package. Re-exports only phylo's own utilities, not submodule contents — import `sim`, `likelihood`, `opt`, and `search` explicitly (e.g. `from phylo.likelihood import ...`)."""

from .oxiphylo import double

__all__ = ["double"]
