import warnings, logging, os
from django.core.wsgi import get_wsgi_application

# 🔇 Suppress GLib / GTK warnings in console
logging.getLogger("gi.repository.Gio").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["G_MESSAGES_DEBUG"] = ""

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paradise.settings')

application = get_wsgi_application()
