class AIError(Exception):
    """Raised when the AI workflow cannot produce a validated result."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


MODEL_HINT = "llama-3.3-70b-versatile or any current Groq chat model"
