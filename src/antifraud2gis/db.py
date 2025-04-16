from rich import print_json
from pathlib import Path
import json
from loguru import logger


class MyDB:
    def __init__(self, directory=Path("~/.cache").expanduser()):
        self.directory = directory

        if self.directory.exists() is False:
            logger.info(f"Create cache directory {self.directory}")
            self.directory.mkdir()

        self.path_private_profiles = self.directory / "private_profiles.json"
        self.path_nocompanies = self.directory / "nocompanies.json"

        self.private_profiles = list()
        self.nocompanies = list()

        self.load()


    def load_private_profiles(self):
        if self.path_private_profiles.exists():
            with open(self.path_private_profiles) as f:
                self.private_profiles = json.load(f)
                #print(f"ZZZ DB Loaded {len(self.private_profiles)} private profiles")
                #print(f"mtime: {int(self.path_private_profiles.stat().st_mtime)}")
                #print(f"sz: {self.path_private_profiles.stat().st_size}")

    def load_nocompanies(self):
        if self.path_nocompanies.exists():
            with open(self.path_nocompanies) as f:
                self.nocompanies = json.load(f)

    def load(self):
        self.load_nocompanies()
        self.load_private_profiles()

    def save_private_profiles(self):
        with open(self.path_private_profiles, 'w') as f:
            json.dump(self.private_profiles, f)
            # logger.info(f"Saved {len(self.private_profiles)} private profiles")

    def save_nocompanies(self):
        with open(self.path_nocompanies, 'w') as f:
            json.dump(self.nocompanies, f)

    def is_private_profile(self, public_id):
        return public_id in self.private_profiles

    def is_nocompany(self, company_id):
        return company_id in self.nocompanies

    def add_private_profile(self, public_id):
        self.private_profiles.append(public_id)
        self.save_private_profiles()


    def add_nocompany(self, company_id):
        self.nocompanies.append(company_id)
        self.save_nocompanies()

    def remove_nocompany(self, company_id):
        if company_id in self.nocompanies:
            self.nocompanies.remove(company_id)
            self.save_nocompanies()

    def dump(self):
        print("private profiles:", len(self.private_profiles))
        print("companies todo:", len(self.nocompanies))
        print_json(data=list(self.nocompanies))

db = MyDB()