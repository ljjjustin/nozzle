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

import zmq

from nozzle.openstack.common import cfg
from nozzle.openstack.common import jsonutils
from nozzle.openstack.common import log as logging

from nozzle import manager
from nozzle.common import exception
from nozzle.common import flags
from nozzle.common import utils
from nozzle.worker.driver import haproxy
from nozzle.worker.driver import nginx


worker_opts = [
    cfg.StrOpt('service_interface',
               default='lo',
               help="listen on which interface to provide service."),
]

FLAGS = flags.FLAGS
FLAGS.register_opts(worker_opts, 'worker')

LOG = logging.getLogger(__name__)


class WorkerManager(manager.Manager):

    def __init__(self):
        self.ips = []
        super(WorkerManager, self).__init__()

    def init_host(self):
        """Handle initialization if this is a standalone service.

        Child class should override this method

        """
        dev = FLAGS.worker.service_interface
        cmd = 'ip addr show dev %s' % dev
        out = utils.execute(cmd)
        for line in out.split('\n'):
            fields = line.split()
            if fields and fields[0] == 'inet':
                self.ips.append(fields[1].split('/')[0])

    def binding_ip(self, ips):
        dev = FLAGS.worker.service_interface
        for ip in ips:
            if ip in self.ips:
                continue
            if FLAGS.worker.service_interface == 'lo':
                cmd = 'ip addr add %s/32 scope link dev %s' % (ip, dev)
            else:
                cmd = 'ip addr add %s/32 scope global dev %s' % (ip, dev)
            utils.execute(cmd)

    def start(self):
        context = zmq.Context()
        # Socket for control input
        self.broadcast = context.socket(zmq.SUB)
        self.broadcast.connect("tcp://%s:%s" % (FLAGS.broadcast_listen,
                                                FLAGS.broadcast_listen_port))
        self.broadcast.setsockopt(zmq.SUBSCRIBE, "lb")

        # Socket to send messages to
        self.feedback = context.socket(zmq.PUSH)
        self.feedback.connect("tcp://%s:%s" % (FLAGS.feedback_listen,
                                               FLAGS.feedback_listen_port))

        # Process messages from broadcast
        self.poller = zmq.Poller()
        self.poller.register(self.broadcast, zmq.POLLIN)

        self.ha_configurer = haproxy.HaproxyConfigurer()
        self.ngx_configurer = nginx.NginxProxyConfigurer()

        self.binding_ip(self.ha_configurer._bind_ip)
        self.binding_ip(self.ngx_configurer._bind_ip)

    def wait(self):

        LOG.info('nozzle worker starting...')

        while True:
            socks = dict(self.poller.poll())
            if socks.get(self.broadcast) == zmq.POLLIN:
                msg_type, msg_id, msg_body = self.broadcast.recv_multipart()
                message = jsonutils.loads(msg_body)
                LOG.info('Received request: %s', message)

                response_msg = {'code': 200, 'message': 'OK'}
                # check input message
                if 'cmd' not in message or 'args' not in message:
                    LOG.warn("Error. 'cmd' or 'args' not in message")
                    response_msg['code'] = 500
                    response_msg['message'] = "missing 'cmd' or 'args' field"

                    self.feedback.send_multipart([msg_type, msg_id,
                                                  jsonutils.dumps(
                                                      response_msg)])
                    break

                if message['args']['protocol'] == 'http':
                    try:
                        self.ngx_configurer.do_config(message)
                    except exception.NginxConfigureError, e:
                        response_msg['code'] = 500
                        response_msg['message'] = str(e)
                elif message['args']['protocol'] == 'tcp':
                    try:
                        self.ha_configurer.do_config(message)
                    except exception.HaproxyConfigureError, e:
                        response_msg['code'] = 500
                        response_msg['message'] = str(e)
                else:
                    LOG.exception('Error. Unsupported protocol')
                    response_msg['code'] = 500
                    response_msg['message'] = "Error: unsupported protocol"

                # Send results to feedback
                response_msg['cmd'] = message['cmd']
                response_msg['uuid'] = message['args']['uuid']
                self.feedback.send_multipart([msg_type, msg_id,
                                              jsonutils.dumps(response_msg)])
