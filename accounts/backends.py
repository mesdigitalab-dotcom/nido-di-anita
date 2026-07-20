"""
accounts/backends.py
---------------------

"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class UsernameOrEmailBackend(ModelBackend):
    """
    Permette il login con username OPPURE email.
    - Se l'input contiene '@' viene trattato come email.
    - Altrimenti viene trattato come username.
    Dopo aver trovato l'utente, verifica la password normalmente.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        login_input = username.strip()

        # Cerca l'utente per email o per username (case-insensitive)
        db_user = None
        if "@" in login_input:
            try:
                db_user = User.objects.get(email__iexact=login_input)
            except User.DoesNotExist:
                pass
        else:
            try:
                db_user = User.objects.get(username__iexact=login_input)
            except User.DoesNotExist:
                pass

        if db_user is None:
            # Esegui comunque un check fittizio per prevenire timing attacks
            User().set_password(password)
            return None

        if db_user.check_password(password) and self.user_can_authenticate(db_user):
            return db_user

        return None
