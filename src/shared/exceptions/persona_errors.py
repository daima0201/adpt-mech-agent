# src/core/persona/persona_exceptions.py

class PersonaError(Exception):
    pass


class PersonaImmutableError(PersonaError):
    pass


class PersonaValidationError(PersonaError):
    pass
