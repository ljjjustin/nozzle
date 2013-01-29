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

"""nozzle api."""
from nozzle import db
from nozzle.common import exception
from nozzle.common import flags
from nozzle.common import utils
from nozzle.server import protocol
from nozzle.server import state
from nozzle.openstack.common.notifier import api as notifier
from nozzle.openstack.common import log as logging

FLAGS = flags.FLAGS
LOG = logging.getLogger(__name__)


def format_msg_to_client(load_balancer_ref):
    result = dict()
    expect_keys = [
        'uuid', 'name', 'protocol', 'instance_port',
        'free', 'listen_port', 'state',
        'created_at', 'updated_at',
        'user_id', 'project_id',
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


def format_msg_to_worker(load_balancer_ref):
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
    result['args'] = message
    return result


def notify(context, load_balancer_ref, event):
    if not FLAGS.notification_enabled:
        return

    payload = {
        'tenant_id': load_balancer_ref.project_id,
        'uuid': load_balancer_ref.uuid,
        'name': load_balancer_ref.name,
        'free': load_balancer_ref.free,
    }
    notifier.notify(context, 'loadbalancer', event, notifier.INFO, payload)


def create_load_balancer(context, **kwargs):
    try:
        module = protocol.get_protocol_module(kwargs['protocol'])
        module_func = getattr(module, 'create_load_balancer')
        result = module_func(context, **kwargs)
        uuid = result['data']['uuid']
        load_balancer_ref = db.load_balancer_get_by_uuid(context, uuid)
        notify(context, load_balancer_ref, 'loadbalancer.create.start')
        result = format_msg_to_client(load_balancer_ref)
    except Exception, exp:
        raise exception.CreateLoadBalancerFailed(msg=str(exp))

    return {'data': result}


def create_for_instance(context, **kwargs):
    expect_keys = [
        'user_id', 'tenant_id', 'instance_uuid', 'instance_port',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    instance_uuid = kwargs['instance_uuid']
    instance_port = kwargs['instance_port']
    try:
        load_balancers = db.load_balancer_get_by_instance_uuid(context,
                                                               instance_uuid)
        for load_balancer_ref in load_balancers:
            if load_balancer_ref.free:
                break
        result = format_msg_to_client(load_balancer_ref)
    except exception.LoadBalancerNotFoundByInstanceUUID, exp:
        pass
    except Exception, exp:
        raise exception.CreateForInstanceFailed(msg=str(exp))

    try:
        load_balancer_name = 'login-' + instance_uuid
        load_balancer_config = {
            'balancing_method': 'round_robin',
            'health_check_timeout_ms': 50000,
            'health_check_interval_ms': 15000,
            'health_check_target_path': '/',
            'health_check_healthy_threshold': 5,
            'health_check_unhealthy_threshold': 2,
        }
        load_balancer_values = {
            'tenant_id': kwargs['tenant_id'],
            'user_id': kwargs['user_id'],
            'free': True,
            'protocol': 'tcp',
            'name': load_balancer_name,
            'config': load_balancer_config,
            'instance_port': instance_port,
            'instance_uuids': [instance_uuid],
            'http_server_names': [],
        }
        return create_load_balancer(context, **load_balancer_values)
    except Exception, exp:
        raise exception.CreateForInstanceFailed(msg=str(exp))
    return None


def delete_load_balancer(context, **kwargs):
    expect_keys = [
        'tenant_id', 'uuid',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    uuid = kwargs['uuid']
    try:
        load_balancer_ref = db.load_balancer_get_by_uuid(context, uuid)
        db.load_balancer_update_state(context, uuid, state.DELETING)
        notify(context, load_balancer_ref, 'loadbalancer.delete.start')
    except Exception, exp:
        raise exception.DeleteLoadBalancerFailed(msg=str(exp))

    return None


def delete_for_instance(context, **kwargs):
    expect_keys = [
        'tenant_id', 'instance_uuid',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    instance_uuid = kwargs['instance_uuid']
    try:
        load_balancers = db.load_balancer_get_by_instance_uuid(context,
                                                               instance_uuid)
        for load_balancer_ref in load_balancers:
            try:
                if load_balancer_ref.free:
                    args = {
                        'tenant_id': context.tenant_id,
                        'uuid': load_balancer_ref.uuid,
                    }
                    delete_load_balancer(context, **args)
                elif load_balancer_ref.state != state.DELETING:
                    old_instance_uuids = map(lambda x: x['instance_uuid'],
                                             load_balancer_ref.instances)
                    new_instance_uuids = filter(lambda x: x != instance_uuid,
                                                old_instance_uuids)
                    args = {
                        'tenant_id': context.tenant_id,
                        'user_id': context.user_id,
                        'protocol': load_balancer_ref.protocol,
                        'uuid': load_balancer_ref.uuid,
                        'instance_uuids': new_instance_uuids,
                    }
                    update_load_balancer_instances(context, **args)
            except Exception, exp:
                LOG.info('delete_for_instance: failed for %s', str(exp))
    except Exception, exp:
        raise exception.DeleteForInstanceFailed(msg=str(exp))
    return None


def update_load_balancer(context, **kwargs):
    expect_keys = [
        'tenant_id', 'uuid',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    uuid = kwargs['uuid']
    try:
        load_balancer_ref = db.load_balancer_get_by_uuid(context, uuid)
    except Exception, exp:
        raise exception.UpdateLoadBalancerFailed(msg=str(exp))

    kwargs.update({'protocol': load_balancer_ref.protocol})

    for key, value in kwargs.iteritems():
        if key == 'config':
            update_load_balancer_config(context, **kwargs)
        elif key == 'http_server_names':
            update_load_balancer_http_servers(context, **kwargs)
        elif key == 'instance_uuids':
            update_load_balancer_instances(context, **kwargs)
    notify(context, load_balancer_ref, 'loadbalancer.update.start')


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


def get_load_balancer_by_instance_uuid(context, **kwargs):
    expect_keys = [
        'tenant_id', 'instance_uuid',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)
    result = None
    uuid = kwargs['instance_uuid']
    try:
        load_balancer_ref = db.load_balancer_get_by_instance_uuid(context,
                                                                  uuid)
        result = format_msg_to_client(load_balancer_ref)
    except Exception, exp:
        raise exception.GetLoadBalancerFailed(msg=str(exp))

    return {'data': result}


def get_all_load_balancers(context, **kwargs):
    expect_keys = [
        'user_id', 'tenant_id', 'all_tenants',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    result = []
    try:
        all_tenants = int(kwargs['all_tenants'])
        if context.is_admin and all_tenants:
            filters = {}
        else:
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


def delete_load_balancer_hard(context, load_balancer_ref):
    try:
        for association_ref in load_balancer_ref.instances:
            db.load_balancer_instance_association_destroy(
                context, load_balancer_ref.id, association_ref.instance_uuid)

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
        raise exception.UpdateLoadBalancerFailed(msg=str(exp))

    if code == 200:
        if load_balancer_ref.state == state.DELETING:
            delete_load_balancer_hard(context, load_balancer_ref)
            notify(context, load_balancer_ref, 'loadbalancer.delete.end')
        elif load_balancer_ref.state == state.CREATING:
            db.load_balancer_update_state(context, uuid, state.ACTIVE)
            notify(context, load_balancer_ref, 'loadbalancer.create.end')
        elif load_balancer_ref.state == state.UPDATING:
            db.load_balancer_update_state(context, uuid, state.ACTIVE)
            notify(context, load_balancer_ref, 'loadbalancer.update.end')
    elif code == 500:
        if load_balancer_ref.state == state.CREATING:
            db.load_balancer_update_state(context, uuid, state.ERROR)
            notify(context, load_balancer_ref, 'loadbalancer.create.error')
        elif load_balancer_ref.state == state.UPDATING:
            db.load_balancer_update_state(context, uuid, state.ERROR)
            notify(context, load_balancer_ref, 'loadbalancer.update.error')
