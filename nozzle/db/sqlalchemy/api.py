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

"""Implementation of SQLAlchemy backend."""

from nozzle.common import exceptions
from nozzle.db.sqlalchemy import models


##def is_admin_context(context):
##    """Indicates if the request context is an administrator."""
##    if not context:
##        raise Exception('Empty request context')
##    return context.is_admin
##
##
##def is_user_context(context):
##    """Indicates if the request context is a normal user."""
##    if not context:
##        return False
##    if context.is_admin:
##        return False
##    if not context.user_id or not context.tenant_id:
##        return False
##    return True


##def require_admin_context(f):
##    """Decorator to require admin request context.
##    The first argument to the wrapped function must be the context.
##    """
##    def wrapper(*args, **kwargs):
##        if not is_admin_context(args[0]):
##            raise exceptions.AdminRequired()
##        return f(*args, **kwargs)
##    return wrapper


def model_query(context, model, **kwargs):
    """Query helper that accounts for context's `read_deleted` field.

    :param context: context to query under
    :param read_deleted: if present, overrides context's read_deleted field.
    """
    query = context.session.query(model)

    read_deleted = kwargs.get('read_deleted') or context.read_deleted
    if read_deleted == 'no':
        query = query.filter_by(deleted=False)
    elif read_deleted == 'yes':
        pass  # omit the filter to include deleted and active
    elif read_deleted == 'only':
        query = query.filter_by(deleted=True)

    if not context.is_admin and hasattr(model, 'tenant_id'):
        query = query.filter_by(tenant_id=context.tenant_id)

    return query


# load_balancers
def load_balancer_create(context, configs):
    with context.session.begin():
        load_balancer_ref = models.LoadBalancer()
        load_balancer_ref.update(configs['lb'])
        context.session.add(load_balancer_ref)
        config_ref = models.LoadBalancerConfig()
        config_ref.update(configs['config'])
        context.session.add(config_ref)
        domains = []
        for domain_values in configs['domains']:
            domain_ref = models.LoadBalancerDomain()
            domain_ref.update(domain_values)
            domains.append(domain_ref)
        if domains:
            context.session.add_all(domains)
        associations = []
        for association_values in configs['associations']:
            association_ref = models.LoadBalancerInstanceAssociation()
            association_ref.update(association_values)
            associations.append(association_ref)
        if associations:
            context.session.add_all(associations)
        context.session.flush()
        return load_balancer_ref


def load_balancer_destroy(context, load_balancer_id):
    with context.session.begin():
        load_balancer_ref = load_balancer_get(context, load_balancer_id)
        for domain in load_balancer_ref.domains:
            domain.deleted = True
        for instance in load_balancer_ref.instances:
            instance.deleted = True
        load_balancer_ref.config.deleted = True
        load_balancer_ref.deleted = True
        context.session.add(load_balancer_ref)
        context.session.flush()


def load_balancer_get(context, load_balancer_id):
    result = model_query(context, models.LoadBalancer).\
                        filter_by(id=load_balancer_id).\
                        first()
    if not result:
        raise exceptions.LoadBalancerNotFound(id=load_balancer_id)
    return result


def load_balancer_update_state(context, load_balancer_id, state):
    with context.session.begin():
        context.session.query(models.LoadBalancer).\
                            filter_by(id=load_balancer_id).\
                            update({'state': state})


def load_balancer_update_config(context, load_balancer_id, config_values):
    with context.session.begin():
        load_balancer_ref = load_balancer_get(context, load_balancer_id)
        load_balancer_ref.config.deleted = True
        config_ref = models.LoadBalancerConfig()
        config_ref.load_balancer_id = load_balancer_ref.id
        config_ref.update(config_values)
        context.session.add(load_balancer_ref)
        context.session.add(config_ref)
        context.session.flush()


def load_balancer_update_domains(context, load_balancer_id, new_domains):
    with context.session.begin():
        load_balancer_ref = load_balancer_get(context, load_balancer_id)
        old_domains = load_balancer_ref.domains
        old_domain_names = map(lambda x: x['name'], old_domains)
        new_domain_names = map(lambda x: x['name'], new_domains)
        for domain in old_domains:
            if domain['name'] not in new_domain_names:
                domain.deleted = True
        added_domains = []
        for domain in new_domains:
            if domain['name'] not in old_domain_names:
                domain_values = {
                    'load_balancer_id': load_balancer_ref.id,
                    'name': domain['name'],
                }
                domain_ref = models.LoadBalancerDomain()
                domain_ref.update(domain_values)
                added_domains.append(domain_ref)
        if added_domains:
            context.session.add_all(added_domains)
        context.session.add(load_balancer_ref)
        context.session.flush()


def load_balancer_update_instances(context, load_balancer_id, new_instances):
    with context.session.begin():
        load_balancer_ref = load_balancer_get(context, load_balancer_id)
        old_instances = load_balancer_ref.instances
        old_instance_uuids = map(lambda x: x['instance_uuid'], old_instances)
        new_instance_uuids = map(lambda x: x['instance_uuid'], new_instances)
        for instance in old_instances:
            if instance['instance_uuid'] not in new_instance_uuids:
                instance.deleted = True
        added_instances = []
        for instance in new_instances:
            if instance['instance_uuid'] not in old_instance_uuids:
                instance_values = {
                    'load_balancer_id': load_balancer_ref.id,
                    'instance_uuid': instance['instance_uuid'],
                    'instance_ip': instance['instance_ip'],
                }
                instance_ref = models.LoadBalancerInstanceAssociation()
                instance_ref.update(instance_values)
                added_instances.append(instance_ref)
        if added_instances:
            context.session.add_all(added_instances)
        context.session.add(load_balancer_ref)
        context.session.flush()


##@require_admin_context
##def load_balancer_get_all(context, filters=None):
##    filters = filters or dict()
##    return model_query(context, models.LoadBalancer).filter_by(**filters).all()
##
##
##@require_admin_context
##def load_balancer_domain_get_all(context, filters=None):
##    filters = filters or dict()
##    return model_query(context, models.LoadBalancerDomain).\
##                       filter_by(**filters).\
##                       all()
