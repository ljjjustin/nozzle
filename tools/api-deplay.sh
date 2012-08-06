#!/bin/bash

PWD=$(pwd)
TOPDIR=$(dirname $PWD)

mkdir -p /etc/nozzle
mkdir -p /var/log/nozzle

cp $TOPDIR/etc/nozzle/api-paste.ini.sample /etc/nozzle/api-paste.ini
cp $TOPDIR/etc/nozzle/nozzle.conf.sample /etc/nozzle/nozzle.conf

## create database and tables.
PASSWORD="nova"
DATABASE="nozzle"
MYSQL="mysql -uroot -p${PASSWORD}"
$MYSQL -e "CREATE DATABASE IF NOT EXISTS $DATABASE"
$MYSQL $DATABASE < $PWD/schema.sql
