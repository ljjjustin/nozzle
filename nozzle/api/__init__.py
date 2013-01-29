# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import routes
import webob.dec
import webob.exc

from nozzle.openstack.common import wsgi
from nozzle.openstack.common import log as logging

from nozzle.api import loadbalancer


LOG = logging.getLogger(__name__)


class FaultWrapper(wsgi.Middleware):

    @classmethod
    def factory(cls, global_config, **local_config):
        def _factory(app):
            return cls(app, **local_config)
        return _factory

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        try:
            return req.get_response(self.application)
        except Exception as ex:
            ## handle exception
            return str(ex)


class APIRouter(wsgi.Router):
    """
    Base class for nozzle API routes.
    """

    @classmethod
    def factory(cls, global_config, **local_config):
        return cls()

    def __init__(self):
        mapper = routes.Mapper()
        self._setup_basic_routes(mapper)
        super(APIRouter, self).__init__(mapper)

    def _setup_basic_routes(self, mapper):
        lb_resource = loadbalancer.create_resource()

        mapper.connect('/loadbalancers', controller=lb_resource,
                       action='index', conditions=dict(method=['GET']))
        mapper.connect('/loadbalancers/detail', controller=lb_resource,
                       action='detail', conditions=dict(method=['GET']))
        mapper.connect('/loadbalancers/domains', controller=lb_resource,
                       action='domains', conditions=dict(method=['GET']))
        mapper.connect('/loadbalancers', controller=lb_resource,
                       action='create', conditions=dict(method=['POST']))
        mapper.connect('/loadbalancers/{id}', controller=lb_resource,
                       action='show', conditions=dict(method=['GET']))
        mapper.connect('/loadbalancers/{id}', controller=lb_resource,
                       action='update', conditions=dict(method=['PUT']))
        mapper.connect('/loadbalancers/{id}', controller=lb_resource,
                       action='delete', conditions=dict(method=['DELETE']))
        mapper.connect('/loadbalancers/create_for_instance',
                       controller=lb_resource,
                       action='create_for_instance',
                       conditions=dict(method=['POST']))
        mapper.connect('/loadbalancers/delete_for_instance/{id}',
                       controller=lb_resource,
                       action='delete_for_instance',
                       conditions=dict(method=['DELETE']))


class APIRouterV10(APIRouter):
    """
    API routes mapping for nozzle API v1.0
    """
    _version = '1.0'


class APIRouterV20(APIRouter):
    """
    API routes mapping for nozzle API v2.0
    """
    _version = '2.0'
