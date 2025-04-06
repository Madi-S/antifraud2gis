from rich import print_json
from pathlib import Path
import json
from loguru import logger


class MyDB:
    def __init__(self, directory=Path(".cache")):
        self.directory = directory

        if self.directory.exists() is False:
            logger.info(f"Create cache directory {self.directory}")
            self.directory.mkdir()

        self.path_private_profiles = self.directory / "private_profiles.json"
        self.path_companies = self.directory / "companies_todo.json"

        self.private_profiles = list()
        self.companies_todo = list()

        self.load()


    def load_private_profiles(self):
        if self.path_private_profiles.exists():
            with open(self.path_private_profiles) as f:
                self.private_profiles = json.load(f)
                #print(f"ZZZ DB Loaded {len(self.private_profiles)} private profiles")
                #print(f"mtime: {int(self.path_private_profiles.stat().st_mtime)}")
                #print(f"sz: {self.path_private_profiles.stat().st_size}")

    def load_companies(self):
        if self.path_companies.exists():
            with open(self.path_companies) as f:
                self.companies_todo = json.load(f)

    def load(self):
        self.load_companies()
        self.load_private_profiles()

    def save_private_profiles(self):
        with open(self.path_private_profiles, 'w') as f:
            json.dump(self.private_profiles, f)
            # logger.info(f"Saved {len(self.private_profiles)} private profiles")

    def save_companies(self):
        with open(self.path_companies, 'w') as f:
            json.dump(self.companies_todo, f)

    def is_private_profile(self, public_id):
        return public_id in self.private_profiles
    
    def add_private_profile(self, public_id):
        self.private_profiles.append(public_id)
        self.save_private_profiles()


    def add_company_todo(self, company_id):
        self.companies_todo.append(company_id)
        self.save_companies()

    def remove_company_todo(self, company_id):
        if company_id in self.companies_todo:
            self.companies_todo.remove(company_id)
            self.save_companies()

    def get_suspicious_company(self):
        if self.companies_todo:
            return self.companies_todo[0]


    def dump(self):
        print("private profiles:", len(self.private_profiles))
        print("companies todo:", len(self.companies_todo))
        print_json(data=list(self.companies_todo))

db = MyDB()