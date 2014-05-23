"""the auth and rules module."""

from nectar.store import SumCapabilities


class Auth():
    def __init__(self, pubkey_chksum):
        self._cap = SumCapabilities()  # global capabilities
        if self._cap[pubkey_chksum] is None:
            raise AuthDeniedError()
        self.pubkey_chksum = pubkey_chksum
        self.capabilities = self._cap[pubkey_chksum]  # session capabilities

    def is_admin(self):
        #TODO read this from session capabilities instead
        return self._cap[self.pubkey_chksum] == 'admin'


class AuthDeniedError(Exception):
    pass


class NotAllowedError(Exception):
    pass
