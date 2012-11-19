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

import zmq

from nozzle.openstack.common import jsonutils
from nozzle.openstack.common import log as logging
from nozzle.openstack.common import wsgi

from nozzle.common import flags
from nozzle.common import utils

FLAGS = flags.FLAGS
LOG = logging.getLogger(__name__)


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


class Controller(object):

    def __init__(self):
        self.client = ZmqClient(host=FLAGS.server_listen,
                                port=FLAGS.server_listen_port)
        super(Controller, self).__init__()

    def index(self, req):
        LOG.info(req.environ['nozzle.context'])
        context = req.environ['nozzle.context']
        zmq_args = {
            'method': 'get_all_load_balancers',
            'args': {
                'user_id': context.user_id,
                'tenant_id': context.tenant_id,
                'is_admin': context.is_admin,
                'all_tenants': False,
            },
        }
        zmq_args['args'].update(req.GET)
        LOG.debug(zmq_args)
        result = self.client.call(zmq_args)
        return result

    def detail(self, req):
        return self.index(req)

    def domains(self, req):
        LOG.info(req.environ['nozzle.context'])
        context = req.environ['nozzle.context']
        zmq_args = {
            'method': 'get_all_http_servers',
            'args': {
                'user_id': context.user_id,
                'tenant_id': context.tenant_id,
            },
        }
        LOG.debug(zmq_args)
        result = self.client.call(zmq_args)
        return result

    def create(self, req, body=None):
        LOG.info(req.environ['nozzle.context'])
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
        LOG.debug(zmq_args)
        result = self.client.call(zmq_args)
        return result

    def show(self, req, id):
        LOG.info(req.environ['nozzle.context'])
        context = req.environ['nozzle.context']
        zmq_args = {
            'method': 'get_load_balancer',
            'args': {
                'user_id': context.user_id,
                'tenant_id': context.tenant_id,
                'uuid': id,
            },
        }
        LOG.debug(zmq_args)
        result = self.client.call(zmq_args)
        return result

    def update(self, req, id, body=None):
        LOG.info(req.environ['nozzle.context'])
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
        LOG.debug(zmq_args)
        result = self.client.call(zmq_args)
        return result

    def delete(self, req, id):
        LOG.info(req.environ['nozzle.context'])
        context = req.environ['nozzle.context']
        zmq_args = {
            'method': 'delete_load_balancer',
            'args': {
                'user_id': context.user_id,
                'tenant_id': context.tenant_id,
                'uuid': id,
            },
        }
        LOG.debug(zmq_args)
        result = self.client.call(zmq_args)
        return result

    def get_by_instance_uuid(self, req, id):
        LOG.info(req.environ['nozzle.context'])
        context = req.environ['nozzle.context']
        zmq_args = {
            'method': 'get_load_balancer_by_instance_uuid',
            'args': {
                'user_id': context.user_id,
                'tenant_id': context.tenant_id,
                'instance_uuid': id,
            },
        }
        LOG.debug(zmq_args)
        result = self.client.call(zmq_args)
        return result


def create_resource():
    controller = Controller()
    return wsgi.Resource(controller)
