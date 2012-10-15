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

"""Implementation of SQLAlchemy backend."""
import datetime

from sqlalchemy.sql.expression import literal_column

from nozzle.common import exception
from nozzle.db.sqlalchemy import models


def utcnow():
    return datetime.datetime.utcnow()


def is_admin_context(context):
    """Indicates if the request context is an administrator."""
    if not context:
        raise Exception('die')
    return context.is_admin


def require_admin_context(f):
    """Decorator to require admin request context.

    The first argument to the wrapped function must be the context.

    """

    def wrapper(*args, **kwargs):
        if not is_admin_context(args[0]):
            raise Exception('admin context required')
        return f(*args, **kwargs)
    return wrapper


# load_balancers
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

    if not context.is_admin and hasattr(model, 'project_id'):
        query = query.filter_by(project_id=context.tenant_id)

    return query


def load_balancer_get(context, load_balancer_id):
    result = model_query(context, models.LoadBalancer).\
                        filter_by(id=load_balancer_id).\
                        first()
    if not result:
        raise exception.LoadBalancerNotFound(load_balancer_id=load_balancer_id)
    return result


def load_balancer_get_by_uuid(context, uuid):
    result = model_query(context, models.LoadBalancer).\
                        filter_by(uuid=uuid).\
                        first()
    if not result:
        raise exception.LoadBalancerNotFoundByUUID(uuid=uuid)
    return result


def load_balancer_get_by_name(context, name):
    result = model_query(context, models.LoadBalancer).\
                        filter_by(name=name).\
                        first()
    if not result:
        raise exception.LoadBalancerNotFoundByName(load_balancer_name=name)
    return result


@require_admin_context
def load_balancer_get_all(context, filters=None):
    filters = filters or dict()
    return model_query(context, models.LoadBalancer).filter_by(**filters).all()


def load_balancer_create(context, values):

    try:
        result = load_balancer_get_by_name(context, values['name'])
    except exception.LoadBalancerNotFoundByName:
        pass
    except Exception, exp:
        raise exp
    else:
        raise Exception('unknown DB error!')

    load_balancer_ref = models.LoadBalancer()
    load_balancer_ref.update(values)
    context.session.add(load_balancer_ref)
    context.session.flush()
    return load_balancer_ref


def load_balancer_destroy(context, load_balancer_id):
    with context.session.begin():
        context.session.query(models.LoadBalancer).\
                filter_by(id=load_balancer_id).\
                update({'deleted': True,
                        'state': 'deleted',
                        'deleted_at': utcnow()})


def load_balancer_update_state(context, load_balancer_uuid, state):
    with context.session.begin():
        context.session.query(models.LoadBalancer).\
                filter_by(uuid=load_balancer_uuid).\
                update({'state': state,
                        'updated_at': literal_column('updated_at')})


# load_balancer_config
def load_balancer_config_get(context, config_id):
    result = model_query(context, models.LoadBalancerConfig).\
                        filter_by(id=config_id).\
                        first()
    if not result:
        raise exception.LoadBalancerConfigNotFound(config_id=config_id)
    return result


def load_balancer_config_get_by_load_balancer_id(context, load_balancer_id):
    result = model_query(context, models.LoadBalancerConfig).\
                        filter_by(load_balancer_id=load_balancer_id).\
                        first()
    if not result:
        raise exception.LoadBalancerConfigNotFoundByLoadBalancerId(
            load_balancer_id=load_balancer_id)
    return result


def load_balancer_config_create(context, values):

    try:
        result = load_balancer_config_get_by_load_balancer_id(
            context, values['load_balancer_id'])
    except exception.LoadBalancerConfigNotFoundByLoadBalancerId:
        pass
    except Exception, exp:
        raise exp
    else:
        raise Exception('unknown DB error!')

    load_balancer_config_ref = models.LoadBalancerConfig()
    load_balancer_config_ref.update(values)
    context.session.add(load_balancer_config_ref)
    context.session.flush()
    return load_balancer_config_ref


