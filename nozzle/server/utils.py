# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

"""Help functions."""
import sqlalchemy
import random
import uuid

from novaclient.v1_1 import client

from shunt.context import get_admin_context
from shunt import db
from shunt import exception
from shunt import flags


FLAGS = flags.FLAGS
nova_client = None


def allocate_listen_port():
    filters = dict({'protocol': 'tcp'})
    context = get_admin_context(read_deleted="yes")
    all_lbs = db.load_balancer_get_all(context, filters=filters)

    active_load_balancers = filter(lambda x: not x['deleted'], all_lbs)
    deleted_load_balancers = filter(lambda x: x['deleted'], all_lbs)
    allocated_ports = map(lambda x: x['listen_port'], active_load_balancers)
    available_ports = filter(lambda x: x not in allocated_ports,
            map(lambda y: y['listen_port'], deleted_load_balancers))

    if available_ports:
        return available_ports[0]
    elif allocated_ports:
        return max(allocated_ports) + 1
    else:
        return 11000


def check_input_parameters(expect_keys, **kwargs):
    for key in expect_keys:
        if not key in kwargs.keys():
            raise exception.MissingParameter(key=key)


def gen_dns_prefix():
    context = get_admin_context(read_deleted="yes")
    all_load_balancers = db.load_balancer_get_all(context)
    all_prefixs = map(lambda x: x['dns_prefix'], all_load_balancers)
    prefix = generate_uid(size=10)
    while prefix in all_prefixs:
        prefix = generate_uid(size=10)
    return prefix


def generate_uid(size=10):
    characters = '01234567890abcdefghijklmnopqrstuvwxyz'
    choices = [random.choice(characters) for _x in xrange(size)]
    return ''.join(choices)


def gen_uuid():
    return uuid.uuid4()


def get_all_domain_names():
    context = get_admin_context()
    all_domains = db.load_balancer_domain_get_all(context)
    all_http_servers = map(lambda x: x['name'], all_domains)
    return all_http_servers


def get_all_load_balancers(filters=None):
    context = get_admin_context()
    all_load_balancers = db.load_balancer_get_all(context, filters=filters)
    return all_load_balancers


def get_fixed_ip_by_instance_uuid(uuid):
    global nova_client
    if nova_client is None:
        nova_client = client.Client(FLAGS.keystone_username,
                                    FLAGS.keystone_password,
                                    FLAGS.keystone_tenant_name,
                                    FLAGS.keystone_auth_url,
                                    service_type="compute")
    instance = nova_client.servers.get(uuid)
    for ip_group, addresses in instance.addresses.items():
        for address in addresses:
            return address['addr']
    raise Exception('failed to ip address of instance: %s' % uuid)
