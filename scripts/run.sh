#!/bin/sh

set -e # to ensure that if any commands in the start fails, the whole script gives an error

python manage.py wait_for_db
python manage.py collectstatic --noinput # collect all static files, and put them in the specified STATIC directory in the settings
python manage.py migrate

uwsgi --socket :9000 --workers 4 --master --enable-threads --module app.wsgi
# This runs the uwsgi application on TCP port 9000 which nginx our reverse proxy server can connect to. The worker flag to 4 depends how many cpus on the server to use. The master flag makes this as the master thread. The enable-threads flag helps to ensure we are supporting multi threading. Finally with the module flag we are specifying to go to app and run wsgi.py script
