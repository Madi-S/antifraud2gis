from pathlib import Path
import os
from dotenv import load_dotenv

class Settings():
    def __init__(self):
        load_dotenv()
        self.storage = Path("~/.af2gis-storage").expanduser()
        self.user_storage = self.storage / "users"
        self.private_user_storage = self.storage / "users" / "_private.json"
        self.company_storage = self.storage / "companies"

        self.deep_check = bool(int(os.getenv('DEEP_CHECK', '0')))

        self.risk_hit_th = int(os.getenv('RISK_HIT_TH', '10'))
        self.sametitle_rel = int(os.getenv('SAMETITLE_HIT', '3'))
        self.sametitle_ratio = int(os.getenv('SAMETITLE_RATIO', '50'))

        self.risk_median_th = int(os.getenv('RISK_MEDIAN_TH', '15'))
        self.show_hit_th = int(os.getenv('SHOW_HIT_TH', '1000'))

        self.risk_highrate_th = float(os.getenv('RISK_HIGHRATE_TH', '5'))
        # self.risk_highrate_hit_th = float(os.getenv('RISK_HIGHRATE_HIT_TH', '5'))
        # self.risk_highrate_median_th = float(os.getenv('RISK_HIGHRATE_MEDIAN_TH', '15'))

        self.risk_empty_user_ratio = float(os.getenv('RISK_EMPTY_USER_TH', '30'))
        self.risk_user_ratio = float(os.getenv('RISK_USER_TH', '20'))
        self.risk_median_rpu = float(os.getenv('RISK_MEDIAN_RPU', '2'))
        
        self.happy_long_rel_th = int(os.getenv('HAPPY_LONG_REL_TH', '10'))
        self.happy_long_rel_min_towns_th = int(os.getenv('HAPPY_LONG_REL_MIN_TOWNS_TH', '3'))


        # 5 years old maximum 365*5=1825
        self.max_review_age = int(os.getenv('MAX_REVIEW_AGE', '1825'))

        self.mean_user_age = int(os.getenv('MEAN_USER_AGE', '180'))

        self.proxy = os.getenv('HTTPS_PROXY', None)

    def param_fp(self):
        return f"risk_hit={self.risk_hit_th} risk_median_th={self.risk_median_th} risk_highrate_th={self.risk_highrate_th} " \
            f"risk_empty_user_ratio={self.risk_empty_user_ratio} risk_user_ratio={self.risk_user_ratio} " \
            f"happy_long_rel_th={self.happy_long_rel_th} mean_user_age={self.mean_user_age} " \
            f"deep_check={self.deep_check}"

settings = Settings()