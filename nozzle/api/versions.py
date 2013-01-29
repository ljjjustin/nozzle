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

import webob.dec
import webob.exc

from nozzle.openstack.common import jsonutils
from nozzle.openstack.common import wsgi


class Versions(object):

    @classmethod
    def factory(cls, global_config, **local_config):
        return cls()

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        """Return all nozzle API versions."""
        version_objs = [
            {
                "id": "v1.0",
                "status": "DEPRECATED",
            },
            {
                "id": "v2.0",
                "status": "CURRENT",
            },
        ]
        if req.path != '/':
            return webob.exc.HTTPNotFound()

        reponse = dict(versions=version_objs)

        body = jsonutils.dumps(reponse)

        reponse = webob.Response()
        reponse.body = body

        return reponse
