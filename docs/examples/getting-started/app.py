class Worker:
    def __init__(self, name: str, timeout: int, retries: int) -> None:
        self.name = name
        self.timeout = timeout
        self.retries = retries
