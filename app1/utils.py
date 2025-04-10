from django.conf import settings
from django.db import connections, OperationalError, ProgrammingError
from django.apps import apps
from django.core.management import call_command
from app2.models import *

def create_database_and_tables(DB_name):     
    with connections['default'].cursor() as cursor:
        db_engine = settings.DATABASES['default']['ENGINE']
        if db_engine == 'django.db.backends.sqlite3':
            if not DB_name.endswith('.sqlite3'):
                DB_name = f"{DB_name}.sqlite3"  # Ensure .sqlite3 extension is added                        
            print(f"SQLite database {DB_name} will be created automatically on first access.")
        elif db_engine in ['django.db.backends.mysql', 'django.db.backends.postgresql', 'django.db.backends.oracle']:
            try:
                cursor.execute(f"CREATE DATABASE {DB_name}")
            except OperationalError as e:
                print(f"Database creation failed: {e}")
                return False
        else:
            raise NotImplementedError(f"Database engine {db_engine} is not supported.")    
    
    # Dynamically add the new database configuration
    settings.DATABASES[DB_name] = {
        'ENGINE': settings.DATABASES['default']['ENGINE'],
        'NAME': DB_name,
        'USER': settings.DATABASES['default'].get('USER', ''),
        'PASSWORD': settings.DATABASES['default'].get('PASSWORD', ''),
        'HOST': settings.DATABASES['default'].get('HOST', 'localhost'),
        'PORT': settings.DATABASES['default'].get('PORT', ''),
        'ATOMIC_REQUESTS': settings.DATABASES['default'].get('ATOMIC_REQUESTS', False),
        'TIME_ZONE': settings.DATABASES['default'].get('TIME_ZONE', settings.TIME_ZONE),  # Add TIME_ZONE
        'CONN_HEALTH_CHECKS': settings.DATABASES['default'].get('CONN_HEALTH_CHECKS', False),  # Add CONN_HEALTH_CHECKS
        'CONN_MAX_AGE': settings.DATABASES['default'].get('CONN_MAX_AGE', 0),  # Add CONN_MAX_AGE
        'OPTIONS': settings.DATABASES['default'].get('OPTIONS', {}),  # Add OPTIONS for database-specific configurations
        'DISABLE_SERVER_SIDE_CURSORS': settings.DATABASES['default'].get('DISABLE_SERVER_SIDE_CURSORS', False),  # Add DISABLE_SERVER_SIDE_CURSORS
        'AUTOCOMMIT': settings.DATABASES['default'].get('AUTOCOMMIT', True),  # Add AUTOCOMMIT
    }
    
    # Ensure the connection is ready
    connections[DB_name].ensure_connection() 


    DEFAULT_DJANGO_APPS = ['auth', 'contenttypes', 'sessions', 'admin', 'migrations']


    try:
        for app in DEFAULT_DJANGO_APPS:
            call_command('migrate', app_label=app, database=DB_name, verbosity=2)
            call_command('migrate', '--database', DB_name, app_label='app2', verbosity=2)

        print(f"Default Django tables migrated successfully in database {DB_name}.")
    except Exception as e:
        print(f"Error migrating default Django tables to database {DB_name}: {e}")
        return False
    # Apply migrations for `app2` to the new database
    # try:
    #     call_command('migrate', '--database', DB_name, app_label='app2', verbosity=2)
    #     print(f"Tables created successfully in database {DB_name}.")
    # except Exception as e:
    #     print(f"Error applying migrations to database {DB_name}: {e}")
    #     return False

    return True
