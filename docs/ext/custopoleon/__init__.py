'''
Due to deficiencies in the design of Sphinx, two modules cannot both
observe the same event.  Napaleon hooks the autodoc-skip-member event
to determine which memembers to show.. We want to use the same thing
to special case the AnimTriggers and BehaviorTypes classes so that
their undocumented memebers show up in the docs.

As a workaround this module monkey patches Napoleon to wrap their
autodoc-skip-member implementation and special case the response for
our classes.
'''


import sphinx.ext.napoleon


_org_skip_member = sphinx.ext.napoleon._skip_member

def _skip_member(app, what, name, obj, skip, options):
    clsname = obj.__class__.__name__
    if clsname in ('_AnimTrigger', '_BehaviorType'):
        return False
    return _org_skip_member(app, what, name, obj, skip, options)

sphinx.ext.napoleon._skip_member = _skip_member

def setup(app):
    return sphinx.ext.napoleon.setup(app)

