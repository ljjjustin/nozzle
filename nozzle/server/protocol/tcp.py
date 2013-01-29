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

"""TCP protocol handler."""
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
        'health_check_healthy_threshold',
        'health_check_unhealthy_threshold',
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
    if not 1 <= config['health_check_healthy_threshold'] <= 10:
        raise exception.InvalidParameter(
            msg='Healthy check healthy threshold out of rage, 1~10')
    if not 1 <= config['health_check_unhealthy_threshold'] <= 10:
        raise exception.InvalidParameter(
            msg='Healthy check unhealthy threshold out of rage, 1~10')

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
        raise exception.CreateLoadBalancerFailed(msg='already exists!')

    # create load balancer
    config_ref = None
    load_balancer_ref = None
    associated_instances = []

    try:
        load_balancer_values = {
            'name': kwargs['name'],
            'user_id': kwargs['user_id'],
            'project_id': kwargs['tenant_id'],
            'uuid': utils.str_uuid(),
            'free': kwargs['free'],
            'protocol': kwargs['protocol'],
            'state': state.CREATING,
            'dns_prefix': utils.gen_dns_prefix(),
            'listen_port': utils.allocate_listen_port(),
            'instance_port': kwargs['instance_port'],
        }
        load_balancer_ref = db.load_balancer_create(context,
                                                    load_balancer_values)

        config_values = {
            'load_balancer_id': load_balancer_ref.id,
            'balancing_method': config['balancing_method'],
            'health_check_timeout_ms': config['health_check_timeout_ms'],
            'health_check_interval_ms': config['health_check_interval_ms'],
            'health_check_target_path': '',
            'health_check_healthy_threshold':
            config['health_check_healthy_threshold'],
            'health_check_unhealthy_threshold':
            config['health_check_unhealthy_threshold'],
        }
        config_ref = db.load_balancer_config_create(context, config_values)
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

    expect_configs = [
        'balancing_method',
        'health_check_timeout_ms',
        'health_check_interval_ms',
        'health_check_healthy_threshold',
        'health_check_unhealthy_threshold',
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
    if not 1 <= config['health_check_healthy_threshold'] <= 10:
        raise exception.InvalidParameter(
            msg='Healthy check healthy threshold out of rage, 1~10')
    if not 1 <= config['health_check_unhealthy_threshold'] <= 10:
        raise exception.InvalidParameter(
            msg='Healthy check unhealthy threshold out of rage, 1~10')

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
        'health_check_target_path': '',
        'health_check_healthy_threshold':
        config['health_check_healthy_threshold'],
        'health_check_unhealthy_threshold':
        config['health_check_unhealthy_threshold'],
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
    return None
