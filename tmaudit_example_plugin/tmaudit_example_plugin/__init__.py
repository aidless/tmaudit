"""tmaudit_example_plugin — three demo audit plugins.

This package exists as a working example for users who
want to write their own tmaudit plugins. It registers
three demo checks via the ``tmaudit.plugins`` entry-point
group:

1. ``flag-todo-markers`` — find ``TODO`` markers.
2. ``flag-xxx-markers`` — find ``XXX`` debug markers.
3. ``flag-long-abstract`` — flag abstracts > 300 words.

Install with::

    pip install -e ./tmaudit_example_plugin

Then ``tmaudit plugins list`` should show:

    NAME                  MODULE                          SEVERITY
    flag-long-abstract    tmaudit_example_plugin         MEDIUM
    flag-todo-markers     tmaudit_example_plugin         MEDIUM
    flag-xxx-markers      tmaudit_example_plugin         MEDIUM

The package is a sibling of ``tmaudit``; it depends on
``tmaudit >= 0.4.0`` to use the public API.
"""

__version__ = "0.1.0"
