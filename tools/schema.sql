CREATE TABLE `load_balancers` (
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted` tinyint(1)  DEFAULT NULL,
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `user_id` varchar(255) NOT NULL,
  `project_id` varchar(255) NOT NULL,
  `uuid` varchar(36) NOT NULL,
  `free` tinyint(1)  DEFAULT NULL,
  `protocol` varchar(255) DEFAULT NULL,
  `state` varchar(255) NOT NULL,
  `dns_prefix` varchar(255) NOT NULL,
  `listen_port` int(11) DEFAULT NULL,
  `instance_port` int(11) DEFAULT NULL,
  KEY (`uuid`),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `load_balancer_configs` (
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted` tinyint(1)  DEFAULT NULL,
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `load_balancer_id` int(11) NOT NULL,
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
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `load_balancer_id` int(11) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  KEY (`load_balancer_id`),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
 
CREATE TABLE `load_balancer_instance_association` (
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted` tinyint(1)  DEFAULT NULL,
  `load_balancer_id` int(11) NOT NULL,
  `instance_uuid` varchar(36) NOT NULL,
  PRIMARY KEY (`load_balancer_id`, `instance_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
