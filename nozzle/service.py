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

from nozzle.openstack.common import importutils
from nozzle.openstack.common import wsgi

from nozzle.common import flags
from nozzle.common import utils


class Service(object):
    """Service object for binaries running on this hosts."""

    def __init__(self, host):
        self.host = host
        self.timers = []
        self.manager = self._get_manager()

    def _get_manager(self):
        """Initialize a manager class for this service."""
        manager_name = flags.FLAGS.manager_name
        manager_class = importutils.import_class(manager_name)
        return manager_class()

    def start(self):
        self.manager.init_host()

    def stop(self):
        self.timers = []

    def wait(self):
        pass


class WSGIService(object):
    """Provides ablitity to launch API from a 'paste' configuration."""

    def __init__(self, name, loader=None):
        """Initialize, but do not start the WSGI server."""
        self.name = name
        self.app = utils.load_paste_app(name)
        ##self.manager = self._get_manager()
        self.server = wsgi.Server()

    def _get_manager(self):
        """Initialize a manager class for this service."""
        manager_name = flags.FLAGS.server_manager
        manager_class = importutils.import_class(manager_name)
        return manager_class()

    def start(self):
        """Start serving this service using loaded configuration."""
        ##if self.manager:
        ##    self.manager.init_host()
        utils.show_configs()
        self.server.start(self.app,
                          flags.FLAGS.api_listen_port,
                          flags.FLAGS.api_listen)

    def stop(self):
        """Stop serving this API."""
        self.server.stop()

    def wait(self):
        """Wait for the service to stop serving this API."""
        self.server.wait()
