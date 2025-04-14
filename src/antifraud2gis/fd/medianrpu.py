from collections import Counter
import numpy as np


from .fd import BaseFD
from ..user import User
from ..company import Company
from ..review import Review
from ..settings import settings

"""
    test companies for medianrpu (detect): 
    141265770459735
"""

class MedianRPUFD(BaseFD):

    def __init__(self, c, explain: bool = False):
        super().__init__(c, explain=explain)
        self.rpu = list()
        self.records = list()


    def feed(self, cr: Review, empty: bool = False):

        if empty:
            return

        u = cr.user
        self.rpu.append(u.nreviews())
        if self.explain:
            self.records.append(f"{u.public_id} {u.name} {cr.rating} {u.nreviews()}")

    def get_score(self):

        median_rpu = int(np.median(self.rpu))

        self.score['median_rpu'] = median_rpu
        
        if self.score['median_rpu'] <= settings.median_rpu:
            self.score['detections'].append(f"median_rpu: {self.score['median_rpu']} <= {settings.median_rpu} "\
                f"({sum(rpu <= settings.median_rpu for rpu in self.rpu)} of {len(self.rpu)})")
    
        return self.score
    
    def explain(self, fh):
        print(f"Explanation for median_rpu", file=fh)

        for line in self.records:
            print(line, file=fh)

        print(f"RPUs ({self.score['median_rpu']}): {sorted(self.rpu)}")
        print(f"result: {self.score['median_rpu']}")