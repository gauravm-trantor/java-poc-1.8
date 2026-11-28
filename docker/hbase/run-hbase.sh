#!/bin/sh
# Start HBase in this one container: its own ZooKeeper and the master as daemons, the region server in the
# foreground (so the container lives as long as the region server does). No ssh is needed, unlike
# HBase's own start-hbase.sh in distributed mode.
set -e
hbase-daemon.sh start zookeeper
hbase-daemon.sh start master
exec hbase regionserver start
