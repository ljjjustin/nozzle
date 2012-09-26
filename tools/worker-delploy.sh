#!/bin/bash

# config nginx
touch /etc/nginx/conf.d/sws-log-format.conf
(cat <<EOF
log_format sws_proxy_log_fmt '\$remote_addr - \$remote_user [\$time_local] '
                             '"\$request" \$status \$body_bytes_sent '
                             '"\$http_referer" "\$http_user_agent" "\$request_time"';
EOF
) > /etc/nginx/conf.d/sws-log-format.conf
# restart nginx
/etc/init.d/nginx restart

# config haproxy
DATA=$(date +"%Y-%m-%d-%H-%M-%S")
mv /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy-$DATA.cfg
(cat <<EOF
global
	log 127.0.0.1   local0 info
	log 127.0.0.1   local1 notice
	#log loghost    local0 info
	maxconn 4096
	#chroot /usr/share/haproxy
	user haproxy
	group haproxy
	daemon
	#debug
	#quiet

defaults
	log global
	mode tcp
	option tcplog
	option dontlognull
	option redispatch
	retries 3
	maxconn 2000
	contimeout 6000
	clitimeout 600000
	srvtimeout 600000

listen admin_stats 0.0.0.0:1024
	mode http
	option httpchk
	option httplog
	option dontlognull
	balance roundrobin
	stats uri /stats
	stats auth admin:nova

EOF
) > /etc/haproxy/haproxy.cfg
# restart haproxy
sed -i -e "s/^ENABLED=.*/ENABLED=1/" /etc/default/haproxy
/etc/init.d/haproxy restart
