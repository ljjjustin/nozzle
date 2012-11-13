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

from nozzle.openstack.common import exception


class NozzleException(exception.OpenstackException):
    """Base Shunt Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")


class Unauthorized(NozzleException):
    """
    HTTP 401 - Unauthorized: bad credentials.
    """
    message = _("Unauthorized: bad credentials.")


class Forbidden(NozzleException):
    """
    HTTP 403 - Forbidden: your credentials don't give you access to this
    resource.
    """
    message = _("Forbidden: your credentials don't give you "
                "access to this resource")


class EndpointNotFound(NozzleException):
    message = _("endpoint not found")


class AmbiguousEndpoints(NozzleException):
    message = _("ambigous endpoint were found")


# api exceptions
class MissingParameter(NozzleException):
    message = _("missing parameter: %(key)s.")


class InvalidParameter(NozzleException):
    message = _("invalid parameter: %(msg)s.")


class CreateLoadBalancerFailed(NozzleException):
    message = _("create load balancer failed: %(msg)s")


class DeleteLoadBalancerFailed(NozzleException):
    message = _("delete load balancer failed: %(msg)s")


class UpdateLoadBalancerFailed(NozzleException):
    message = _("update load balancer failed: %(msg)s")


class GetLoadBalancerFailed(NozzleException):
    message = _("get load balancer failed: %(msg)s")


class GetAllLoadBalancerFailed(NozzleException):
    message = _("get all load balancer failed: %(msg)s")


class GetAllHttpServersFailed(NozzleException):
    message = _("get all http servers failed: %(msg)s")


# db exceptions
class LoadBalancerNotFound(NozzleException):
    message = _("LoadBalancer %(load_balancer_id)s could not be found.")


class LoadBalancerNotFoundByUUID(NozzleException):
    message = _("LoadBalancer %(uuid)s could not be found by uuid.")


class LoadBalancerNotFoundByName(NozzleException):
    message = _("LoadBalancer %(load_balancer_name)s could not be "
                "found by name.")


class LoadBalancerNotFoundByInstanceUUID(NozzleException):
    message = _("LoadBalancer %(instance_uuid)s could not be found by name.")


class LoadBalancerConfigNotFound(NozzleException):
    message = _("LoadBalancerConfig %(config_id)s could not be found.")


class LoadBalancerConfigNotFoundByLoadBalancerId(NozzleException):
    message = _("LoadBalancerConfig %(load_balancer_id)s could not be found.")


class LoadBalancerDomainNotFound(NozzleException):
    message = _("LoadBalancerDomain %(domain_id)s could not be found.")


class LoadBalancerDomainNotFoundByName(NozzleException):
    message = _("LoadBalancerDomain %(domain_name)s could not be found.")


class LoadBalancerInstanceAssociationNotFound(NozzleException):
    message = _("LoadBalancerInstanceAssociation %(load_balancer_id)s "
                "with %(instance_uuid)s could not be found")


class CommandError(Exception):
    pass


class ProcessExecutionError(IOError):
    def __init__(self, exit_code=None, output=None, cmd=None):
        self.exit_code = exit_code
        self.output = output
        self.cmd = cmd

        message = _('Command: %(cmd)s\n'
                    'Exit code: %(exit_code)s\n'
                    'Output: %(output)s\r\n') % locals()

        IOError.__init__(self, message)


class LBWorkerException(Exception):
    """Base Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")

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
    message = _("Resource could not be found.")
    code = 404


class FileNotFound(NotFound):
    message = _("File %(file_path)s could not be found.")


class DirNotFound(NotFound):
    message = _("Directory %(dir)s could not be found.")


class ConfigNotFound(NotFound):
    message = _("Could not find config at %(path)s")


class Invalid(LBWorkerException):
    message = _("Unacceptable parameters.")
    code = 400


class InvalidType(Invalid):
    message = _("Valid type should be %(valid_type)s not %(invalid_type)s")


class InvalidPort(Invalid):
    message = _("Invalid port %(port)s. %(msg)s")


class InvalidIpv4Address(Invalid):
    message = _("%(address)s is not a valid IP v4 address.")


class NginxConfFileExists(Invalid):
    message = _("The supplied nginx configuration file (%(path)s) "
                "already exists, it is expected not to exist.")


class BadRequest(LBWorkerException):
    """
    The worker could not comply with the request since
    it is either malformed or otherwise incorrect.
    """
    message = _("%(explanation)s")


class ConfigureError(LBWorkerException):
    message = _("Could not configure the server.")


class NginxConfigureError(ConfigureError):
    message = _("Could not configure nginx: %(explanation)s")


class NginxCreateProxyError(NginxConfigureError):
    message = _("Could not create the nginx proxy: %(explanation)s")


class NginxUpdateProxyError(NginxConfigureError):
    message = _("Could not update the nginx proxy: %(explanation)s")


class NginxDeleteProxyError(NginxConfigureError):
    message = _("Could not delete the nginx proxy: %(explanation)s")


class HaproxyConfigureError(ConfigureError):
    message = _("Could not configure haproxy: %(explanation)s")


class HaproxyCreateError(HaproxyConfigureError):
    message = _("Could not create the haproxy proxy: %(explanation)s")


class HaproxyCreateCfgError(HaproxyConfigureError):
    message = _("Could not create the haproxy proxy "
                " configuration: %(explanation)s")


class HaproxyUpdateError(HaproxyConfigureError):
    message = _("Could not update the haproxy proxy: %(explanation)s")


class HaproxyDeleteError(HaproxyConfigureError):
    message = "Could not delete the haproxy proxy: %(explanation)s"


class HaproxyLBExists(Invalid):
    message = _("The supplied load balancer (%(name)s) "
                "already exists, it is expected not to exist.")


class HaproxyLBNotExists(Invalid):
    message = _("The supplied load balancer (%(name)s) "
                "does not exists, it is expected to exist.")
