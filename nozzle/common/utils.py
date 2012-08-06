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
#
# vim: tabstop=4 shiftwidth=4 softtabstop=4

import inspect
import os
import sys
import uuid

from paste import deploy

from nozzle.openstack.common import cfg
from nozzle.openstack.common import timeutils


def default_cfgfile(filename='nozzle.conf', args=None):
    if args is None:
        args = sys.argv
    for arg in args:
        if arg.find('config-file') != -1:
            return arg[arg.index('config-file') + len('config-file') + 1:]
    else:
        if not os.path.isabs(filename):
            # turn relative filename into an absolute path
            script_dir = os.path.dirname(inspect.stack()[-1][1])
            filename = os.path.abspath(os.path.join(script_dir, filename))
        if not os.path.exists(filename):
            filename = "./nozzle.conf"
            if not os.path.exists(filename):
                filename = '/etc/nozzle/nozzle.conf'
        if os.path.exists(filename):
            cfgfile = '--config-file=%s' % filename
            args.insert(1, cfgfile)
            return filename


def load_paste_app(app_name):
    """
    Builds and returns a WSGI app from a paste config file.

    :param app_name: Name of the application to load
    :raises RuntimeError when config file cannot be located or
            application cannot be loaded from config file
    """

    config_file = cfg.CONF.find_file(cfg.CONF.api_paste_config)
    config_path = os.path.abspath(config_file)
    ##LOG.info("Config paste file: %s", config_path)

    try:
        app = deploy.loadapp("config:%s" % config_path, name=app_name)
    except (LookupError, ImportError):
        msg = ("Unable to load %(app_name)s from "
               "configuration file %(config_path)s.") % locals()
        ##LOG.exception(msg)
        raise RuntimeError(msg)
    return app


def str_uuid():
    return str(uuid.uuid4())


def utcnow():
    return timeutils.utcnow()
