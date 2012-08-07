# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 Sina Corporation
# All Rights Reserved.
# Author: Justin Ljj <iamljj@gmail.com>
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

import sys

from nozzle.openstack.common import wsgi

from nozzle.common import flags
from nozzle.common import log as logging
from nozzle.common import utils

LOG = logging.getLogger(__name__)


def main():
    utils.default_cfgfile()
    flags.FLAGS(sys.argv)
    logging.setup('nozzle')

    LOG.debug("*" * 80)
    LOG.debug("Configuration options gathered from config file:")
    LOG.debug("================================================")
    items = dict([(k, v) for k, v in flags.FLAGS.items()
                  if k not in ('__file__', 'here')])
    for key, value in sorted(items.items()):
        LOG.debug("%(key)-30s %(value)s" % {'key': key,
                                            'value': value})
    LOG.debug("*" * 80)

    app = utils.load_paste_app("nozzle")
    server = wsgi.Server()
    server.start(app, 5557)
    server.wait()
