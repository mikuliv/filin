# Third-party dependency notices

The repository does not assign a project license. Before any distribution,
generate an inventory for the exact release environment and review every
dependency licence and image notice. The current development inventory can be
recorded with `python tools/runtime_environment_report.py`; Python packages
should additionally be captured with `python -m pip freeze` in the release
environment. Docker image digests must be recorded only after they are
actually resolved; this repository does not invent digests.
