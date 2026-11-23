# P01-23.1 · the catalogue release-string validator

**Date:** 2026-11-23. **Subtask:** P01-23. **Affects:** nothing measured;
this note records an implementation, not a result.

## What was built

`scripts/validate_catalogue.py` implements the acceptance gate for
P01-23. The deviation register (D002, issue #27) states that because the
released image carries InterProScan **5.59-91.0** rather than the
pre-registered 5.70-102.0, the catalogue must record the InterProScan
data release beside every domain hit. The data release is what a domain
hit means, so the rule is enforced mechanically, ahead of the P01-13
sweep that will produce the catalogue:

- The catalogue is a TSV with a header row; one column is dedicated to
  the release and is named exactly `interproscan_release`. The name is
  fixed in the validator, once, so producers and validator cannot drift.
- Every data row must carry a non-empty value in that column, and the
  value must equal the released image's release string exactly.
- The expected string is read from the environment manifest
  (`docs/released-manifest.txt`), from the line on which
  `interproscan.sh` reports its own version — never typed by hand, per
  the issue. Zero or several such lines in a manifest is a manifest
  error, not something to guess around.

Exit status follows the repository's checker convention: 0 valid, 1 any
row fails (every failing line is reported), 2 for unreadable or malformed
inputs.

## Validation

`tests/test_validate_catalogue.py`, 12 tests. Both failure modes named in
the P01-23 acceptance criteria are pinned with fixture catalogues: a row
without the release fails, and a row whose release does not match the
manifest fails (the fixture uses 5.70-102.0 — the pre-registered string —
which is exactly the defect D002 warns about). A further test parses the
real `docs/released-manifest.txt` and asserts it yields `5.59-91.0`, so
the validator and the released image cannot silently part company. The
full repository suite passes (236 passed; the 5 pre-existing failures
require a git checkout, and the verification environment had a tarball).

## What is deliberately not done

- **The catalogue does not exist yet.** P01-13 (the Pfam/InterProScan
  sweep) produces it; this validator is its gate, not its output.
- **Header propagation is the producer's job.** P01-23 also asks that
  the GFF/GTF and protein FASTA carry the same string in their headers
  or accompanying metadata; that is enforced at catalogue build time and
  is noted here so the sweep's author sees it. Extending this validator
  to check those headers is a natural follow-up once their formats are
  fixed by the sweep.
