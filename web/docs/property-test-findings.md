# Comparison property-test findings

## 2026-10-24

The first invariant test found that current-mode membership did not explicitly include a feature referenced by a `modified` feature's `replaces` list unless that older feature was also marked `existing` or `removed`. The membership builder now includes every feature replaced by a modified feature, matching invariant 4.

The task plan also makes task 7.4 depend on task 7.6's tests while task 7.6 depends on task 7.4. They were validated together so neither check was skipped.
