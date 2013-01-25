import os

from nozzle.openstack.common import cfg
from nozzle.openstack.common import log as logging

from nozzle.common import flags
from nozzle.common import exception
from nozzle.common import validate
from nozzle.common import utils

nginx_opts = [
    cfg.ListOpt('listen',
                default=['127.0.0.1:80'],
                help="List of ip which nginx will listen to"),
    cfg.StrOpt('access_log_dir',
               default='/var/log/nginx/',
               help="Where to store nginx access log."),
    cfg.StrOpt('configuration_backup_dir',
               default='/var/lib/nozzle/backup/nginx',
               help="Where to backup nginx configuration."),
]

FLAGS = flags.FLAGS
FLAGS.register_opts(nginx_opts, 'nginx')

LOG = logging.getLogger(__name__)

_NGX_UPSTREAM_FMT = '''
upstream %(upstream_name)s {
\t%(balancing_method)s ip_hash;
\t%(servers)s
}
'''

_NGX_UPSTREAM_SERVER_FMT = ("\tserver %(ip)s:%(port)s "
                            "max_fails=%(max_fails)s "
                            "fail_timeout=%(fail_timeout)ss;")

_NGX_SERVER_FMT = '''
server {
%(listen)s

       server_name_in_redirect  off;
       server_name %(server_name)s;

       proxy_connect_timeout 4;
       proxy_read_timeout    300;
       proxy_send_timeout    300;

       location / {
              proxy_set_header Host $host;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_pass http://%(proxy_pass)s;
       }

       access_log %(log_path)s sws_proxy_log_fmt;
}
'''


