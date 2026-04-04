class BaseAdapter:
    def complete(self, messages: list, tools: list = None, system: str = None) -> dict:
        """Send messages, return structured response with content blocks."""
        raise NotImplementedError

    def stream(self, messages: list, tools: list = None, system: str = None):
        """Optional streaming. Raise NotImplementedError to disable."""
        raise NotImplementedError

    @property
    def supports_tools(self) -> bool:
        """Return False for providers that don't support function calling."""
        return True
