from .company import Company
import numpy as np

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import print as rprint

class Relation:
    """ relation between two companies """

    a: Company
    b: str
    users: set
    nusers: int
    mean: float
    median: float

    count: int

    def __init__(self, a: Company, b: str):
        self.a = a
        self.b = b
        self.count = 0
        self._calculated = False
        self.users = set()
        self.nusers = 0
        self.mean = None
        self.median = None

    def add_user(self, user):
        if user in self.users:
            # print(f"ALREADY EXISTS {user} for {self.b}")
            pass
        self.users.add(user)
        self.nusers = len(self.users)

    def calc(self):
        if self._calculated:
            return

        user_reviews = list()
        for u in self.users:
            user_reviews.append(u.nreviews())
        
        self.mean = round(float(np.mean(user_reviews)), 3)
        self.median = int(np.median(user_reviews))
        self._calculated = True
    
    def inc(self):
        self.count += 1
    
    def is_dangerous(self):
        if self.count > 10:
            return True
        return False
    

    def __repr__(self):
        if not self._calculated:
            self.calc()
        bcompany = Company(self.b)
        return f"{bcompany.get_title()} ({bcompany.address}): hits: {len(self.users)}/{self.count} mean: {self.mean} median: {self.median})"

class RelationDict:

    c: Company
    relations: dict

    meanmedian: float
    doublemedian: float

    def __init__(self, c: Company):
        self.c = c
        self.relations = dict()
        self.meanmedian = None
        self.doublemedian = None
        self.ndangerous = None

    def __getitem__(self, oid):
        if oid not in self.relations:
            self.relations[oid] = Relation(self.c, oid)
        return self.relations[oid]

    def calc(self):        
        if self.meanmedian:
            # already calculated
            return
        self.ndangerous = 0
        medianlist = list()
        for k, rel in self.relations.items():
            if rel.is_dangerous():
                self.ndangerous += 1
            rel.calc()
            medianlist.append(rel.median)
        
        if medianlist:
            self.meanmedian = round(float(np.mean(medianlist)), 3)
            self.doublemedian = int(np.median(medianlist))
        else:
            self.meanmedian = 0
            self.doublemedian = 0

    def __repr__(self):
        self.calc()
        return f"RELATIONS: {len(self.relations)} meanmedian: {self.meanmedian} doublemedian: {self.doublemedian} ndangerous: {self.ndangerous}"

    def dangerous(self, field='count'):
        filtered = (rel for rel in self.relations.values() if rel.is_dangerous())  # Filter dangerous items
        sorted_items = sorted(filtered, key=lambda x: getattr(x, field), reverse=True)  # Sort descending
        yield from sorted_items


    def dump_table(self):
        console = Console()
        table = Table(show_header=True, header_style="bold magenta", title="Scores")
        table.add_column("T", style='red')
        table.add_column("Company name")
        # table.add_column("Address")
        table.add_column("ID/Alias")
        table.add_column("Hits")
        table.add_column("Mean")
        table.add_column("Median")

        for rel in self.dangerous():            
            _c = Company(rel.b)
            table.add_row(_c.tags, _c.get_title(), _c.alias or Text(_c.object_id, style='grey30'), f'{rel.count}/{len(rel.users)}', str(rel.mean), str(rel.median))
        print()
        console.print(table)

        rprint(self)