class NginxProxyConfigurer(object):
    """
    Configure nginx
    """

    _bind_ip = []
    listen_field = []
    access_log_dir = None

    def __init__(self, **kwargs):
        ip_port_list = FLAGS.nginx.listen
        validate.is_ipv4_port_list(ip_port_list)

        for ip_port in ip_port_list:
            self._bind_ip.append(ip_port.split(':')[0])

        _listen_field = map(lambda x: ("\tlisten %s;" % str(x)),
                            ip_port_list)
        self.listen_field = '\n'.join(_listen_field)

        self.backup_dir = FLAGS.nginx.configuration_backup_dir
        self.access_log_dir = FLAGS.nginx.access_log_dir
        if not os.path.exists(self.access_log_dir):
            raise exception.DirNotFound(dir=self.access_log_dir)

    @utils.synchronized('nginx')
    def do_config(self, request):
        try:
            self._validate_request(request)
        except exception.BadRequest as e:
            LOG.warn('Bad request: %s' % e)
            raise exception.NginxConfigureError(explanation=str(e))

        cmd = request['cmd']
        msg = request['args']

        if cmd == 'create_lb':
            try:
                self._create_lb(msg)
            except exception.NginxCreateProxyError as e:
                raise exception.NginxConfigureError(explanation=str(e))

        elif cmd == 'delete_lb':
            try:
                self._delete_lb(msg)
            except exception.NginxDeleteProxyError as e:
                raise exception.NginxConfigureError(explanation=str(e))

        elif cmd == 'update_lb':
            try:
                self._update_lb(msg)
            except exception.NginxUpdateProxyError as e:
                raise exception.NginxConfigureError(explanation=str(e))

    def _create_lb(self, msg):
        LOG.debug("Creating the nginx load "
                  "balancer for NAME:%s USER: %s PROJECT:%s" %
                  (msg['uuid'], msg['user_id'], msg['tenant_id']))
        try:
            self._create_http_ngx_cfg(msg)
        except exception.NginxConfFileExists as e:
            LOG.warn('%s', e)
            raise exception.NginxCreateProxyError(explanation=str(e))
        except IOError as e:
            LOG.critical('%s', e)
            raise exception.NginxCreateProxyError(explanation=str(e))

        try:
            self._test_http_ngx_cfg()
        except exception.ProcessExecutionError as e:
            try:
                self._delete_http_ngx_cfg(msg)
            except:
                pass
            raise exception.NginxCreateProxyError(explanation=str(e))

        try:
            self._reload_http_ngx_cfg()
        except exception.ProcessExecutionError as e:
            try:
                self._delete_http_ngx_cfg(msg)
            except:
                pass
            raise exception.NginxCreateProxyError(explanation=str(e))

        LOG.info("Create nginx load balancer successfully")

    def _delete_lb(self, msg):
        LOG.debug("Deleting the nginx load "
                  "balancer for NAME:%s USER: %s PROJECT:%s" %
                  (msg['uuid'], msg['user_id'], msg['tenant_id']))

        try:
            self._delete_http_ngx_cfg(msg)
        except OSError as e:
            raise exception.NginxDeleteProxyError((explanation)=str(e))

        try:
            self._reload_http_ngx_cfg()
        except exception.ProcessExecutionError as e:
            raise exception.NginxDeleteProxyError((explanation)=str(e))

        LOG.info("Delete nginx load balancer successfully")

    def _update_lb(self, msg):
        LOG.debug("Updating the nginx load "
                  "balancer for NAME:%s USER: %s PROJECT:%s" %
                  (msg['uuid'], msg['user_id'], msg['tenant_id']))

        try:
            self._delete_http_ngx_cfg(msg)
        except OSError as e:
            raise exception.NginxUpdateProxyError(explanation=str(e))

        try:
            self._create_lb(msg)
        except exception.NginxCreateProxyError as e:
            raise exception.NginxUpdateProxyError(explanation=str(e))

        LOG.info("Update nginx load balancer successfully")

    def _reload_http_ngx_cfg(self):
        LOG.debug('Reloading nginx')

        try:
            utils.execute('nginx -s reload')
        except exception.ProcessExecutionError as e:
            LOG.warn("Failed to reload nginx  "
                     "nginx master process: %s", e)
            raise

    def _test_http_ngx_cfg(self):
        LOG.debug('Testing the new nginx configuration')
        try:
            utils.execute('nginx -t')
        except exception.ProcessExecutionError as e:
            LOG.warn('Did not pass the new nginx configuration test: %s', e)
            raise

    def _delete_http_ngx_cfg(self, msg):
        confname = self._conf_file_name(msg)
        LOG.debug("Deleting %s and its symbolic link", confname)

        dirname = os.path.dirname('/etc/nginx/sites-enabled/')
        symbol_path = os.path.join(dirname, confname)

        dirname = os.path.dirname('/etc/nginx/sites-available/')
        conf_path = os.path.join(dirname, confname)

        try:
            utils.delete_if_exists(symbol_path)
        except OSError as e:
            LOG.critical('Failed to delete %s: %s' % (symbol_path, e))
            try:
                utils.delete_if_exists(conf_path)
            except OSError as e:
                LOG.critical('Failed to delete %s: %s' % (conf_path, e))
                raise
            raise

        try:
            #utils.delete_if_exists(conf_path)
            utils.backup_config(conf_path, self.backup_dir)
        except OSError as e:
            LOG.critical('Failed to delete %s: %s' % (conf_path, e))
            raise

    def _validate_request(self, request):
        validate.check_http_request(request)

    def _conf_file_name(self, msg):
        # TODO (wenjianhn) valid ln -s cmd
        return self._upstream_name(msg)

    def _upstream_name(self, msg):
        # TODO(wenjianhn): base64 msg['user_id'], msg['tenant_id'],
        # msg['uuid']
        ngx_upstream_name = "%s" % msg['uuid']

        return ngx_upstream_name

    def _create_ngx_upstream_directive(self, upstream_name, msg):
        source_binding = ' '
        round_robin = '#'

        balancing_method = source_binding
        if msg['balancing_method'] != 'source_binding':
            balancing_method = round_robin

        # TODO(wenjinahn): ngx healthy check

        max_fails = 3
        fail_timeout = 10
        server_list = []
        for ip in msg['instance_ips']:
            server_list.append(_NGX_UPSTREAM_SERVER_FMT %
                               {'ip': ip,
                                'port': msg['instance_port'],
                                'max_fails': max_fails,
                                'fail_timeout': fail_timeout})

        return _NGX_UPSTREAM_FMT % {'upstream_name': upstream_name,
                                    'balancing_method': balancing_method,
                                    'servers': '\n'.join(server_list)}

    def _create_ngx_server_directive(self, upstream_name, msg):
        server_name_list = msg['dns_names']
        server_name_list.extend(msg['http_server_names'])
        server_name = ' '.join(server_name_list)
        dirname = os.path.dirname(self.access_log_dir)
        log_path = os.path.join(dirname, upstream_name)

        return _NGX_SERVER_FMT % {'listen': self.listen_field,
                                  'server_name': server_name,
                                  'proxy_pass': upstream_name,
                                  'log_path': log_path}

    def _create_http_ngx_cfg(self, msg):
        cfile_path = "/etc/nginx/sites-available/%s" % \
                     self._conf_file_name(msg)
        if os.path.exists(cfile_path):
            raise exception.NginxConfFileExists(path=cfile_path)

        ngx_cfg = self._create_http_ngx_cfg_buffer(msg)
        LOG.info('Write it into configuration file: %s', cfile_path)
        with open(cfile_path, 'w') as cfile:
            cfile.write(ngx_cfg)

        cmd = "ln -sf %s /etc/nginx/sites-enabled/" % cfile_path
        utils.execute(cmd)

    def _create_http_ngx_cfg_buffer(self, msg):
        ngx_upstream_name = self._upstream_name(msg)

        ngx_upstream_directive = self._create_ngx_upstream_directive(
            ngx_upstream_name, msg)

        ngx_server_directive = self._create_ngx_server_directive(
            ngx_upstream_name, msg)

        ngx_cfg = "%s\n%s\n" % (ngx_upstream_directive, ngx_server_directive)

        LOG.debug("""Created nginx configuration buffer:
                  =====================================
                  %s
                  =====================================
                  """, ngx_cfg)

        return ngx_cfg
