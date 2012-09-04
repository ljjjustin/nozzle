import logging
import os
import time

from nozzle.openstack.common import cfg
from nozzle.common import flags
from nozzle.common import exception
from nozzle.common import validate
from nozzle.common import utils

haproxy_opts = [
    cfg.ListOpt('listen',
                default=[],
                help="List of ip which haproxy will listen to"),
    cfg.StrOpt('listen_port_range',
               default='10000,61000',
               help="Port range haproxy need to listen."),
    cfg.StrOpt('configuration_backup_dir',
               default='/tmp/',
               help="Directory for backup haproxy configuration"),
]

FLAGS = flags.FLAGS
FLAGS.register_opts(haproxy_opts, 'haproxy')

LOG = logging.getLogger(__name__)


class HaproxyConfigurer(object):

    """
    Configure haproxy
    """

    _bind_ip = []
    listen_port_min = None
    listen_port_max = None

    cfg_backup_dir = None

    def __init__(self, **kwargs):
        for ip in FLAGS.haproxy.listen:
            if validate.is_ipv4(ip):
                self._bind_ip.append(ip)
        ##print self._bind_ip
        listen_port_range = FLAGS.haproxy.listen_port_range.split(',')
        self.listen_port_min = int(listen_port_range[0])
        self.listen_port_max = int(listen_port_range[1])

        self.cfg_backup_dir = FLAGS.haproxy.configuration_backup_dir

        if not os.path.exists(self.cfg_backup_dir):
            strerror = ("configuration_backup_dir(dir=%s) does not exist" %
                        self.cfg_backup_dir)
            LOG.error(strerror)
            raise Exception(strerror)

    @utils.synchronized('haproxy')
    def do_config(self, request):
        try:
            self._validate_request(request)
        except exception.BadRequest as e:
            LOG.warn('Bad request: %s' % e)
            raise exception.HaproxyConfigureError(explanation=str(e))

        cmd = request['cmd']
        msg = request['msg']

        if cmd == 'create_lb':
            try:
                self._create_lb(msg)
            except exception.HaproxyCreateError as e:
                raise exception.HaproxyConfigureError(explanation=str(e))

        elif cmd == 'delete_lb':
            try:
                self._delete_lb(msg)
            except exception.HaproxyDeleteError as e:
                raise exception.HaproxyConfigureError(explanation=str(e))

        elif cmd == 'update_lb':
            try:
                self._update_lb(msg)
            except exception.HaproxyUpdateError as e:
                raise exception.HaproxyConfigureError(explanation=str(e))

    def _create_lb(self, msg):
        LOG.debug("Creating the haproxy load "
                  "balancer for NAME:%s USER: %s PROJECT:%s" %
                  (msg['uuid'], msg['user_id'], msg['tenant_id']))

        try:
            new_cfg_path = self._create_lb_haproxy_cfg(msg)
        except exception.HaproxyCreateCfgError as e:
            raise exception.HaproxyCreateError(explanation=str(e))

        try:
            self._test_haproxy_config(new_cfg_path)
        except exception.ProcessExecutionError as e:
            raise exception.HaproxyCreateError(explanation=str(e))

        rc, backup_path = self._backup_original_cfg()
        if rc != 0:
            raise exception.HaproxyCreateError(explanation=backup_path)

        rc, strerror = self._replace_original_cfg_with_new(new_cfg_path)
        if rc != 0:
            raise exception.HaproxyCreateError(explanation=strerror)

        if self._reload_haproxy_cfg(backup_path) != 0:
            e = 'Failed to reload haproxy'
            raise exception.HaproxyCreateError(explanation=e)

        LOG.debug("Created the new load balancer successfully")

    def _delete_lb(self, msg):
        LOG.debug("Deleting the haproxy load "
                  "balancer for NAME:%s USER: %s PROJECT:%s" %
                  (msg['uuid'], msg['user_id'], msg['tenant_id']))
        try:
            new_cfg_path = self._create_lb_deleted_haproxy_cfg(msg)
        except exception.HaproxyLBNotExists as e:
            LOG.warn('%s', e)
            return
            ##raise exception.HaproxyDeleteError(explanation=str(e))

        try:
            self._test_haproxy_config(new_cfg_path)
        except exception.ProcessExecutionError as e:
            raise exception.HaproxyDeleteError(explanation=str(e))

        rc, backup_path = self._backup_original_cfg()
        if rc != 0:
            raise exception.HaproxyDeleteError(explanation=backup_path)

        rc, strerror = self._replace_original_cfg_with_new(new_cfg_path)
        if rc != 0:
            raise exception.HaproxyDeleteError(explanation=strerror)

        if self._reload_haproxy_cfg(backup_path) != 0:
            e = 'Failed to reload haproxy'
            raise exception.HaproxyDeleteError(explanation=str(e))

        LOG.debug("Deleted the new load balancer successfully")

    def _update_lb(self, msg):
        LOG.debug("Updating the haproxy load "
                  "balancer for NAME:%s USER: %s PROJECT:%s" %
                  (msg['uuid'], msg['user_id'], msg['tenant_id']))

        try:
            lb_deleted_cfg_path = self._create_lb_deleted_haproxy_cfg(msg)
        except exception.HaproxyLBNotExists as e:
            LOG.warn('%s', e)
            raise exception.HaproxyUpdateError(explanation=str(e))

        try:
            new_cfg_path = self._create_lb_haproxy_cfg(msg,
                                        base_cfg_path=lb_deleted_cfg_path)
        except exception.HaproxyCreateCfgError as e:
            raise exception.HaproxyUpdateError(explanation=str(e))

        try:
            self._test_haproxy_config(new_cfg_path)
        except exception.ProcessExecutionError as e:
            raise exception.HaproxyUpdateError(explanation=str(e))

        rc, backup_path = self._backup_original_cfg()
        if rc != 0:
            raise exception.HaproxyUpdateError(explanation=backup_path)

        rc, strerror = self._replace_original_cfg_with_new(new_cfg_path)
        if rc != 0:
            raise exception.HaproxyUpdateError(explanation=strerror)

        if self._reload_haproxy_cfg(backup_path) != 0:
            e = 'Failed to reload haproxy'
            raise exception.HaproxyUpdateError(explanation=str(e))

        LOG.debug("Updated the new load balancer successfully")

    def _validate_request(self, request):
        validate.check_tcp_request(request)

    def _get_lb_name(self, msg):
        # TODO(wenjianhn): utf-8 support, base64
        return "%s_%s" % (msg['tenant_id'],
                          msg['uuid'])

    def _create_haproxy_lb_server_directive(self, msg):
        servers = []

        _HAPROXY_LB_SERVER_FMT = \
        '\tserver %s %s:%s check inter %sms rise %s fall %s'

        n = len(msg['instance_uuids'])
        for i in range(n):
            servers.append(_HAPROXY_LB_SERVER_FMT %
                           (msg['instance_uuids'][i],
                            msg['instance_ips'][i],
                            msg['instance_port'],
                            msg['health_check_interval_ms'],
                            msg['health_check_healthy_threshold'],
                            msg['health_check_unhealthy_threshold']))

        return '\n'.join(servers)

    def _backup_original_cfg(self):
        now = time.asctime().replace(' ', '_')
        backup_filename = 'haproxy.cfg_' + now

        backup_path = os.path.join(self.cfg_backup_dir, backup_filename)
        cmd = "cp /etc/haproxy/haproxy.cfg %s" % backup_path

        try:
            utils.execute(cmd)
        except exception.ProcessExecutionError as e:
            LOG.error("Failed to make a backup configuration")
            return -1, str(e)

        return 0, backup_path

    def _replace_original_cfg_with_new(self, new_cfg_path):
        cmd = "cp %s /etc/haproxy/haproxy.cfg" % new_cfg_path
        try:
            utils.execute(cmd)
        except exception.ProcessExecutionError as e:
            LOG.error("Failed to replace the orignal configuration")
            return -1, str(e)

        return 0, None

    def _create_lb_haproxy_cfg(self, msg,
                               base_cfg_path='/etc/haproxy/haproxy.cfg'):
        try:
            haproxy_new_proxy_cfg = self._create_haproxy_listen_cfg(msg,
                                                            base_cfg_path)
        except exception.HaproxyLBExists as e:
            LOG.warn('%s', e)
            raise exception.HaproxyCreateCfgError(explanation=str(e))

        new_cfg_path = '/etc/haproxy/haproxy.cfg.sws-lb-worker.new'
        cmd = 'cp %s %s' % (base_cfg_path, new_cfg_path)
        try:
            utils.execute(cmd)
        except exception.ProcessExecutionError as e:
            LOG.error("Failed to copy original configuration: %s", e)
            raise exception.HaproxyCreateCfgError(explanation=str(e))

        try:
            with open(new_cfg_path, 'a') as cfile:
                cfile.write(haproxy_new_proxy_cfg)
        except IOError as e:
            LOG.error("Failed to open %s: %s" % (new_cfg_path, e))
            raise exception.HaproxyCreateCfgError(explanation=str(e))

        return new_cfg_path

    def _create_haproxy_listen_cfg(self, msg,
                                   base_cfg_path='/etc/haproxy/haproxy.cfg'):
        lb_name = self._get_lb_name(msg)

        if self._is_lb_in_use(lb_name, base_cfg_path):
            raise exception.HaproxyLBExists(name=lb_name)

        listen_port = int(msg['listen_port'])
        if listen_port < self.listen_port_min or \
           listen_port > self.listen_port_max:
            warn_msg = 'Valid listen port(%s) should between %s and %s' % (
                listen_port, self.listen_port_min, self.listen_port_max)
            LOG.error(warn_msg)
            raise exception.HaproxyCreateError(explanation=warn_msg)

        if msg['balancing_method'] == 'round_robin':
            balancing_method = 'roundrobin'
        else:
            balancing_method = 'source'
        LOG.info("selft._bind_ip = %s" % self._bind_ip)

        server_directives = self._create_haproxy_lb_server_directive(msg)

        bind_directive = ','.join(map(lambda ip: "%s:%s" % (ip, listen_port),
                                      self._bind_ip))

        _HAPROXY_LB_FMT = \
            '\nlisten\t%s\n\tmode tcp\n\tbind %s\n\tbalance %s\n\ttimeout check %sms\n%s'

        config = _HAPROXY_LB_FMT % (lb_name,
                                    bind_directive,
                                    balancing_method,
                                    msg['health_check_timeout_ms'],
                                    server_directives)

        LOG.debug("""Created new haproxy listen configuration:
                  =====================================
                  %s
                  =====================================
                  """, config)

        return config

    def _create_lb_deleted_haproxy_cfg(self, msg):
        lb_name = self._get_lb_name(msg)

        # TODO(wenjianhn): handle exception
        if not self._is_lb_in_use(lb_name):
            raise exception.HaproxyLBNotExists(name=lb_name)

        config = self._format_haproxy_config()

        cfg_body = config['body']
        self._del_one_lb_info(cfg_body, lb_name)

        body_lines = []
        for k, v in cfg_body.iteritems():
            body_lines.append("%s%s" % (k, ''.join(v)))

        new_config = "%s%s" % (''.join(config['header']),
                               '\n'.join(body_lines))

        new_cfg_path = '/etc/haproxy/haproxy.cfg.sws-lb-worker.new.lb_deleted'
        try:
            with open(new_cfg_path, 'w') as cfile:
                cfile.write(new_config)
        except IOError as e:
            LOG.error("Failed to open %s: %s" % (new_cfg_path, e))
            raise exception.HaproxyCreateCfgError(explanation=str(e))

        return new_cfg_path

    def _is_lb_in_use(self, lb_name,
                      base_cfg_path='/etc/haproxy/haproxy.cfg'):
        with open(base_cfg_path) as cfg:
            lines = cfg.readlines()

        try:
            in_use_lb_name = [line.split()[1] for line in lines
                              if line.startswith('listen')]
        except IndexError:
            LOG.error("No item was found after listen directive,"
                         "is the haproxy configuraion file valid?")
            raise

        return lb_name in in_use_lb_name

    def _get_haproxy_pid(self):
        try:
            with open('/var/run/haproxy.pid') as pidfile:
                pid = int(pidfile.read())
        except IOError:
            LOG.error("Can not read the haproxy pid file")
            raise
        except ValueError:
            LOG.error("The pid in the haproxy pid file is not an integer")
            raise
        return pid

    def _test_haproxy_config(self, cfile_path):
        LOG.info('Testing the new haproxy configuration file')
        cmd = "haproxy -c -f %s" % cfile_path

        try:
            utils.execute(cmd)
        except exception.ProcessExecutionError as e:
            LOG.warn('Did not pass the new haproxy configuration test: %s', e)
            raise

    def _reload_haproxy_cfg(self, backup_path):
        LOG.debug("Reloading haproxy")
        try:
            pid = self._get_haproxy_pid()
        except IOError:
            return -1
        except ValueError:
            return -1

        cmd = ("haproxy -f /etc/haproxy/haproxy.cfg -p "
               "/var/run/haproxy.pid -sf %s " % pid)

        try:
            utils.execute(cmd)
        except exception.ProcessExecutionError as e:
            LOG.error("Failed to reload haproxy(pid=%s): %s", pid, e)

            LOG.debug('Try to rollback the configuration')
            cmd = "cp %s /etc/haproxy/haproxy.cfg" % backup_path
            try:
                utils.execute(cmd)
            except exception.ProcessExecutionError as e:
                LOG.error('Failed to rollback the configuration')
                return -1

            LOG.debug('Try to load the original configration')
            cmd = ("haproxy -f /etc/haproxy/haproxy.cfg -p "
                   "/var/run/haproxy.pid -sf %s " % pid)
            try:
                utils.execute(cmd)
            except exception.ProcessExecutionError as e:
                LOG.error('Failed to load original configuration')
                return -1

        LOG.debug("Reloaded haproxy successfully")
        return 0

    def _format_haproxy_config(self):
        # TODO(wenjianhn): handle exception
        with open("/etc/haproxy/haproxy.cfg") as cfg_file:
            line_all = cfg_file.readlines()

        cfg_file_buff = {}
        cfg_header = []         # global, defaults
        cfg_body = {}           # listen

        line_total = len(line_all)

        index = 0
        for i in range(0, line_total):
            if line_all[i].startswith('listen'):
                index = i
                break
            cfg_header.append(line_all[i])

        while True:
            key = line_all[index]
            index, cfg_body[key] = self._get_one_lb_info(line_all,
                                                         index + 1,
                                                         line_total)
            if index == line_total - 1:
                break

        cfg_file_buff['header'] = cfg_header
        cfg_file_buff['body'] = cfg_body

        return cfg_file_buff

    def _get_one_lb_info(self, line_all, line_index, line_total):
        value = []

        for i in range(line_index, line_total):
            line = line_all[i]

            if line.startswith('\t'):
                value.append(line)
            elif line.startswith('listen'):
                return i, value

        return line_total - 1, value

    def _del_one_lb_info(self, cfg_body, lb_name):
        del_key = None
        for key in cfg_body:
            if key.startswith('listen'):
                if key.split()[1] == lb_name:
                    del_key = key
                    break
        del cfg_body[key]
