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
#
# vim: tabstop=4 shiftwidth=4 softtabstop=4

"""
Shunt base exception handling.
"""

from openstack.common.exception import Error
from openstack.common.exception import OpenstackException


class ShuntException(OpenstackException):
    """Base Shunt Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")


# api exceptions
class MissingParameter(ShuntException):
    message = _("missing parameter: %(key)s.")


class InvalidParameter(ShuntException):
    message = _("invalid parameter: %(msg)s.")


class CreateLoadBalancerFailed(ShuntException):
    message = _("create load balancer failed: %(msg)s")


class DeleteLoadBalancerFailed(ShuntException):
    message = _("delete load balancer failed: %(msg)s")


class UpdateLoadBalancerFailed(ShuntException):
    message = _("update load balancer failed: %(msg)s")


class GetLoadBalancerFailed(ShuntException):
    message = _("get load balancer failed: %(msg)s")


class GetAllLoadBalancerFailed(ShuntException):
    message = _("get all load balancer failed: %(msg)s")


class GetAllHttpServersFailed(ShuntException):
    message = _("get all http servers failed: %(msg)s")


# db exceptions
class LoadBalancerNotFound(ShuntException):
    message = _("LoadBalancer %(id)s could not be found.")
