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

"""nozzle api."""
from nozzle import db
from nozzle.common import exception
from nozzle.common import utils
from nozzle import protocol
from nozzle import state


def create_load_balancer(context, **kwargs):
    try:
        module = protocol.get_protocol_module(kwargs['protocol'])
        module_func = getattr(module, 'create_load_balancer')
    except Exception, exp:
        raise exception.CreateLoadBalancerFailed(msg=str(exp))
    return module_func(context, **kwargs)


def delete_load_balancer(context, **kwargs):
    try:
        module = protocol.get_protocol_module(kwargs['protocol'])
        module_func = getattr(module, 'delete_load_balancer')
    except Exception, exp:
        raise exception.DeleteLoadBalancerFailed(msg=str(exp))
    return module_func(context, **kwargs)


def update_load_balancer_config(context, **kwargs):
    try:
        module = protocol.get_protocol_module(kwargs['protocol'])
        module_func = getattr(module, 'update_load_balancer_config')
    except Exception, exp:
        raise exception.UpdateLoadBalancerFailed(msg=str(exp))
    return module_func(context, **kwargs)


def update_load_balancer_instances(context, **kwargs):
    try:
        module = protocol.get_protocol_module(kwargs['protocol'])
        module_func = getattr(module, 'update_load_balancer_instances')
    except Exception, exp:
        raise exception.UpdateLoadBalancerFailed(msg=str(exp))
    return module_func(context, **kwargs)


def update_load_balancer_http_servers(context, **kwargs):
    try:
        module = protocol.get_protocol_module(kwargs['protocol'])
        module_func = getattr(module, 'update_load_balancer_http_servers')
    except Exception, exp:
        raise exception.UpdateLoadBalancerFailed(msg=str(exp))
    return module_func(context, **kwargs)


