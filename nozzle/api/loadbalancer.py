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

import logging

import zmq

from nozzle.openstack.common import wsgi

from nozzle.api import base

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
        msg_id = str(uuid.uuid4())
        self.handler.send_multipart(msg_type, msg_id, json.dumps(msg_body))
        return self.handler.recv_multipart()


class Controller(base.Controller):

    def __init__(self):
        self.client = ZmqClient()
        super(Controller, self).__init__()

    def index(self, req):
        print "<<< %r" % req
        return dict({"loadbalancers": 'index'})

    def detail(self, req):
        return dict({"loadbalancers": 'detail'})

    def create(self, req, body=None):
        return dict({"loadbalancer": { "id": "create" }})

    def show(self, req, id):
        return dict({"loadbalancer": { "id": "show" }})

    def update(self, req, id, body=None):
        return dict({"loadbalancer": { "id": "update" }})

    def delete(self, req, id):
        return dict({"loadbalancer": { "id": "delete" }})


def create_resource():
    controller = Controller()
    return wsgi.Resource(controller)
