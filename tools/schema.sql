DROP TABLE IF EXISTS `load_balancer_instance_association`;
DROP TABLE IF EXISTS `load_balancer_domains`;
DROP TABLE IF EXISTS `load_balancer_configs`;
DROP TABLE IF EXISTS `load_balancers`;

CREATE TABLE `load_balancers` (
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted` tinyint(1)  DEFAULT NULL,
  `id` varchar(36) NOT NULL,
  `user_id` varchar(255) NOT NULL,
  `tenant_id` varchar(255) NOT NULL,
  `free` tinyint(1)  DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `state` varchar(16) NOT NULL,
  `protocol` varchar(16) DEFAULT NULL,
  `dns_prefix` varchar(255) NOT NULL,
  `listen_port` int(11) DEFAULT NULL,
  `instance_port` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `load_balancer_configs` (
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted` tinyint(1)  DEFAULT NULL,
  `id` varchar(36) NOT NULL,
  `load_balancer_id` varchar(36) NOT NULL,
  `balancing_method` varchar(255) DEFAULT NULL,
  `health_check_timeout_ms` int(11) DEFAULT NULL,
  `health_check_interval_ms` int(11) DEFAULT NULL,
  `health_check_target_path` varchar(255) DEFAULT NULL,
  `health_check_unhealthy_threshold` int(11) DEFAULT NULL,
  `health_check_healthy_threshold` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
 
CREATE TABLE `load_balancer_domains` (
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted` tinyint(1)  DEFAULT NULL,
  `id` varchar(36) NOT NULL,
  `name` varchar(255) NOT NULL,
  `load_balancer_id` varchar(36) NOT NULL,
  KEY (`load_balancer_id`),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
 
CREATE TABLE `load_balancer_instance_association` (
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted` tinyint(1)  DEFAULT NULL,
  `instance_ip` varchar(64) NOT NULL,
  `instance_uuid` varchar(36) NOT NULL,
  `load_balancer_id` varchar(36) NOT NULL,
  PRIMARY KEY (`load_balancer_id`, `instance_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
