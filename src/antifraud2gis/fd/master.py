
from typing import List, Dict, Set
from collections import Counter, defaultdict
from rich import print_json
import sys
import json
import gzip
import datetime

from ..company import Company
from ..user import User
from ..review import Review
from .fd import BaseFD

from .emptyuser import EmptyUserFD
from .medianage import MedianAgeFD
from .relation import RelationFD
from .medianrpu import MedianRPUFD

from ..settings import settings

class MasterFD(BaseFD):

    _detectors: Dict[str, BaseFD]

    # processed users
    _users: Set[User]

    def __init__(self, c: Company, explain: bool = False):

        super().__init__(c, explain=explain)
        
        # detectors which produced detections
        self.triggered = list()

        self.score['total_reviews'] = 0
        self.score['processed_reviews'] = 0
        self.score['empty_reviews'] = 0
        self.score['discarded'] = 0

        self._detectors = {
            'empty_user': EmptyUserFD(c, explain=explain),
            'median_age': MedianAgeFD(c, explain=explain),
            'median_rpu': MedianRPUFD(c, explain=explain),
            'relation': RelationFD(c, explain=explain)            
        }
        self._users = set()
        self.providers = defaultdict(int)


    def feed(self, cr: Review):
        # only A-company review feeded here
        self.score['total_reviews'] += 1

        empty = False

        if cr.age > settings.max_review_age:
            self.score['discarded'] += 1
            return

        self.providers[cr.provider] += 1

        if cr.is_empty():
            print("zzzz empty")


        if cr.is_empty() or cr.user.public_id in self._users:
            if cr.uid is not None and cr.user.public_id in self._users:
                # print(f"User {cr.user.public_id} {cr.created} {cr.provider} already processed DUPLICATE !!!")
                pass
            self.score['empty_reviews'] += 1
            empty = True
        else:
            self.score['processed_reviews'] += 1


        for d in self._detectors.values():
            d.feed(cr, empty=empty)

        if cr.uid is not None:
            self._users.add(cr.user.public_id)

    def explain(self, fh):
        for detector in self.triggered:
            detector.explain(fh = fh)

    def get_score(self):

        for detector_name, detector in self._detectors.items():
            detector_score = detector.get_score()
            # carefully join

            for k in detector_score.keys():
                if k == 'detections':
                    continue

                if k not in self.score:
                    self.score[k] = detector_score[k]
                else:
                    assert self.score[k] == detector_score[k]
            
            if detector_score['detections']:
                self.triggered.append(detector)
                self.score['detections'].extend(detector_score['detections'])

        self.score['providers'] = dict(self.providers)
        self.score['trusted'] = not self.score['detections']
        self.score['param_fp'] = settings.param_fp()
        self.score['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return self.score

