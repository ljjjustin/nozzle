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

"""nozzle flags."""

from nozzle.openstack.common import cfg

default_opts = [
    cfg.StrOpt('auth_strategy',
               default='keystone',
               help='authorize strategy'),
    cfg.StrOpt('api_paste_config',
               default='api-paste.ini',
               help='paste configuration file'),
    cfg.StrOpt('keystone_username',
               default='demo',
               help='Username to access keystone'),
    cfg.StrOpt('keystone_password',
               default='demo',
               help='Password to access keystone'),
    cfg.StrOpt('keystone_tenant_name',
               default='demo',
               help='Tenant name to access keystone'),
    cfg.StrOpt('keystone_auth_url',
               default='http://localhost:5000/v2.0',
               help='URL to access keystone'),
    cfg.StrOpt('server_manager',
               default='nozzle.server.manager.ServerManager',
               help='full class name for server manager'),
    cfg.StrOpt('worker_manager',
               default='nozzle.worker.manager.WorkerManager',
               help='full class name for worker manager')
    ]


api_opts = [
    cfg.StrOpt('api_listen',
               default='127.0.0.1',
               help='IP address for nozzle API to listen.'),
    cfg.IntOpt('api_listen_port',
               default=5556,
               help='Port for nozzle api to listen.'),
    cfg.StrOpt('server_listen',
               default='127.0.0.1',
               help='IP address for nozzle server to listen.'),
    cfg.IntOpt('server_listen_port',
               default=5557,
               help='Port for nozzle server to listen.'),
    cfg.StrOpt('broadcast_listen',
               default='127.0.0.1',
               help='IP address for nozzle worker to listen.'),
    cfg.IntOpt('broadcast_listen_port',
               default=5558,
               help='Port for nozzle worker to listen.'),
    cfg.StrOpt('feedback_listen',
               default='127.0.0.1',
               help='IP address for nozzle API to get response from worker.'),
    cfg.IntOpt('feedback_listen_port',
               default=5559,
               help='Port for nozzle api to get response from worker.'),
    ]


sql_opts = [
    cfg.StrOpt('sql_connection',
               default='mysql://root:nova@127.0.0.1:3306/nozzle',
               help='Database connection'),
    cfg.IntOpt('sql_connection_debug',
               default=0,
               help='Verbosity of SQL debugging info, 0=None, 100=all'),
    cfg.IntOpt('sql_max_retries',
               default=3,
               help='Max retry times when database connection error occur'),
    cfg.StrOpt('reconnect_interval',
               default=3,
               help='Retry interval when database connection error occur'),
    ]

protocol_opts = [
    cfg.ListOpt('tcp_postfixs',
                default=['.elb4.sinasws.com', '.internal.elb4.sinasws.com'],
                help='dns postfix for tcp protocol'),
    cfg.ListOpt('http_postfixs',
                default=['.elb7.sinasws.com', '.internal.elb7.sinasws.com'],
                help='dns postfix for http protocol'),
    ]

FLAGS = cfg.CONF
FLAGS.register_opts(default_opts)
FLAGS.register_opts(api_opts)
FLAGS.register_opts(sql_opts)
FLAGS.register_opts(protocol_opts)
