class Server:
    def __init__(self, host: str, port: int, secret_key: str = "") -> None:
        self.host = host
        self.port = port
        self.secret_key = secret_key


class Database:
    def __init__(self, url: str) -> None:
        self.url = url


class SQLite(Database):
    pass


class Postgres(Database):
    pass
