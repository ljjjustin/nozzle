import unittest
import copy
import mock
import os
import subprocess

from nozzle.common import exception
from nozzle.common import utils
from nozzle.worker.driver import nginx

_msg = {
    u'user_id': u'test',
    u'tenant_id': u'test',
    u'uuid': u'testLB',
    u'protocol': u'http',
    u'instance_port': 80,
    u'listen_port': 80,
    u'health_check_timeout_ms': 5,
    u'balancing_method': u'source_binding',
    u'health_check_unhealthy_threshold': 0,
    u'health_check_healthy_threshold': 0,
    u'health_check_interval_ms': 500,
    u'health_check_fail_count': 2,
    u'health_check_target_path': u'/',
    u'http_server_names': [u"g.cn", u't.cn'],
    u'instance_ips': [u'10.0.0.1'],
    u'dns_names': [u'abc.lb.com.cn', u'abc.interal.lb.com.cn'],
}


_request_template = {u'args': _msg,
                     u'cmd': u'create_lb'}


def return_create_lb_request():
    return copy.deepcopy(_request_template)


def return_update_lb_request():
    update_lb_requet = copy.deepcopy(_request_template)
    update_lb_requet[u'cmd'] = u'update_lb'
    return update_lb_requet


def return_delete_lb_request():
    delete_lb_requet = copy.deepcopy(_request_template)
    delete_lb_requet[u'cmd'] = u'delete_lb'
    return delete_lb_requet


