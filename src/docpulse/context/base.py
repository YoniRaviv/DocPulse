from typing import Protocol, runtime_checkable


@runtime_checkable
class ContextProvider(Protocol):
    """Supplies the 'why' behind a change as one intent blob for the verifier."""

    def get_intent(self) -> str: ...
