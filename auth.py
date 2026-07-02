"""HTTP Basic Auth per il sistema di distribuzione voucher.

Due ruoli:
- 'user': accesso a UI principale (assegna / annulla / cerca / guida)
- 'admin': accesso a /admin/* — ha anche il ruolo 'user' (puo' fare tutto)

Credenziali via env var. I fallback locali servono solo per lo sviluppo:
in produzione impostare sempre USER_PASSWORD e ADMIN_PASSWORD.
"""
import os
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()

USERS = {
    'user': os.environ.get('USER_PASSWORD', 'user-dev-password'),
    'admin': os.environ.get('ADMIN_PASSWORD', 'admin-dev-password'),
}


@auth.verify_password
def verify_password(username, password):
    """Ritorna username se le credenziali sono valide, altrimenti None."""
    if username in USERS and USERS[username] == password:
        return username
    return None


@auth.get_user_roles
def get_user_roles(user):
    """L'admin ha anche il ruolo 'user': puo' accedere a tutte le route."""
    if user == 'admin':
        return ['admin', 'user']
    return ['user']
