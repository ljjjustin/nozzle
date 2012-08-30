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

from nozzle.client.v1_0 import ListCommand
from nozzle.client.v1_0 import ShowCommand


class ListLoadBalancer(ListCommand):

    def get_data(self, parsed_args):
        cols = ('ID', 'Name')
        data = ('123', 'test')
        return (cols, (data,))


class ShowLoadBalancer(ShowCommand):

    def get_data(self, parsed_args):
        cols = ('ID', 'Name', 'Detail')
        data = ('123', 'test', 'details')
        return (cols, data)
