#!/bin/bash

PWD=$(cd $(dirname $0) && pwd)
TOPDIR=$(dirname $PWD)

# Grab a numbered field from python prettytable output
# Fields are numbered starting with 1
# Reverse syntax is supported: -1 is the last field, -2 is second to last, etc.
# get_field field-number
function get_field() {
    while read data; do
        if [ "$1" -lt 0 ]; then
            field="(\$(NF$1))"
        else
            field="\$$(($1 + 1))"
        fi
        echo "$data" | awk -F'[ \t]*\\|[ \t]*' "{print $field}"
    done
}

mkdir -p /etc/nozzle
mkdir -p /var/log/nozzle

cp $TOPDIR/etc/nozzle/api-paste.ini.sample /etc/nozzle/api-paste.ini
cp $TOPDIR/etc/nozzle/nozzle.conf.sample /etc/nozzle/nozzle.conf

## create database and tables.
PASSWORD="nova"
DATABASE="nozzle"
MYSQL="mysql -uroot -p${PASSWORD}"
$MYSQL -e "DROP DATABASE IF EXISTS $DATABASE;"
$MYSQL -e "CREATE DATABASE $DATABASE CHARACTER SET utf8;"
$MYSQL $DATABASE < $PWD/schema.sql

## add load balance into service catalog
source nozzlerc
sed -i -e '/loadbalance/d' /etc/keystone/default_catalog.templates

(cat <<EOF

catalog.RegionOne.loadbalance.publicURL = http://localhost:5556/v1.0
catalog.RegionOne.loadbalance.adminURL = http://localhost:5556/v1.0
catalog.RegionOne.loadbalance.internalURL = http://localhost:5556/v1.0
catalog.RegionOne.loadbalance.name = Load Balance Service
EOF
) >> /etc/keystone/default_catalog.templates

## create keystone user
TENANT_ID=$(keystone tenant-list | grep " service " | get_field 1)
USER_ID=$(keystone user-list | grep " nozzle " | get_field 1)

if [ "$USER_ID" != "" ]
then
    keystone user-delete $USER_ID 
fi

keystone user-create --tenant_id $TENANT_ID --name nozzle --pass nova --email nozzle@example.com

USER_ID=$(keystone user-list | grep " nozzle " | get_field 1)
ROLE_ID=$(keystone role-list | grep " admin " | get_field 1)

keystone user-role-add --user_id $USER_ID --role_id $ROLE_ID --tenant_id $TENANT_ID
