# Code Style Guide

The code should generally follow [PEP8](https://www.python.org/dev/peps/pep-0008/)

Code documentation should be written using Google style, which can be extracted
using Sphinx:
* http://google.github.io/styleguide/pyguide.html
* http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html


Main style points to consider:

## Line Length

PEP8 recommends a maximum line length of 80 characters.  While some lines
are easier to read if they're a bit longer than that, generally try to stay
within the 80 character limit.

Parameter lists can be wrapped and long strings can be split by enclosing them
in parentheses:

````python
long_string = ('First long line...'
    'Second long line')
````

or by using triple quotes.

## White Space

Indentation should be made using 4 space characters.

* Two blank lines between class definitions and top-level functions
* One blank line between methods (generally)

Follow [PEP8 guidelines](https://www.python.org/dev/peps/pep-0008/#whitespace-in-expressions-and-statements)
for whitespace in expressions and statements.

## Imports

Import statements should be arranged in three blocks at the head of the file
(though after the module documentation).  Each block of imports should be in
alphabetical order.

1. The first block should be Python-provided packages (eg. `sys`)
2. The second block should be third-party packages (eg. `numpy`)
3. The final block should be local packages and module (eg. `from . import camera`)

````python
import os
import sys

import numpy

from . import camera
from . import event
````

Wildcard imports (`from module import *`) should not be used outside of tests.

Additionally it is generally useful to avoid importing variables from modules
directly into the local namespace (`from module import some_object`) - Doing
so means you now have two references to to the same thing, which impedes
mocking during unit tests.

Better instead to import the module and reference a qualified name (`import module`
and `module.some_object`).

## Names

* Module level constants should be in CAPS
* Class names should be CamelCase
* Variables, attributes, functions, methods and properties should be lowercase_with_underscores
* Variables, attributes, functions, methods and properties can be named with a
leading underscore to indicate that they're "private"

## Documentation

See http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html
for documentation examples.

* Module-level documentation should appear first in the file, before imports
* All public-facing classes, functions, methods etc should be documented
* The first line of a docstring should contain the summary of what the item does.
This should be followed by a blank line and the extended description, if any.
* Use Sphinx-friendly markup (per the Google guide above) so that cross-references
work automatically and examples are formatted correctly.

### Documenting properties and attributes

For class and object attributes, use the `#:` comment syntax rather than a
trailing docstring.  Instance attributes can be documented in the `__init__`
constructor.

Properties should use a docstring like any other method, but should be
written in the same style as an attribute, as that's how they'll be presented
in Sphinx (ie. as `return_type: description`).

Properties with setters must have the docstring on the getter rather than
the setter.


```python
class MyClass:
    '''One line summary of class.

    Docstring for constructor should appear in the class description

    Args:
        default_timeout (int): Default number of seconds for operations to
            wait for timeout.
    '''
    #: string: Description of a class-level attribute.  The description
    #: may span multiple lines as long as they all begin with #:
    class_level_attr = ''

    def __init__(self, default_timeout=None):
        #: int: The default number of seconds for operations to wait for timeout.
        self.default_timeout = default_timeout

    @property
    def timeout_enabled(self):
        '''bool: True if a value for :attr:`default_timeout` has been set.'''
        return self.default_timeout is not None
```


## Exceptions

Wherever practical, catch explicit exception classes rather than using
a bare try/except statement (or matching `Exception`).

To re-raise the original exception use `raise` by itself or
`raise MyException() from exc`
(rather than `raise exc`) to maintain the original stack trace.