def get_load_balancer(context, **kwargs):
    expect_keys = [
        'tenant_id', 'uuid',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    result = None
    uuid = kwargs['uuid']
    try:
        load_balancer_ref = db.load_balancer_get_by_uuid(context, uuid)
        result = format_msg_to_client(load_balancer_ref)
    except Exception, exp:
        raise exception.GetLoadBalancerFailed(msg=str(exp))

    return {'data': result}


def get_all_load_balancers(context, **kwargs):
    expect_keys = [
        'user_id', 'tenant_id',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    result = []
    try:
        filters = {'project_id': kwargs['tenant_id']}
        context = context.elevated(read_deleted='no')
        all_load_balancers = db.load_balancer_get_all(context, filters=filters)
        for load_balancer_ref in all_load_balancers:
            result.append(format_msg_to_client(load_balancer_ref))
    except Exception, exp:
        raise exception.GetAllLoadBalancerFailed(msg=str(exp))

    return {'data': result}


def get_all_http_servers(context, **kwargs):
    expect_keys = [
        'user_id', 'tenant_id',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    result = None
    try:
        context = context.elevated(read_deleted='no')
        all_domains = db.load_balancer_domain_get_all(context)
        result = map(lambda x: x['name'], all_domains)
    except Exception, exp:
        raise exception.GetAllHttpServersFailed(msg=str(exp))

    return {'data': result}


def get_msg_to_worker(context, method, **kwargs):
    result = dict()
    message = dict()
    load_balancer_ref = None
    if method == 'delete_load_balancer':
        result['cmd'] = 'delete_lb'
        message['user_id'] = kwargs['user_id']
        message['tenant_id'] = kwargs['tenant_id']
        message['uuid'] = kwargs['uuid']
        message['protocol'] = kwargs['protocol']
    elif method == 'create_load_balancer':
        result['cmd'] = 'create_lb'
        load_balancer_ref = db.load_balancer_get_by_name(context,
                kwargs['name'])
        message = format_msg_to_worker(load_balancer_ref)
    elif method.startswith('update_load_balancer'):
        result['cmd'] = 'update_lb'
        load_balancer_ref = db.load_balancer_get_by_uuid(context,
                kwargs['uuid'])
        message = format_msg_to_worker(load_balancer_ref)
    else:
        return None
    result['msg'] = message
    return result


def delete_load_balancer_hard(context, load_balancer_ref):
    try:
        for association_ref in load_balancer_ref.instances:
            db.load_balancer_instance_association_destroy(context,
                    load_balancer_ref.id, association_ref.instance_uuid)

        for domain_ref in load_balancer_ref.domains:
            db.load_balancer_domain_destroy(context, domain_ref.id)

        db.load_balancer_config_destroy(context, load_balancer_ref.config.id)
        db.load_balancer_destroy(context, load_balancer_ref.id)
    except Exception, exp:
        raise exception.DeleteLoadBalancerFailed(msg=str(exp))


def update_load_balancer_state(context, **kwargs):
    code = kwargs['code']
    uuid = kwargs['uuid']
    try:
        load_balancer_ref = db.load_balancer_get_by_uuid(context, uuid)
    except Exception, exp:
        raise exception.DeleteLoadBalancerFailed(msg=str(exp))

    if code == 200:
        if load_balancer_ref.state == state.DELETING:
            delete_load_balancer_hard(context, load_balancer_ref)
        elif load_balancer_ref.state in [state.CREATING, state.UPDATING]:
            db.load_balancer_update_state(context, uuid, state.ACTIVE)
        else:
            db.load_balancer_update_state(context, uuid, state.ERROR)
    elif code == 500:
        if load_balancer_ref.state != state.DELETING:
            db.load_balancer_update_state(context, uuid, state.ERROR)


def format_msg_to_worker(load_balancer_ref):
    result = dict()
    expect_keys = [
        'uuid', 'name', 'protocol', 'instance_port',
        'free', 'listen_port', 'state',
    ]
    for key in expect_keys:
        result[key] = getattr(load_balancer_ref, key)
    expect_configs = [
        'balancing_method',
        'health_check_timeout_ms',
        'health_check_interval_ms',
        'health_check_target_path',
        'health_check_healthy_threshold',
        'health_check_unhealthy_threshold',
    ]
    config = dict()
    for key in expect_configs:
        config[key] = getattr(load_balancer_ref.config, key)

    instance_uuids = map(lambda x: x['instance_uuid'],
                         load_balancer_ref.instances)
    http_server_names = map(lambda x: x['name'],
                         load_balancer_ref.domains)
    dns_names = []
    protocol = load_balancer_ref.protocol
    prefix = load_balancer_ref.dns_prefix
    postfixs = []
    if protocol == 'http':
        postfixs = FLAGS.http_postfixs
    elif protocol == 'tcp':
        postfixs = FLAGS.tcp_postfixs
    for postfix in postfixs:
        dns_name = '%s%s' % (prefix, postfix)
        dns_names.append(dns_name)

    result['config'] = config
    result['dns_names'] = dns_names
    result['instance_uuids'] = instance_uuids
    result['http_server_names'] = http_server_names
    return result


def format_msg_to_client(load_balancer_ref):
    result = dict()
    result['user_id'] = load_balancer_ref.user_id
    result['tenant_id'] = load_balancer_ref.project_id
    result['uuid'] = load_balancer_ref.uuid
    result['protocol'] = load_balancer_ref.protocol
    expect_keys = [
        'dns_prefix', 'instance_port', 'listen_port',
    ]
    for key in expect_keys:
        result[key] = getattr(load_balancer_ref, key)
    expect_configs = [
        'balancing_method',
        'health_check_timeout_ms',
        'health_check_interval_ms',
        'health_check_target_path',
        'health_check_healthy_threshold',
        'health_check_unhealthy_threshold',
    ]
    for key in expect_configs:
        result[key] = getattr(load_balancer_ref.config, key)

    instance_uuids = map(lambda x: x['instance_uuid'],
                         load_balancer_ref.instances)
    http_server_names = map(lambda x: x['name'],
                         load_balancer_ref.domains)
    dns_names = []
    protocol = load_balancer_ref.protocol
    prefix = load_balancer_ref.dns_prefix
    postfixs = []
    if protocol == 'http':
        postfixs = FLAGS.http_postfixs
    elif protocol == 'tcp':
        postfixs = FLAGS.tcp_postfixs
    for postfix in postfixs:
        dns_name = '%s%s' % (prefix, postfix)
        dns_names.append(dns_name)
    instance_ips = []
    for uuid in instance_uuids:
        instance_ips.append(utils.get_fixed_ip_by_instance_uuid(uuid))

    result['dns_names'] = dns_names
    result['instance_ips'] = instance_ips
    result['instance_uuids'] = instance_uuids
    result['http_server_names'] = http_server_names
    return result