def load_balancer_config_destroy(context, config_id):
    with context.session.begin():
        context.session.query(models.LoadBalancerConfig).\
                filter_by(id=config_id).\
                update({'deleted': True,
                        'deleted_at': utcnow()})


# load_balancer_domain
def load_balancer_domain_get(context, domain_id):
    result = model_query(context, models.LoadBalancerDomain).\
                        filter_by(id=domain_id).\
                        first()
    if not result:
        raise exception.LoadBalancerDomainNotFound(domain_id=domain_id)
    return result


def load_balancer_domain_get_by_name(context, domain_name):
    result = model_query(context, models.LoadBalancerDomain).\
                        filter_by(name=domain_name).\
                        first()
    if not result:
        raise exception.LoadBalancerDomainNotFoundByName(
            domain_name=domain_name)
    return result


@require_admin_context
def load_balancer_domain_get_all(context, filters=None):
    filters = filters or dict()
    return model_query(context, models.LoadBalancerDomain).\
                       filter_by(**filters).\
                       all()


def load_balancer_domain_create(context, values):

    try:
        result = load_balancer_domain_get_by_name(context, values['name'])
    except exception.LoadBalancerDomainNotFoundByName:
        pass
    except Exception, exp:
        raise exp
    else:
        raise Exception('unknown DB error!')

    load_balancer_domain_ref = models.LoadBalancerDomain()
    load_balancer_domain_ref.update(values)
    context.session.add(load_balancer_domain_ref)
    context.session.flush()
    return load_balancer_domain_ref


def load_balancer_domain_destroy(context, domain_id):
    with context.session.begin():
        context.session.query(models.LoadBalancerDomain).\
                filter_by(id=domain_id).\
                update({'deleted': True,
                        'deleted_at': utcnow()})


def load_balancer_instance_association_get(context,
                                           load_balancer_id,
                                           instance_uuid):
    result = model_query(context, models.LoadBalancerInstanceAssociation).\
                        filter_by(load_balancer_id=load_balancer_id).\
                        filter_by(instance_uuid=instance_uuid).\
                        first()
    if not result:
        raise exception.LoadBalancerInstanceAssociationNotFound(
            load_balancer_id=load_balancer_id,
            instance_uuid=instance_uuid)
    return result


def load_balancer_instance_association_get_all(context, load_balancer_id):
    result = model_query(context, models.LoadBalancerInstanceAssociation).\
                        filter_by(load_balancer_id=load_balancer_id).\
                        all()
    if not result:
        raise exception.LoadBalancerInstanceAssociationNotFoundAll(
            load_balancer_id=load_balancer_id)
    return result


def load_balancer_instance_association_create(context, values):
    try:
        result = load_balancer_instance_association_get(
            context, values['load_balancer_id'], values['instance_uuid'])
    except exception.LoadBalancerInstanceAssociationNotFound:
        pass
    except Exception, exp:
        raise exp
    else:
        raise Exception('unknown DB error!')

    association_ref = models.LoadBalancerInstanceAssociation()
    association_ref.update(values)
    context.session.add(association_ref)
    context.session.flush()
    return association_ref


def load_balancer_instance_association_destroy(context,
                                               load_balancer_id,
                                               instance_uuid):
    with context.session.begin():
        context.session.query(models.LoadBalancerInstanceAssociation).\
                filter_by(load_balancer_id=load_balancer_id).\
                filter_by(instance_uuid=instance_uuid).\
                delete()
        context.session.flush()


def load_balancer_get_by_instance_uuid(context, instance_uuid):
    result = model_query(context, models.LoadBalancerInstanceAssociation).\
                        filter_by(instance_uuid=instance_uuid).\
                        all()
    if not result:
        raise exception.LoadBalancerNotFoundByInstanceUUID(
            instance_uuid=instance_uuid)

    for association_ref in result:
        load_balancer_ref = load_balancer_get(context,
                                              association_ref.load_balancer_id)
        if load_balancer_ref.free:
            return load_balancer_ref
