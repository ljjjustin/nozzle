# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Ustack Corporation
# All Rights Reserved.
# Author: Jiajun Liu <iamljj@gmail.com>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Get all supported protocol."""

import os

from nozzle.openstack.common import importutils


PROTOCOLS = []


def get_all_protocols():
    global PROTOCOLS

    search_dir = __path__[0]
    for dirpath, dirnames, filenames in os.walk(search_dir):
        relpath = os.path.relpath(dirpath, search_dir)
    if relpath == '.':
        relpkg = ''
    else:
        relpkg = '.%s' % '.'.join(relpath.split(os.sep))
    for fname in filenames:
        root, ext = os.path.splitext(fname)
        if ext != '.py' or root == '__init__':
            continue
        module_name = "%s%s.%s" % (__package__, relpkg, root)
        module = importutils.import_module(module_name)
        PROTOCOLS.append(module)

    return PROTOCOLS


def get_protocol_module(name):

    for module in PROTOCOLS:
        if name == module.__name__.split('.')[-1]:
            return module
    raise Exception('unsupported protocol: %s' % name)


if not PROTOCOLS:
    get_all_protocols()
