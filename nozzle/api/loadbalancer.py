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

from nozzle.openstack.common import wsgi

from nozzle.api import base

class Controller(base.Controller):

    def __init__(self):
        super(Controller, self).__init__()

    def index(self, request):
        return dict({"loadbalancers": []})

    def detail(self, request):
        return dict({"loadbalancers": 'detail'})

    def create(self, request, body=None):
        return dict({"loadbalancer": { "id": "create" }})

    def show(self, request, id):
        return dict({"loadbalancer": { "id": "show" }})

    def update(self, request, id, body=None):
        return dict({"loadbalancer": { "id": "update" }})

    def delete(self, request, id):
        return dict({"loadbalancer": { "id": "delete" }})


def create_resource():
    controller = Controller()
    return wsgi.Resource(controller)
