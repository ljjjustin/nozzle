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

import logging
import zmq

from nozzle.common import flags
from nozzle import manager


class WorkerManager(manager.Manager):

    def __init__(self):
        super(WorkerManager, self).__init__()

    def init_host(self):
        """Handle initialization if this is a standalone service.

        Child class should override this method

        """
        context = zmq.Context()
        # Socket for control input
        self.broadcast = context.socket(zmq.SUB)
        self.broadcast.connect("tcp://%s" % zmqSUBAddr)
        self.broadcast.setsockopt(zmq.SUBSCRIBE, "lb")

        # Socket to send messages to
        self.feedback = context.socket(zmq.PUSH)
        self.feedback.connect("tcp://%s" % zmqPUSHAddr)

        # Process messages from broadcast
        self.poller = zmq.Poller()
        self.poller.register(self.broadcast, zmq.POLLIN)

        self.ngx_configurer = configure_nginx.NginxProxyConfigurer()
        self.ha_configurer = configure_haproxy.HaproxyConfigurer()

    def start(self):
        LOG.debug('Started sws-lb-worker')
        while True:
            try:
                socks = dict(self.poller.poll())
            except zmq.ZMQError:
                # interrupted
                break

            if socks.get(self.broadcast) == zmq.POLLIN:
                try:
                    msg_type, msg_id, msg_body = \
                                        self.broadcast.recv_multipart()
                except zmq.ZMQError:
                    # TODO(wenjianhn): feed back Error msg?
                    break

            try:
                message = json.loads(msg_body)
            except ValueError, e:
                self.LOG.warn("Bad JSON: %s. msg_body: %s", e, msg_body)
                # TODO(wenjianhn) feedback
                break

            self.LOG.info('Received request: %s', message)

            # check input message
            if 'cmd' not in message or 'msg' not in message:
                self.LOG.warn("Error. 'cmd' or 'msg' not in message")
                code = 500
                desc = "missing 'cmd' or 'msg' in request"

                self.feedback.send_multipart([msg_type, msg_id,
                                json.dumps({'cmd': 'unknown',
                                            'msg': {
                                                'worker_id': worker_id,
                                                'code': code,
                                                'desc': desc}})])
                break

            code = 200
            desc = "request was done successfully"
            uuid = message['msg']['uuid']

            if message['msg']['protocol'] == 'http':
                try:
                    self.ngx_configurer.do_config(message)
                except exception.NginxConfigureError, e:
                    code = 500
                    desc = str(e)
            elif message['msg']['protocol'] == 'tcp':
                try:
                    self.ha_configurer.do_config(message)
                except exception.HaproxyConfigureError, e:
                    code = 500
                    desc = str(e)
            else:
                code = 500
                desc = "Error: unsupported protocol"
                self.LOG('Error. Unsupported protocol')

            # Send results to feedback
            self.feedback.send_multipart([msg_type, msg_id,
                                json.dumps({'cmd': message['cmd'],
                                            'msg': {
                                                'worker_id': worker_id,
                                                'code': code,
                                                'uuid': uuid,
                                                'desc': desc,
                                            }})])
