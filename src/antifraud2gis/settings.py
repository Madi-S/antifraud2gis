from pathlib import Path
import os
from dotenv import load_dotenv

class Settings():
    def __init__(self):
        load_dotenv()
        self.storage = Path("~/.af2gis-storage").expanduser()
        self.user_storage = self.storage / "users"
        self.lmdb_user_storage = self.storage / "users.lmdb"

        self.private_user_storage = self.storage / "users" / "_private.json"
        self.company_storage = self.storage / "companies"

        # self.search = self.storage / "search.jsonl"
        # self.searchnew = self.storage / "searchnew.jsonl"
        self.companydb = self.storage / "companies.db"

        # trust company if <= min_reviews
        self.min_reviews = int(os.getenv('MIN_REVIEWS', '20'))


        # Relations-specific
        self.risk_hit_th = int(os.getenv('RISK_HIT_TH', '10'))
        self.sametitle_rel = int(os.getenv('SAMETITLE_HIT', '3'))
        self.sametitle_ratio = int(os.getenv('SAMETITLE_RATIO', '50'))

        self.happy_long_rel_happy_ratio = int(os.getenv('HAPPY_LONG_REL_HAPPY_RATIO', '50'))
        self.happy_long_rel = int(os.getenv('HAPPY_LONG_REL', '10'))
        self.happy_long_rel_min_towns = int(os.getenv('HAPPY_LONG_REL_MIN_TOWNS', '3'))

        # median rpu for relations/printing
        self.risk_median_th = int(os.getenv('RISK_MEDIAN_TH', '15'))
        self.show_hit_th = int(os.getenv('SHOW_HIT_TH', '1000'))



        # for relations and median age
        self.risk_highrate_th = float(os.getenv('RISK_HIGHRATE_TH', '5'))
        # self.risk_highrate_hit_th = float(os.getenv('RISK_HIGHRATE_HIT_TH', '5'))
        # self.risk_highrate_median_th = float(os.getenv('RISK_HIGHRATE_MEDIAN_TH', '15'))

        self.risk_user_ratio = float(os.getenv('RISK_USER_TH', '30'))


        # untrusted if EMPTY_USER% (and their rating differs)
        self.empty_user = float(os.getenv('EMPTY_USER', '75'))
        
        # do not run empty-user if less then N users available empty/real
        self.apply_empty_user_min = int(os.getenv('APPLY_EMPTY_USER', '20'))
        self.apply_median_rpu = int(os.getenv('APPLY_MEDIAN_RPU', '20'))
        self.apply_median_userage = int(os.getenv('APPLY_MEDIAN_UA', '20'))

        self.rating_diff = float(os.getenv('RATING_DIFF', '1.2'))

        self.median_rpu = float(os.getenv('MEDIAN_RPU', '5'))
        
        # 2 year old maximum 365
        self.max_review_age = int(os.getenv('MAX_REVIEW_AGE', '730'))

        self.median_user_age = int(os.getenv('MEDIAN_USER_AGE', '30'))
        self.median_user_age_nusers = int(os.getenv('MEDIAN_USER_AGE_NUSERS', '10'))


        self.proxy = os.getenv('HTTPS_PROXY', None)

        self.turnstile_sitekey = os.getenv('TURNSTILE_SITEKEY', None)
        self.turnstile_secret = os.getenv('TURNSTILE_SECRET', None)


    def param_fp(self):
        return f"risk_hit={self.risk_hit_th} risk_median_th={self.risk_median_th} risk_highrate_th={self.risk_highrate_th} " \
            f"empty_user={self.empty_user} " \
            f"risk_user_ratio={self.risk_user_ratio} " \
            f"happy_long_rel_th={self.happy_long_rel} happy_long_rel_happy_ratio={self.happy_long_rel_happy_ratio} " \
            f"median_user_age={self.median_user_age} median_rpu={self.median_rpu} " \
            f"sametitle_rel={self.sametitle_rel} sametitle_ratio={self.sametitle_ratio} " \
            f"apply_empty_user_min={self.apply_empty_user_min} apply_median_rpu={self.apply_median_rpu} apply_median_userage={self.apply_median_userage} " \
            f"rating_diff={self.rating_diff}"


settings = Settings()