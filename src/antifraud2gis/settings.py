from pathlib import Path

class Settings():
    def __init__(self):
        self.storage = Path(".storage")
        self.user_storage = self.storage / "users"
        self.private_user_storage = self.storage / "users" / "_private.json"

        self.company_storage = self.storage / "companies"


settings = Settings()
