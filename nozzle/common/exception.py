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


# db exceptions
##class LoadBalancerNotFound(exception.NotFound):
##    message = _("LoadBalancer %(load_balancer_id)s could not be found.")
##
##
##class LoadBalancerNotFoundByUUID(exception.NotFound):
##    message = _("LoadBalancer %(uuid)s could not be found by uuid.")
##
##
##class LoadBalancerNotFoundByName(exception.NotFound):
##    message = _("LoadBalancer %(load_balancer_name)s could not be "
##                "found by name.")
##
##
##class LoadBalancerConfigNotFound(exception.NotFound):
##    message = _("LoadBalancerConfig %(config_id)s could not be found.")
##
##
##class LoadBalancerConfigNotFoundByLoadBalancerId(exception.NotFound):
##    message = _("LoadBalancerConfig %(load_balancer_id)s could not be found.")
##
##
##class LoadBalancerDomainNotFound(exception.NotFound):
##    message = _("LoadBalancerDomain %(domain_id)s could not be found.")
##
##
##class LoadBalancerDomainNotFoundByName(exception.NotFound):
##    message = _("LoadBalancerDomain %(domain_name)s could not be found.")
##
##
##class LoadBalancerInstanceAssociationNotFound(exception.NotFound):
##    message = _("LoadBalancerInstanceAssociation %(load_balancer_id)s "
##                "with %(instance_uuid)s could not be found")


class CommandError(Exception):
    pass


class ProcessExecutionError(IOError):
    def __init__(self, exit_code=None, output=None, cmd=None):
        self.exit_code = exit_code
        self.output = output
        self.cmd = cmd

        message = 'Command: %(cmd)s\n' \
                  'Exit code: %(exit_code)s\n' \
                  'Output: %(output)s\r\n' % locals()

        IOError.__init__(self, message)


class LBWorkerException(Exception):
    """Base Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = "An unknown exception occurred."

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.message % kwargs

            except Exception as e:
                # at least get the core message out if something happened
                message = self.message

        super(LBWorkerException, self).__init__(message)


class NotFound(LBWorkerException):
    message = "Resource could not be found."
    code = 404


class FileNotFound(NotFound):
    message = "File %(file_path)s could not be found."


class DirNotFound(NotFound):
    message = "Directory %(dir)s could not be found."


class ConfigNotFound(NotFound):
    message = "Could not find config at %(path)s"


class Invalid(LBWorkerException):
    message = "Unacceptable parameters."
    code = 400


class InvalidType(Invalid):
    message = "Valid type should be %(valid_type)s not %(invalid_type)s"


class InvalidPort(Invalid):
    message = "Invalid port %(port)s. %(msg)s"


class InvalidIpv4Address(Invalid):
    message = "%(address)s is not a valid IP v4 address."


class NginxConfFileExists(Invalid):
    message = ("The supplied nginx configuration file (%(path)s) "
               "already exists, it is expected not to exist.")


class BadRequest(LBWorkerException):
    """
    The worker could not comply with the request since
    it is either malformed or otherwise incorrect.
    """
    message = "%(explanation)s"


class ConfigureError(LBWorkerException):
    message = "Could not configure the server."


class NginxConfigureError(ConfigureError):
    message = "Could not configure nginx: %(explanation)s"


class NginxCreateProxyError(NginxConfigureError):
    message = "Could not create the nginx proxy: %(explanation)s"


class NginxUpdateProxyError(NginxConfigureError):
    message = "Could not update the nginx proxy: %(explanation)s"


class NginxDeleteProxyError(NginxConfigureError):
    message = "Could not delete the nginx proxy: %(explanation)s"


class HaproxyConfigureError(ConfigureError):
    message = "Could not configure haproxy: %(explanation)s"


class HaproxyCreateError(HaproxyConfigureError):
    message = "Could not create the haproxy proxy: %(explanation)s"


class HaproxyCreateCfgError(HaproxyConfigureError):
    message = ("Could not create the haproxy proxy "
               " configuration: %(explanation)s")


class HaproxyUpdateError(HaproxyConfigureError):
    message = "Could not update the haproxy proxy: %(explanation)s"


class HaproxyDeleteError(HaproxyConfigureError):
    message = "Could not delete the haproxy proxy: %(explanation)s"


class HaproxyLBExists(Invalid):
    message = ("The supplied load balancer (%(name)s) "
               "already exists, it is expected not to exist.")


class HaproxyLBNotExists(Invalid):
    message = ("The supplied load balancer (%(name)s) "
               "does not exists, it is expected to exist.")
