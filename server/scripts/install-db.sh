#!/bin/bash
# One-shot: create the four databases, load the TBC world DB, apply core updates.
# WARNING: drops and recreates all CMaNGOS databases (accounts and characters included).
set -e

cd /opt/tbc-db
cat > InstallFullDB.config <<EOF
MYSQL_HOST="db"
MYSQL_PORT="3306"
MYSQL_USERNAME="mangos"
MYSQL_PASSWORD="${DB_PASSWORD}"
MYSQL_USERIP="%"
MYSQL_PATH="/usr/bin/mariadb"
MYSQL_DUMP_PATH="/usr/bin/mariadb-dump"
CORE_PATH="/opt/mangos-tbc"
WORLD_DB_NAME="tbcmangos"
REALM_DB_NAME="tbcrealmd"
CHAR_DB_NAME="tbccharacters"
LOGS_DB_NAME="tbclogs"
LOCALES="YES"
DEV_UPDATES="NO"
AHBOT="NO"
PLAYERBOTS_DB="NO"
FORCE_WAIT="NO"
EOF

export TERM=dumb
./InstallFullDB.sh -InstallAll root "${DB_ROOT_PASSWORD}" DeleteAll
