# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

"""
SQLAlchemy models for nozzle data.
"""
import datetime

from sqlalchemy import Column, ForeignKey
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, backref, object_mapper


BASE = declarative_base()


def utcnow():
    return datetime.datetime.utcnow()


class ShuntBase(object):
    """Base class for Shunt Models."""
    __table_args__ = {'mysql_engine': 'InnoDB'}
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, onupdate=utcnow)
    deleted_at = Column(DateTime)
    deleted = Column(Boolean, default=False)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __iter__(self):
        self._i = iter(object_mapper(self).columns)
        return self

    def next(self):
        n = self._i.next().name
        return n, getattr(self, n)

    def update(self, values):
        """Make the model object behave like a dict"""
        for k, v in values.iteritems():
            setattr(self, k, v)

    def iteritems(self):
        """Make the model object behave like a dict.
        Includes attributes from joins."""
        local = dict(self)
        joined = dict([(k, v) for k, v in self.__dict__.iteritems()
                       if not k[0] == '_'])
        local.update(joined)
        return local.iteritems()


class LoadBalancer(BASE, ShuntBase):
    """Represents a load balancer."""

    __tablename__ = 'load_balancers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    user_id = Column(String(255), nullable=False)
    project_id = Column(String(255), nullable=False)
    free = Column(Boolean, default=False)
    uuid = Column(String(36), nullable=False)
    state = Column(String(255), nullable=False)
    protocol = Column(String(255), nullable=False)
    dns_prefix = Column(String(255), nullable=False)
    listen_port = Column(Integer, nullable=False)
    instance_port = Column(Integer, nullable=False)


class LoadBalancerConfig(BASE, ShuntBase):
    """Represents the configuration of a load balancer."""

    __tablename__ = 'load_balancer_configs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    load_balancer_id = Column(Integer, ForeignKey('load_balancers.id'))
    balancing_method = Column(String(255), nullable=False)
    health_check_timeout_ms = Column(Integer)
    health_check_interval_ms = Column(Integer)
    health_check_target_path = Column(String(255))
    health_check_unhealthy_threshold = Column(Integer)
    health_check_healthy_threshold = Column(Integer)

    load_balancer = relationship(
        LoadBalancer,
        backref=backref('config', uselist=False),
        foreign_keys=load_balancer_id,
        primaryjoin=('and_('
                     'LoadBalancerConfig.deleted == False,'
                     'LoadBalancer.id == LoadBalancerConfig.load_balancer_id)')
    )


class LoadBalancerDomain(BASE, ShuntBase):
    """Represents a domain binding to load balancer."""

    __tablename__ = 'load_balancer_domains'
    id = Column(Integer, primary_key=True, autoincrement=True)
    load_balancer_id = Column(Integer, ForeignKey('load_balancers.id'))
    name = Column(String(255), nullable=False)

    load_balancer = relationship(
        LoadBalancer,
        backref=backref('domains'),
        foreign_keys=load_balancer_id,
        primaryjoin=('and_('
                     'LoadBalancerDomain.deleted == False,'
                     'LoadBalancer.id == LoadBalancerDomain.load_balancer_id)')
    )


class LoadBalancerInstanceAssociation(BASE, ShuntBase):
    __tablename__ = 'load_balancer_instance_association'
    load_balancer_id = Column(Integer, primary_key=True)
    instance_uuid = Column(String(36), primary_key=True)

    load_balancer = relationship(
        LoadBalancer,
        backref=backref('instances'),
        foreign_keys=load_balancer_id,
        primaryjoin=('and_('
                     'LoadBalancerInstanceAssociation.deleted == False,'
                     'LoadBalancer.id == '
                     'LoadBalancerInstanceAssociation.load_balancer_id)')
    )
