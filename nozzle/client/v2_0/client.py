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

import httplib
import urllib

from nozzle.common import exception
from nozzle.client.httpclient import HTTPClient
from nozzle.client.serializer import Serializer


class Client(object):
    """Client for the nozzle v2.0 API.

    :param string username: Username for authentication. (optional)
    :param string password: Password for authentication. (optional)
    :param string token: Token for authentication. (optional)
    :param string tenant_name: Tenant name. (optional)
    :param string auth_url: Keystone service endpoint for authorization.
    :param string region_name: Name of a region to select when choosing an
                               endpoint from the service catalog.
    """

    loadbalancers_path = "/loadbalancers"
    loadbalancer_path = "/loadbalancers/%s"

    def create_loadbalancer(self, body=None):
        """Create a new loadbalancer for a tenant."""
        return self.post(self.loadbalancers_path, body=body)

    def update_loadbalancer(self, loadbalancer, body=None):
        """Update a loadbalancer."""
        return self.put(self.loadbalancer_path % (loadbalancer), body=body)

    def delete_loadbalancer(self, loadbalancer):
        """Delete a loadbalancer."""
        return self.delete(self.loadbalancer_path % (loadbalancer))

    def list_loadbalancers(self, **_params):
        """Fetches a list of loadbalancers for a tenant."""
        return self.get(self.loadbalancers_path, params=_params)

    def list_loadbalancer_domains(self, **_params):
        """Fetches all domains binding to load balancers."""
        return self.get(self.loadbalancer_path % ('domains'), params=_params)

    def show_loadbalancer(self, loadbalancer):
        """Fetches information of a certain load balancer."""
        return self.get(self.loadbalancer_path % (loadbalancer))

    def create_for_instance(self, body=None):
        """create a new load balancer for instance."""
        return self.post("/%s/create_for_instance" % (self.loadbalancers_path),
                         body=body)

    def delete_for_instance(self, instance_uuid):
        """Delete and update loadbalancer for instance."""
        return self.delete('/%s/delete_for_instance/%s' % (
            self.loadbalancers_path, instance_uuid))

    def __init__(self, **kwargs):
        """Initialize a new client for the Nozzle v2.0 API."""
        super(Client, self).__init__()
        self.httpclient = HTTPClient(**kwargs)
        ##self.version = '1.0'
        ##self.action_prefix = "/v%s" % self.version
        self.format = 'json'
        self.retries = 0
        self.retry_interval = 1

    def content_type(self, format=None):
        """
        Returns the mime-type for either 'xml' or 'json'.  Defaults to the
        currently set format
        """
        if not format:
            format = self.format
        return "application/%s" % (format)

    def serialize(self, data):
        """
        Serializes a dictionary with a single key (which can contain any
        structure) into either xml or json
        """
        if data is None:
            return None
        elif type(data) is dict:
            return Serializer().serialize(data, self.content_type())
        else:
            raise Exception("unable to serialize object of type = '%s'" %
                            type(data))

    def deserialize(self, data, status_code):
        """
        Deserializes a an xml or json string into a dictionary
        """
        if status_code == 204:
            return data
        return Serializer().deserialize(data, self.content_type())

    def get_status_code(self, response):
        """
        Returns the integer status code from the response, which
        can be either a Webob.Response (used in testing) or httplib.Response
        """
        if hasattr(response, 'status_int'):
            return response.status_int
        else:
            return response.status

    def handle_fault_response(self, status_code, response_body):
        # Create exception with HTTP status code and message
        error_message = response_body
        ##_logger.debug("Error message: %s", error_message)
        # Add deserialized error message to exception arguments
        try:
            des_error_body = Serializer().deserialize(error_message,
                                                      self.content_type())
        except:
            des_error_body = {'message': error_message}
        # Raise the appropriate exception
        raise Exception(des_error_body)

    def do_request(self, method, action, body=None, headers=None, params=None):
        ##action = self.action_prefix + action
        if params:
            action += '?' + urllib.urlencode(params, doseq=1)
        if body:
            body = self.serialize(body)
        self.httpclient.content_type = self.content_type()
        resp, replybody = self.httpclient.do_request(action, method, body=body)
        status_code = self.get_status_code(resp)
        if status_code in (httplib.OK,
                           httplib.CREATED,
                           httplib.ACCEPTED,
                           httplib.NO_CONTENT):
            return self.deserialize(replybody, status_code)
        else:
            self.handle_fault_response(status_code, replybody)

    def delete(self, action, body=None, headers=None, params=None):
        return self.do_request("DELETE", action, body=body,
                               headers=headers, params=params)

    def get(self, action, body=None, headers=None, params=None):
        return self.do_request("GET", action, body=body,
                               headers=headers, params=params)

    def post(self, action, body=None, headers=None, params=None):
        return self.do_request("POST", action, body=body,
                               headers=headers, params=params)

    def put(self, action, body=None, headers=None, params=None):
        return self.do_request("PUT", action, body=body,
                               headers=headers, params=params)
