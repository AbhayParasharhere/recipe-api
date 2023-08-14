"""
Django command to wait for the database to be available
"""
import time

from psycopg2 import OperationalError as Psycopg2Error

from django.db import OperationalError

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Django command to wait for database"""

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database...')
        db_ready = False

        while db_ready is False:
            try:
                self.check(databases=['default'])
                db_ready = True
            except (Psycopg2Error, OperationalError):
                self.stdout.write('Database unavailable, waiting 1 second ...')
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Database available'))
