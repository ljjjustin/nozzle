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

import eventlet
import logging
import zmq

from nozzle.openstack.common import jsonutils

from nozzle import manager
from nozzle.common import context
from nozzle.common import flags
from nozzle.common import utils
from nozzle.server import api
from nozzle.server import state

FLAGS = flags.FLAGS


def setup_logging(logfile):
    logger = logging.getLogger(logfile)
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(logfile)
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
            "%(asctime)s %(name)s %(levelname)s: %(message)s [-] %(funcName)s"
            " from (pid=%(process)d) %(filename)s:%(lineno)d")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def client_routine(*args, **kwargs):
    handler = kwargs['handler']
    broadcast = kwargs['broadcast']
    # Setup logging
    LOG = setup_logging('/var/log/nozzle/client.log')
    LOG.info('nozzle client starting...')

    poller = zmq.Poller()
    poller.register(handler, zmq.POLLIN)

    while True:
        eventlet.sleep(0)
        socks = dict(poller.poll(100))
        if socks.get(handler) == zmq.POLLIN:
            msg_type, msg_uuid, msg_json = handler.recv_multipart()
            response = dict()
            cli_msg = {'code': 200, 'message': 'OK'}
            try:
                msg_body = jsonutils.loads(msg_json)
                LOG.debug("<<<<<<< client: %s" % msg_body)
                method = msg_body['method']
                args = msg_body['args']
                ctxt = context.get_context(**args)
                method_func = getattr(api, method)
                result = method_func(ctxt, **args)
                if result is not None:
                    response.update(result)
                # send request to worker
                try:
                    msg = api.get_msg_to_worker(ctxt, method, **args)
                    if msg is not None:
                        request_msg = jsonutils.dumps(msg)
                        LOG.debug(">>>>>>> worker: %s" % request_msg)
                        broadcast.send_multipart([msg_type, msg_uuid,
                                                  request_msg])
                except Exception:
                    pass
            except Exception, e:
                cli_msg['code'] = 500
                cli_msg['message'] = str(e)
                LOG.exception(cli_msg['message'])
            response.update(cli_msg)
            response_msg = jsonutils.dumps(response)
            LOG.debug(">>>>>>> client: %s" % response_msg)
            handler.send_multipart([msg_type, msg_uuid, response_msg])


def worker_routine(*args, **kwargs):
    feedback = kwargs['feedback']
    # Setup logging
    LOG = setup_logging('/var/log/nozzle/worker.log')
    LOG.info('nozzle worker starting...')

    poller = zmq.Poller()
    poller.register(feedback, zmq.POLLIN)

    while True:
        eventlet.sleep(0)
        socks = dict(poller.poll(100))
        if socks.get(feedback) == zmq.POLLIN:
            msg_type, msg_uuid, msg_json = feedback.recv_multipart()
            msg_body = json.loads(msg_json)
            LOG.debug("<<<<<<< worker: %s" % msg_body)
            # update load balancer's state
            try:
                args = msg_body['msg']
                ctxt = context.get_admin_context()
                api.update_load_balancer_state(ctxt, **args)
            except Exception, exp:
                continue


def checker_routine(*args, **kwargs):
    broadcast = kwargs['broadcast']
    # Setup logging
    LOG = setup_logging('/var/log/nozzle/checker.log')
    LOG.info('nozzle checker starting...')

    states = [state.CREATING, state.UPDATING, state.DELETING]
    while True:
        eventlet.sleep(6)
        msg_type = 'lb'
        msg_uuid = utils.str_uuid()
        try:
            ctxt = context.get_admin_context()
            all_load_balancers = db.load_balancer_get_all(ctxt)
            transient_load_balancers = filter(lambda x: x.state in states,
                                              all_load_balancers)
            for load_balancer_ref in transient_load_balancers:
                try:
                    result = dict()
                    message = dict()
                    if load_balancer_ref.state == state.CREATING:
                        message['cmd'] = 'create_lb'
                        result = api.format_msg_to_worker(load_balancer_ref)
                    elif load_balancer_ref.state == state.UPDATING:
                        message['cmd'] = 'update_lb'
                        result = api.format_msg_to_worker(load_balancer_ref)
                    elif load_balancer_ref.state == state.DELETING:
                        message['cmd'] = 'delete_lb'
                        result['user_id'] = load_balancer_ref['user_id']
                        result['tenant_id'] = load_balancer_ref['tenant_id']
                        result['uuid'] = load_balancer_ref['uuid']
                        result['protocol'] = load_balancer_ref['protocol']
                    message['msg'] = result
                    request_msg = json.dumps(message)
                    LOG.debug(">>>>>>> worker: %s" % request_msg)
                    broadcast.send_multipart([msg_type, msg_uuid, request_msg])
                except Exception, exp:
                    continue
        except Exception:
            continue


class ServerManager(manager.Manager):

    def __init__(self):
        super(ServerManager, self).__init__()

    def init_host(self):
        """Handle initialization if this is a standalone service.

        Child class should override this method

        """
        self.pool = eventlet.GreenPool(3)

    def start(self):
        zmq_context = zmq.Context()

        # Socket to receive messages on
        handler = zmq_context.socket(zmq.REP)
        handler.bind("tcp://%s:%s" % (FLAGS.server_listen,
                                      FLAGS.server_listen_port))

        # Socket to send messages on
        broadcast = zmq_context.socket(zmq.PUB)
        broadcast.bind("tcp://%s:%s" % (FLAGS.broadcast_listen,
                                        FLAGS.broadcast_listen_port))

        # Socket with direct access to the feedback
        feedback = zmq_context.socket(zmq.PULL)
        feedback.bind("tcp://%s:%s" % (FLAGS.feedback_listen,
                                       FLAGS.feedback_listen_port))

        args = {
                'handler': handler,
                'broadcast': broadcast,
                'feedback': feedback,
        }

        self.pool.spawn(client_routine, **args)
        self.pool.spawn(worker_routine, **args)
        self.pool.spawn(checker_routine, **args)

    def wait(self):
        self.pool.waitall()
