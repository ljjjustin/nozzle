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

import webob.exc
import logging
import zmq

from nozzle.openstack.common import jsonutils
from nozzle.openstack.common import wsgi

from nozzle.api import base
from nozzle.common import utils

class ZmqClient(object):

    def __init__(self, host='127.0.0.1', port=5557):
        url = "tcp://%s:%s" % (host, port)
        context = zmq.Context()
        self.handler = context.socket(zmq.REQ)
        self.handler.connect(url)

    def __del__(self):
        self.handler.close()

    def call(self, msg_body):
        msg_type = "lb"
        msg_id = utils.str_uuid()
        self.handler.send_multipart([msg_type, msg_id,
                                     jsonutils.dumps(msg_body)])
        msg_type, msg_id, msg_body = self.handler.recv_multipart()
        return jsonutils.loads(msg_body)


class Controller(base.Controller):

    def __init__(self):
        self.client = ZmqClient()
        super(Controller, self).__init__()

    def index(self, req):
        context = req.environ['nozzle.context']
        zmq_args = {
            'method': 'get_all_load_balancers',
            'args': {
                'user_id': context.user_id,
                'tenant_id': context.tenant_id,
            },
        }
        result = self.client.call(zmq_args)
        if result['code'] != 200:
            return webob.exc.HTTPError(result['message'])
        else:
            return dict({"loadbalancers": result['data']})

    def detail(self, req):
        return self.index(req)

    def create(self, req, body=None):
        context = req.environ['nozzle.context']
        zmq_args = {
            'method': 'create_load_balancer',
            'args': {
                'user_id': context.user_id,
                'tenant_id': context.tenant_id,
            },
        }
        loadbalancer = body['loadbalancer']
        zmq_args['args'].update(loadbalancer)
        result = self.client.call(zmq_args)
        if result['code'] != 200:
            return webob.exc.HTTPError(result['message'])
        else:
            return dict({"loadbalancer": result['data']})

    def show(self, req, id):
        context = req.environ['nozzle.context']
        zmq_args = {
            'method': 'get_load_balancer',
            'args': {
                'user_id': context.user_id,
                'tenant_id': context.tenant_id,
                'uuid': id,
            },
        }
        result = self.client.call(zmq_args)
        if result['code'] != 200:
            return webob.exc.HTTPError(result['message'])
        else:
            return dict({"loadbalancer": result['data']})

    def update(self, req, id, body=None):
        context = req.environ['nozzle.context']
        zmq_args = {
            'method': 'update_load_balancer',
            'args': {
                'user_id': context.user_id,
                'tenant_id': context.tenant_id,
                'uuid': id,
            },
        }
        loadbalancer = body['loadbalancer']
        zmq_args['args'].update(loadbalancer)
        result = self.client.call(zmq_args)
        if result['code'] != 200:
            return webob.exc.HTTPError(result['message'])
        else:
            return dict({"message": "successful"})

    def delete(self, req, id):
        context = req.environ['nozzle.context']
        zmq_args = {
            'method': 'delete_load_balancer',
            'args': {
                'user_id': context.user_id,
                'tenant_id': context.tenant_id,
                'uuid': id,
            },
        }
        result = self.client.call(zmq_args)
        if result['code'] != 200:
            return webob.exc.HTTPError(result['message'])
        else:
            return dict({"message": "successful"})


def create_resource():
    controller = Controller()
    return wsgi.Resource(controller)