class TestConfigureNginx(unittest.TestCase):

    def setUp(self):
        super(TestConfigureNginx, self).setUp()
        self.manager = nginx.NginxProxyConfigurer()
        self.requests = {'create_lb': return_create_lb_request(),
                         'update_lb': return_update_lb_request(),
                         'delete_lb': return_delete_lb_request()}

    @mock.patch('lockfile.FileLock', mock.MagicMock())
    def test_do_config(self):
        self.manager._validate_request = mock.MagicMock()
        self.manager._create_lb = mock.MagicMock()
        self.manager._update_lb = mock.MagicMock()
        self.manager._delete_lb = mock.MagicMock()

        for method in self.requests:
            self.manager.do_config(self.requests[method])
            self.manager._validate_request.assert_called_with(
                self.requests[method])

        self.manager._create_lb.assert_called_once_with(
            self.requests['create_lb']['args'])
        self.manager._update_lb.assert_called_once_with(
            self.requests['update_lb']['args'])
        self.manager._create_lb.assert_called_once_with(
            self.requests['delete_lb']['args'])

    @mock.patch('lockfile.FileLock', mock.MagicMock())
    def test_do_config_with_bad_request(self):
        self.manager._validate_request = \
                        mock.MagicMock(side_effect=exception.BadRequest)

        for method in self.requests:
            self.assertRaises(exception.NginxConfigureError,
                                self.manager.do_config, self.requests[method])

    def test_reload_http_ngx_cfg(self):
        utils.execute = mock.MagicMock()

        self.manager._reload_http_ngx_cfg()

        utils.execute.assert_called_once_with('nginx -s reload')

    def test_reload_http_ngx_cfg_with_exec_failed(self):
        utils.execute = mock.MagicMock(
            side_effect=exception.ProcessExecutionError)

        self.assertRaises(exception.ProcessExecutionError,
                          self.manager._reload_http_ngx_cfg)

    def test_delete_http_ngx_cfg(self):
        args = self.requests['delete_lb']['args']
        confname = self.manager._conf_file_name(args)
        utils.delete_if_exists = mock.MagicMock()
        utils.backup_config = mock.MagicMock()

        self.manager._delete_http_ngx_cfg(args)

        utils.delete_if_exists.assert_called_once_with(
            '/etc/nginx/sites-enabled/%s' % confname)
        utils.backup_config.assert_called_once_with(
            '/etc/nginx/sites-available/%s' % confname,
            self.manager.backup_dir)

    def test_create_ngx_upstream_directive(self):
        args = self.requests['create_lb']['args']
        args['instance_ips'] = ['10.0.0.1', '10.10.0.2', '10.10.0.3']
        ngx_upstream_name = self.manager._upstream_name(args)

        expected = '''
upstream %s {
\t  ip_hash;
\t\tserver 10.0.0.1:80 max_fails=3 fail_timeout=10s;
\tserver 10.10.0.2:80 max_fails=3 fail_timeout=10s;
\tserver 10.10.0.3:80 max_fails=3 fail_timeout=10s;
}
''' % ngx_upstream_name

        upstream_directive = self.manager._create_ngx_upstream_directive(
            ngx_upstream_name,
            args)

        self.assertEquals(upstream_directive, expected)

    def test_create_ngx_server_directive(self):
        args = self.requests['create_lb']['args']
        ngx_upstream_name = self.manager._upstream_name(args)

        dirname = os.path.dirname(self.manager.access_log_dir)
        log_path = os.path.join(dirname, ngx_upstream_name)

        expected = '''
server {
%s

       server_name_in_redirect  off;
       server_name abc.lb.com.cn abc.interal.lb.com.cn g.cn t.cn;

       proxy_connect_timeout 4;
       proxy_read_timeout    300;
       proxy_send_timeout    300;

       location / {
              proxy_set_header Host $host;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_pass http://%s;
       }

       access_log %s sws_proxy_log_fmt;
}
''' % (self.manager.listen_field,
       ngx_upstream_name,
       log_path)

        server_directive = self.manager._create_ngx_server_directive(
            ngx_upstream_name, args)

        self.assertEquals(server_directive, expected)

    def test_create_lb(self):
        args = self.requests['create_lb']['args']
        self.manager._create_http_ngx_cfg = mock.MagicMock()
        self.manager._test_http_ngx_cfg = mock.MagicMock()
        self.manager._reload_http_ngx_cfg = mock.MagicMock()

        self.manager._create_lb(args)

        self.manager._create_http_ngx_cfg.assert_called_once_with(args)
        self.manager._test_http_ngx_cfg.assert_called_once_with()
        self.manager._reload_http_ngx_cfg.assert_called_once_with()

        # TODO(wenjianhn) clean created configuration

    def test_create_lb_with_conffile_exists(self):
        args = self.requests['create_lb']['args']

        self.manager._create_http_ngx_cfg = mock.MagicMock(
            side_effect=exception.NginxConfFileExists)

        self.assertRaises(exception.NginxCreateProxyError,
                          self.manager._create_lb, args)

    def test_create_lb_with_ioerror(self):
        args = self.requests['create_lb']['args']

        self.manager._create_http_ngx_cfg = mock.MagicMock(
            side_effect=IOError)

        self.assertRaises(exception.NginxCreateProxyError,
                          self.manager._create_lb, args)

    def test_create_lb_with_test_ngx_cfg_failed(self):
        args = self.requests['create_lb']['args']
        self.manager._create_http_ngx_cfg = mock.MagicMock()
        self.manager._delete_http_ngx_cfg = mock.MagicMock()
        self.manager._test_http_ngx_cfg = mock.MagicMock(
            side_effect=exception.ProcessExecutionError)

        self.assertRaises(exception.NginxCreateProxyError,
                          self.manager._create_lb, args)

        self.manager._create_http_ngx_cfg.assert_called_once_with(args)
        self.manager._test_http_ngx_cfg.assert_called_once_with()
        self.manager._delete_http_ngx_cfg.assert_called_once_with(args)

    def test_create_lb_with_reload_ngx_cfg_failed(self):
        args = self.requests['create_lb']['args']

        self.manager._create_http_ngx_cfg = mock.MagicMock()
        self.manager._delete_http_ngx_cfg = mock.MagicMock()
        self.manager._test_http_ngx_cfg = mock.MagicMock()

        self.manager._reload_http_ngx_cfg = mock.MagicMock(
            side_effect=exception.ProcessExecutionError)

        self.assertRaises(exception.NginxCreateProxyError,
                          self.manager._create_lb, args)

        self.manager._create_http_ngx_cfg.assert_called_once_with(args)
        self.manager._test_http_ngx_cfg.assert_called_once_with()
        self.manager._reload_http_ngx_cfg.assert_called_once_with()
        self.manager._delete_http_ngx_cfg.assert_called_once_with(args)

    def test_delete_lb(self):
        args = self.requests['delete_lb']['args']

        self.manager._delete_http_ngx_cfg = mock.MagicMock()
        self.manager._reload_http_ngx_cfg = mock.MagicMock()

        self.manager._delete_lb(args)

        self.manager._delete_http_ngx_cfg.assert_called_once_with(args)
        self.manager._reload_http_ngx_cfg.assert_called_once_with()

    def test_delete_lb_with_delete_http_ngx_cfg_failed(self):
        args = self.requests['delete_lb']['args']

        self.manager._delete_http_ngx_cfg = mock.MagicMock(
            side_effect=OSError)

        self.assertRaises(exception.NginxDeleteProxyError,
                          self.manager._delete_lb, args)

    def test_delete_lb_with_reload_http_ngx_cfg_failed(self):
        args = self.requests['delete_lb']['args']

        self.manager._delete_http_ngx_cfg = mock.MagicMock()
        self.manager._reload_http_ngx_cfg = mock.MagicMock(
            side_effect=exception.ProcessExecutionError)

        self.assertRaises(exception.NginxDeleteProxyError,
                          self.manager._delete_lb, args)

        self.manager._delete_http_ngx_cfg.assert_called_with(args)

    def test_update_lb(self):
        args = self.requests['update_lb']['args']

        self.manager._delete_http_ngx_cfg = mock.MagicMock()
        self.manager._create_lb = mock.MagicMock()

        self.manager._update_lb(args)

        self.manager._delete_http_ngx_cfg.assert_called_with(args)
        self.manager._create_lb.assert_called_with(args)

    def test_update_lb_with_delete_ngx_cfg_failed(self):
        args = self.requests['update_lb']['args']

        self.manager._delete_http_ngx_cfg = mock.MagicMock(
            side_effect=OSError)

        self.manager._create_lb = mock.MagicMock()

        self.assertRaises(exception.NginxUpdateProxyError,
                          self.manager._update_lb, args)

    def test_update_lb_with_create_lb_failed(self):
        args = self.requests['update_lb']['args']

        self.manager._delete_http_ngx_cfg = mock.MagicMock()
        self.manager._create_lb = mock.MagicMock(
            side_effect=exception.NginxCreateProxyError)

        self.assertRaises(exception.NginxUpdateProxyError,
                          self.manager._update_lb, args)

        self.manager._delete_http_ngx_cfg.assert_called_with(args)

    @mock.patch('os.path.exists', mock.MagicMock(return_value=False))
    @mock.patch('__builtin__.open', mock.MagicMock())
    def test_create_http_ngx_cfg(self):
        args = self.requests['create_lb']['args']

        self.manager._create_ngx_upstream_directive = mock.MagicMock()
        self.manager._create_ngx_server_directive = mock.MagicMock()

        utils.execute = mock.MagicMock()

        self.manager._create_http_ngx_cfg(args)

        self.assertTrue(self.manager._create_ngx_upstream_directive.called)
        self.assertTrue(self.manager._create_ngx_server_directive.called)
        self.assertTrue(open.called)
        self.assertTrue(utils.execute)

    @mock.patch('os.path.exists', mock.MagicMock(return_value=True))
    def test_create_http_ngx_cfg_with_file_exists(self):
        args = self.requests['create_lb']['args']
        self.assertRaises(exception.NginxConfFileExists,
                          self.manager._create_http_ngx_cfg, args)

    @mock.patch('os.path.exists', mock.MagicMock(return_value=False))
    @mock.patch('__builtin__.open', mock.MagicMock(side_effect=IOError))
    def test_create_http_ngx_cfg_with_open_error(self):
        args = self.requests['create_lb']['args']

        self.assertRaises(IOError, self.manager._create_http_ngx_cfg, args)

    @mock.patch('os.path.exists', mock.MagicMock(return_value=False))
    @mock.patch('__builtin__.open', mock.MagicMock())
    def test_create_http_ngx_cfg_with_mk_soft_link(self):
        args = self.requests['create_lb']['args']

        utils.execute = mock.MagicMock(
            side_effect=exception.ProcessExecutionError)

        self.assertRaises(exception.ProcessExecutionError,
                          self.manager._create_http_ngx_cfg, args)

if __name__ == '__main__':
    unittest.main()
