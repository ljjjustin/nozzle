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

from nozzle.client.v2_0 import ListCommand
from nozzle.client.v2_0 import ShowCommand
from nozzle.client.v2_0 import CreateCommand
from nozzle.client.v2_0 import DeleteCommand
from nozzle.client.v2_0 import UpdateCommand


class ListLoadBalancer(ListCommand):

    resource = 'loadbalancer'

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--all_tenants', metavar='show-all-tenants',
            help=_('The name of the load balancer to be created'))


class ShowLoadBalancer(ShowCommand):

    resource = 'loadbalancer'


class CreateLoadBalancer(CreateCommand):

    resource = 'loadbalancer'

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--name', metavar='name',
            help=_('The name of the load balancer to be created'))
        parser.add_argument(
            '--protocol', metavar='protocol',
            help=_('What protocol to use for this load balancer'))
        parser.add_argument(
            '--instances', metavar='instance_uuids',
            help=_('instances uuids to be added to this load balancer'))
        parser.add_argument(
            '--port', metavar='instance_port',
            help=_("traffics forwarded to which port of instance"))
        parser.add_argument(
            '--domains', metavar='domains',
            help=_("public dns binding to the load balancer to be created, "
                   "do not need to set if protocol is not 'http'"))

    def make_request_body(self, parsed_args):
        if not parsed_args.name:
            raise Exception("Specify a unique name for this loadbalancer")

        if parsed_args.protocol not in ['http', 'tcp']:
            raise Exception("Only 'http' and 'tcp' are supported now!")

        instance_uuids = []
        if not parsed_args.instances:
            raise Exception("Please specify one or more instance uuids")
        else:
            instance_uuids = parsed_args.instances.split(',')
            instance_uuids = filter(lambda x: x, instance_uuids)
        if len(instance_uuids) < 1:
            raise Exception("Please specify one or more instance uuids")

        instance_port = 0
        if not parsed_args.port:
            raise Exception("instance_port should between 1~65535")
        else:
            instance_port = int(parsed_args.port)
        if not 1 <= instance_port <= 65535:
            raise Exception("instance_port should between 1~65535")

        load_balancer_domains = []
        if parsed_args.protocol == 'http':
            if not parsed_args.domains:
                raise Exception("Please specify one or more domains")
            load_balancer_domains = parsed_args.domains.split(',')
            load_balancer_domains = filter(lambda x: x, load_balancer_domains)
            if len(load_balancer_domains) < 1:
                raise Exception("Please specify one or more domains")

        load_balancer_config = {
            'balancing_method': 'round_robin',
            'health_check_timeout_ms': 50000,
            'health_check_interval_ms': 15000,
            'health_check_target_path': '/',
            'health_check_healthy_threshold': 5,
            'health_check_unhealthy_threshold': 2,
        }

        request_body = {
            'loadbalancer': {
                'config': load_balancer_config,
                'name': parsed_args.name,
                'protocol': parsed_args.protocol,
                'instance_port': instance_port,
                'instance_uuids': instance_uuids,
                'http_server_names': load_balancer_domains,
            }
        }
        return request_body


class DeleteLoadBalancer(DeleteCommand):

    resource = 'loadbalancer'


class UpdateLoadBalancer(UpdateCommand):

    resource = 'loadbalancer'

    def add_known_arguments(self, parser):
        parser.add_argument(
            '--instances', metavar='instance_uuids',
            help=_('instances uuids to be added to this load balancer'))
        parser.add_argument(
            '--domains', metavar='domains',
            help=_("public dns binding to the load balancer to be created, "
                   "do not need to set if protocol is not 'http'"))

    def make_request_body(self, parsed_args):
        load_balancer_values = {}

        instance_uuids = []
        if parsed_args.instances:
            instance_uuids = parsed_args.instances.split(',')
            instance_uuids = filter(lambda x: x, instance_uuids)
        if len(instance_uuids) >= 1:
            load_balancer_values['instance_uuids'] = instance_uuids

        load_balancer_domains = []
        if parsed_args.domains:
            load_balancer_domains = parsed_args.domains.split(',')
            load_balancer_domains = filter(lambda x: x, load_balancer_domains)
        if len(load_balancer_domains) >= 1:
            load_balancer_values['http_server_names'] = load_balancer_domains

        return {'loadbalancer': load_balancer_values}
