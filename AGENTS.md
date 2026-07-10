# Repository Instructions

## GitHub synchronization

- Before using repository state for a task, synchronize with `origin/main`.
- After completing any repository change, review the staged diff, create a
  descriptive commit, and push it to `origin/main`.
- Before reporting project status, verify that the current `main` commit is
  present on `origin/main`.
- Do not force-push, overwrite remote history, or add ignored raw datasets,
  processed arrays, virtual environments, checkpoints, or training runs.

## Algorithm integrity

Avoid degradation handling, fallback, hacks, heuristics, local stabilizations,
or post-processing bandages that are not faithful general algorithms.
