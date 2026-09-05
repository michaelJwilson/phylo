# docs/nb/

One notebook per problem class, each a single pass from a seeded fixture to a
learned search policy, checking every claim against an oracle that shares no
code with what it checks.

| Notebook | Problem | Oracles it rests on |
| --- | --- | --- |
| [`potts_chain.ipynb`](potts_chain.ipynb) | Potts chain in an external field | Exhaustive enumeration of the partition function; enumeration of all 81 configurations |
| [`phylo_tree.ipynb`](phylo_tree.ipynb) | Phylogenetic trees, 6 taxa | Brute-force marginalization over ancestral states; all 105 unrooted topologies enumerated |
| [`hmm.ipynb`](hmm.ipynb) | Discrete hidden Markov model | Enumeration over all `3**8` hidden paths; the retained hidden path; Baum-Welch as an independent algorithm |

Each ends with a **Further Work** section naming what it could not demonstrate
and the issue that carries it. Those sections are the point as much as the
results are: a notebook that quietly skipped the unbuilt half would misreport
the state of the repository.

## Running them

The notebooks import `phylo` and read fixtures from
`tests/regression/fixtures/`, resolving the repository root from wherever they
are opened. Install the package first (`INSTALL.md`), then open them with any
Jupyter front end.

Jupyter is **not** a dependency of this repository and no continuous
integration job re-executes these notebooks, so they are committed with the
outputs they were written against and their numbers date from that commit.
That is weaker than the contract `docs/tex/` figures hold, where CI
regenerates every figure and fails a pull request whose rebuilt PDF differs
from the committed one. Adding the dependency and the job would close the gap
and needs the sign-off root `CLAUDE.md` requires before a dependency lands.

## Keeping them true

A change to `phylo.sim`, `phylo.opt`, `phylo.likelihood`, `phylo.search` or
`phylo.learn` that alters a number these notebooks print must re-run them in
the same pull request, exactly as it must regenerate a `docs/tex/` figure.
Nothing here may state a result the regression suite does not also pin.
