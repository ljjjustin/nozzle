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

from nozzle.client.v1_0 import client

class ClientManager(object):
    """Manages access to API clients, including authentication."""

    def __init__(self, username=None, password=None,
                 tenant_name=None, tenant_id=None,
                 token=None, auth_url=None, url=None,
                 region_name=None, api_version=None,
                 auth_strategy=None):
        self.username = username
        self.password = password
        self.tenant_name = tenant_name
        self.tenant_id = tenant_id
        self.token = token
        self.auth_url = auth_url
        self.url = url
        self.region_name = region_name
        self.api_version = api_version
        self.auth_strategy = auth_strategy
        self.service_catalog = None
        self.handle = None

    def get_client(self):
        if self.handle is None:
            self.handle = client.Client(username=self.username,
                                        password=self.password,
                                        tenant_name=self.tenant_name,
                                        region_name=self.region_name,
                                        auth_url=self.auth_url,
                                        endpoint_url=self.url,
                                        auth_strategy=self.auth_strategy,
                                        token=self.token)
        return self.handle
