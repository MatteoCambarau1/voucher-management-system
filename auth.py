"""HTTP Basic Auth per il sistema di distribuzione voucher.

Due ruoli:
- 'user': accesso a UI principale (assegna / annulla / cerca / guida)
- 'admin': accesso a /admin/* — ha anche il ruolo 'user' (puo' fare tutto)

Le credenziali sono lette dalle env var USER_PASSWORD e ADMIN_PASSWORD.
Se una delle due manca, l'app si rifiuta di partire — comportamento
volutamente rigido per evitare deploy in produzione senza auth configurata.
Per lo sviluppo locale, imposta le due variabili prima di lanciare l'app:
    export USER_PASSWORD='...'
    export ADMIN_PASSWORD='...'
"""
import os
from flask_httpauth import HTTPBasicAuth


def _require_env(name: str) -> str:
    """Legge una env var obbligatoria. Solleva RuntimeError se assente/vuota."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Env var '{name}' non impostata. "
            "Configurala prima di avviare l'app (vedi auth.py per i dettagli)."
        )
    return value


auth = HTTPBasicAuth()

USERS = {
    'user': _require_env('USER_PASSWORD'),
    'admin': _require_env('ADMIN_PASSWORD'),
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
