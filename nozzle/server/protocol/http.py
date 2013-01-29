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

"""HTTP protocol handler."""
from nozzle import db
from nozzle.common import exception
from nozzle.common import utils
from nozzle.server import state


def create_load_balancer(context, **kwargs):
    expect_keys = [
        'user_id', 'tenant_id', 'protocol', 'name',
        'instance_port', 'instance_uuids', 'config',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    expect_configs = [
        'balancing_method',
        'health_check_timeout_ms',
        'health_check_interval_ms',
        'health_check_target_path',
    ]
    config = kwargs['config']
    utils.check_input_parameters(expect_configs, **config)

    if not 1 <= kwargs['instance_port'] <= 65535:
        raise exception.InvalidParameter(
            msg='invalid instance port, should between 1~65535')
    if config['balancing_method'] not in ['round_robin', 'source_binding']:
        raise exception.InvalidParameter(
            msg='invalid balancing method, round_robin or source_binding')
    if not 100 <= config['health_check_timeout_ms']:
        raise exception.InvalidParameter(
            msg='healthy check timeout out of range, 100ms~120s')
    if not 100 <= config['health_check_interval_ms']:
        raise exception.InvalidParameter(
            msg='Healthy check interval out of rage, 100ms~10m')
    if not config['health_check_target_path']:
        raise exception.InvalidParameter(
            msg='health check path could not be null')

    try:
        free = kwargs['free']
    except KeyError:
        kwargs['free'] = False
    except Exception, e:
        raise exception.CreateLoadBalancerFailed(msg='unknown error!')

    # check if load balancer already exists
    try:
        db.load_balancer_get_by_name(context, kwargs['name'])
    except exception.LoadBalancerNotFoundByName:
        pass
    except Exception, exp:
        raise exception.CreateLoadBalancerFailed(msg=str(exp))
    else:
        raise exception.CreateLoadBalancerFailed(msg='already exist!')

    # check if any domain to be created already exists
    all_domain_names = utils.get_all_domain_names()
    for name in kwargs['http_server_names']:
        if name in all_domain_names:
            exp = exception.LoadBalancerDomainExists(domain_name=name)
            raise exception.CreateLoadBalancerFailed(msg=str(exp))

    # create load balancer
    config_ref = None
    load_balancer_ref = None
    inserted_domains = []
    associated_instances = []

    try:
        load_balancer_values = {
            'name': kwargs['name'],
            'user_id': kwargs['user_id'],
            'project_id': kwargs['tenant_id'],
            'uuid': utils.str_uuid(),
            'free': kwargs['free'],
            'state': state.CREATING,
            'protocol': kwargs['protocol'],
            'dns_prefix': utils.gen_dns_prefix(),
            'listen_port': 80,
            'instance_port': kwargs['instance_port'],
        }
        load_balancer_ref = db.load_balancer_create(context,
                                                    load_balancer_values)

        config_values = {
            'load_balancer_id': load_balancer_ref.id,
            'balancing_method': config['balancing_method'],
            'health_check_timeout_ms': config['health_check_timeout_ms'],
            'health_check_interval_ms': config['health_check_interval_ms'],
            'health_check_target_path': config['health_check_target_path'],
            'health_check_healthy_threshold': 0,
            'health_check_unhealthy_threshold': 0,
        }
        config_ref = db.load_balancer_config_create(context, config_values)
        # binding domains
        for domain in kwargs['http_server_names']:
            domain_values = {
                'load_balancer_id': load_balancer_ref.id,
                'name': domain,
            }
            domain_ref = db.load_balancer_domain_create(context, domain_values)
            inserted_domains.append(domain_ref.id)
        # binding instances
        for uuid in kwargs['instance_uuids']:
            association = {
                'load_balancer_id': load_balancer_ref.id,
                'instance_uuid': uuid,
            }
            db.load_balancer_instance_association_create(context, association)
            associated_instances.append(uuid)
    except Exception, exp:
        if load_balancer_ref:
            for instance_uuid in associated_instances:
                db.load_balancer_instance_association_destroy(
                    context, load_balancer_ref.id, instance_uuid)
        for domain_id in inserted_domains:
            db.load_balancer_domain_destroy(context, domain_id)
        if config_ref:
            db.load_balancer_config_destroy(context, config_ref.id)
        if load_balancer_ref:
            db.load_balancer_destroy(context, load_balancer_ref.id)
        raise exception.CreateLoadBalancerFailed(msg=str(exp))

    return {'data': {'uuid': load_balancer_ref.uuid}}


def update_load_balancer_config(context, **kwargs):
    expect_keys = [
        'user_id', 'tenant_id', 'protocol',
        'uuid', 'config',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    config = kwargs['config']
    expect_configs = [
        'balancing_method',
        'health_check_timeout_ms',
        'health_check_interval_ms',
        'health_check_target_path',
    ]
    config = kwargs['config']
    utils.check_input_parameters(expect_configs, **config)

    if config['balancing_method'] not in ['round_robin', 'source_binding']:
        raise exception.InvalidParameter(
            msg='invalid balancing method, round_robin or source_binding')
    if not 100 <= config['health_check_timeout_ms']:
        raise exception.InvalidParameter(
            msg='healthy check timeout out of range, 100ms~120s')
    if not 100 <= config['health_check_interval_ms']:
        raise exception.InvalidParameter(
            msg='Healthy check interval out of rage, 100ms~10m')
    if not config['health_check_target_path']:
        raise exception.InvalidParameter(
            msg='health check path could not be null')

    uuid = kwargs['uuid']
    try:
        load_balancer_ref = db.load_balancer_get_by_uuid(context, uuid)
    except Exception, exp:
        raise exception.UpdateLoadBalancerFailed(msg=str(exp))

    config_values = {
        'load_balancer_id': load_balancer_ref.id,
        'balancing_method': config['balancing_method'],
        'health_check_timeout_ms': config['health_check_timeout_ms'],
        'health_check_interval_ms': config['health_check_interval_ms'],
        'health_check_target_path': config['health_check_target_path'],
        'health_check_healthy_threshold': 0,
        'health_check_unhealthy_threshold': 0,
    }
    try:
        db.load_balancer_config_destroy(context, load_balancer_ref.config.id)
        db.load_balancer_config_create(context, config_values)
        db.load_balancer_update_state(context, uuid, state.UPDATING)
    except Exception, exp:
        raise exception.UpdateLoadBalancerFailed(msg=str(exp))

    return None


def update_load_balancer_instances(context, **kwargs):
    expect_keys = [
        'user_id', 'tenant_id', 'protocol',
        'uuid', 'instance_uuids',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    new_instance_uuids = kwargs['instance_uuids']
    if not new_instance_uuids:
        raise exception.InvalidParameter(
            msg='instance_uuids can not be null')

    uuid = kwargs['uuid']
    try:
        load_balancer_ref = db.load_balancer_get_by_uuid(context, uuid)
    except Exception, exp:
        raise exception.UpdateLoadBalancerFailed(msg=str(exp))

    old_instance_uuids = map(lambda x: x['instance_uuid'],
                             load_balancer_ref.instances)
    need_deleted_instances = filter(lambda x: x not in new_instance_uuids,
                                    old_instance_uuids)
    need_created_instances = filter(lambda x: x not in old_instance_uuids,
                                    new_instance_uuids)
    try:
        for instance_uuid in need_deleted_instances:
            db.load_balancer_instance_association_destroy(
                context, load_balancer_ref.id, instance_uuid)
        for instance_uuid in need_created_instances:
            association = {
                'load_balancer_id': load_balancer_ref.id,
                'instance_uuid': instance_uuid,
            }
            db.load_balancer_instance_association_create(context, association)
        db.load_balancer_update_state(context, uuid, state.UPDATING)
    except Exception, exp:
        raise exception.UpdateLoadBalancerFailed(msg=str(exp))

    return None


def update_load_balancer_http_servers(context, **kwargs):
    expect_keys = [
        'user_id', 'tenant_id', 'protocol',
        'uuid', 'http_server_names',
    ]
    utils.check_input_parameters(expect_keys, **kwargs)

    uuid = kwargs['uuid']
    try:
        load_balancer_ref = db.load_balancer_get_by_uuid(context, uuid)
    except Exception, exp:
        raise exception.UpdateLoadBalancerFailed(msg=str(exp))

    new_http_servers = kwargs['http_server_names']
    old_http_servers = map(lambda x: x['name'], load_balancer_ref.domains)
    need_deleted_domains = filter(lambda x: x not in new_http_servers,
                                  old_http_servers)
    need_created_domains = filter(lambda x: x not in old_http_servers,
                                  new_http_servers)

    # check if any domain to be created already exists
    all_domain_names = utils.get_all_domain_names()
    for name in need_created_domains:
        if name in all_domain_names:
            exp = exception.LoadBalancerDomainExists(domain_name=name)
            raise UpdateLoadBalancerFailed(msg=str(exp))

    try:
        for domain in load_balancer_ref.domains:
            if domain.name in need_deleted_domains:
                db.load_balancer_domain_destroy(context, domain.id)

        for domain in need_created_domains:
            domain_values = {
                'load_balancer_id': load_balancer_ref.id,
                'name': domain,
            }
            db.load_balancer_domain_create(context, domain_values)
        db.load_balancer_update_state(context, uuid, state.UPDATING)
    except Exception, exp:
        raise exception.UpdateLoadBalancerFailed(msg=str(exp))

    return None
