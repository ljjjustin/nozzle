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

import datetime
import functools
import inspect
import lockfile
import os
import random
import shutil
import shlex
import subprocess
import sys
import uuid

from paste import deploy

from novaclient.v1_1 import client

from nozzle.openstack.common import cfg
from nozzle.openstack.common import timeutils
from nozzle.openstack.common import log as logging
from nozzle.common import context
from nozzle.common import exception
from nozzle.common import flags
from nozzle import db

FLAGS = flags.FLAGS
nova_client = None


LOG = logging.getLogger(__name__)


def default_cfgfile(filename='nozzle.conf', args=None):
    if args is None:
        args = sys.argv
    for arg in args:
        if arg.find('config-file') != -1:
            return arg[arg.index('config-file') + len('config-file') + 1:]
    else:
        if not os.path.isabs(filename):
            # turn relative filename into an absolute path
            script_dir = os.path.dirname(inspect.stack()[-1][1])
            filename = os.path.abspath(os.path.join(script_dir, filename))
        if not os.path.exists(filename):
            filename = "./nozzle.conf"
            if not os.path.exists(filename):
                filename = '/etc/nozzle/nozzle.conf'
        if os.path.exists(filename):
            cfgfile = '--config-file=%s' % filename
            args.insert(1, cfgfile)
            return filename


def load_paste_app(app_name):
    """
    Builds and returns a WSGI app from a paste config file.

    :param app_name: Name of the application to load
    :raises RuntimeError when config file cannot be located or
            application cannot be loaded from config file
    """

    config_file = cfg.CONF.find_file(cfg.CONF.api_paste_config)
    config_path = os.path.abspath(config_file)

    try:
        app = deploy.loadapp("config:%s" % config_path, name=app_name)
    except (LookupError, ImportError):
        msg = ("Unable to load %(app_name)s from "
               "configuration file %(config_path)s.") % locals()
        raise RuntimeError(msg)
    return app


def show_configs():
    LOG.debug("*" * 80)
    LOG.debug("Configuration options gathered from config file:")
    LOG.debug("================================================")
    items = dict([(k, v) for k, v in cfg.CONF.items()
                  if k not in ('__file__', 'here')])
    for key, value in sorted(items.items()):
        LOG.debug("%(key)-30s = %(value)s" % {'key': key,
                                              'value': value})
    LOG.debug("*" * 80)


def str_uuid():
    return str(uuid.uuid4())


def utcnow():
    return timeutils.utcnow()


def delete_if_exists(pathname):
    try:
        os.unlink(pathname)
    except OSError as (errno, strerror):
        if errno == 2:  # doesn't exist
            return
        else:
            raise


def backup_config(filepath, backup_dir):
    if not os.path.exists(filepath):
        return

    time_str = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
    dst = os.path.join(backup_dir, time_str)
    try:
        shutil.move(filepath, dst)
    except OSError as (errno, strerror):
        LOG.error('shutil.move(%s, %s) fail: %s' % (filepath, dst, strerror))
        delete_if_exists(filepath)
        raise


def execute(cmd):
    # NOTE(wenjianhn): shlex supports ascii only
    cmd = cmd.encode('ascii')

    try:
        LOG.debug('Running cmd (subprocess): %s', cmd)
        subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        LOG.warning('[%s] failed: %s' % (cmd, e.output))
        raise exception.ProcessExecutionError(exit_code=e.returncode,
                                              output=e.output, cmd=cmd)


def synchronized(name):
    def wrap(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            LOG.debug('Attempting to grab file lock "%(lock)s" for '
                      'method "%(method)s"...' %
                      {'lock': name, 'method': f.__name__})

            lock_file_path = os.path.join('/var/run/nozzle',
                                          'nozzle-worker.%s' % name)

            lock = lockfile.FileLock(lock_file_path, threaded=False)

            with lock:
                LOG.debug('Got file lock "%(lock)s" for '
                          'method "%(method)s"...' %
                          {'lock': name, 'method': f.__name__})
                return f(*args, **kwargs)

        return inner
    return wrap


def check_input_parameters(expect_keys, **kwargs):
    for key in expect_keys:
        if not key in kwargs.keys():
            raise exception.MissingParameter(key=key)


def allocate_listen_port():
    filters = dict({'protocol': 'tcp'})
    ctxt = context.get_admin_context(read_deleted="yes")
    all_lbs = db.load_balancer_get_all(ctxt, filters=filters)

    active_load_balancers = filter(lambda x: not x['deleted'], all_lbs)
    deleted_load_balancers = filter(lambda x: x['deleted'], all_lbs)
    allocated_ports = map(lambda x: x['listen_port'], active_load_balancers)
    available_ports = filter(lambda x: x not in allocated_ports,
                             map(lambda y: y['listen_port'],
                                 deleted_load_balancers))

    if available_ports:
        return available_ports[0]
    elif allocated_ports:
        return max(allocated_ports) + 1
    else:
        return 11000


def check_input_parameters(expect_keys, **kwargs):
    for key in expect_keys:
        if not key in kwargs.keys():
            raise exception.MissingParameter(key=key)


def gen_dns_prefix():
    ctxt = context.get_admin_context(read_deleted="yes")
    all_load_balancers = db.load_balancer_get_all(ctxt)
    all_prefixs = map(lambda x: x['dns_prefix'], all_load_balancers)
    prefix = generate_uid(size=10)
    while prefix in all_prefixs:
        prefix = generate_uid(size=10)
    return prefix


def generate_uid(size=10):
    characters = '01234567890abcdefghijklmnopqrstuvwxyz'
    choices = [random.choice(characters) for _x in xrange(size)]
    return ''.join(choices)


def get_all_domain_names():
    ctxt = context.get_admin_context()
    all_domains = db.load_balancer_domain_get_all(ctxt)
    all_http_servers = map(lambda x: x['name'], all_domains)
    return all_http_servers


def get_all_load_balancers(filters=None):
    ctxt = context.get_admin_context()
    all_load_balancers = db.load_balancer_get_all(ctxt, filters=filters)
    return all_load_balancers


def get_fixed_ip_by_instance_uuid(uuid):
    global nova_client
    if nova_client is None:
        nova_client = client.Client(FLAGS.nova_admin_username,
                                    FLAGS.nova_admin_password,
                                    FLAGS.nova_admin_tenant_name,
                                    FLAGS.nova_admin_auth_url,
                                    region_name=FLAGS.nova_region_name,
                                    service_type="compute",
                                    no_cache=True)
    instance = nova_client.servers.get(uuid)
    for ip_group, addresses in instance.addresses.items():
        for address in addresses:
            return address['addr']
    raise Exception('failed to ip address of instance: %s' % uuid)
