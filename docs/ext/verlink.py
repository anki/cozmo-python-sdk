# Copyright (c) 2016 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Generate versioned links for example files.

This extension adds a new role to generate links to the correct version
of files referenced by the documentation.

It substitutes the string "0.0.0" with a version number defined by the
"verlink_version" configuration value.

Roles can optionally include text to use for the link, else it defaults
to the supplied filename.  the URL is prefixed with the
"verlink_base_url" value to make a complete URL.

For example, if verlink_base_url="http://example.com/files/0.0.0/"
and verlink_version="1.2.3" then

:verlink:`examples-0.0.0.zip` will display "examples-1.2.3.zip" and link
to http:/example.com/files/1.2.3/examples-1.2.3.zip

:verlink:`Examples for 0.0.0 <examples-0.0.0.zip>` will display
"Examples for 1.2.3" and link to http:/example.com/files/1.2.3/examples-1.2.3.zip
'''


from docutils import nodes, utils

import sphinx
from sphinx.util.nodes import split_explicit_title


def replace_version(app, str):
    try:
        ver = app.config.verlink_version
    except AttributeError as err:
        raise ValueError("verlink_version configuration value is not set")
    return str.replace('0.0.0', ver)


def verlink_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    app = inliner.document.settings.env.app
    try:
        base_url = app.config.verlink_base_url
    except AttributeError as err:
        raise ValueError("verlink_base_url configuration value is not set")

    text = utils.unescape(text)
    has_explicit_title, title, fn = split_explicit_title(text)
    full_url = replace_version(app, base_url + fn)
    if not has_explicit_title:
        title = fn
    title = replace_version(app, title)
    pnode = nodes.reference(title, title, internal=False, refuri=full_url)
    return [pnode], []


def setup(app):
    app.add_role('verlink', verlink_role)
    app.add_config_value('verlink_base_url', None, {})
    app.add_config_value('verlink_version', None, {})
