import random
from pathlib import Path
import os
from typing import Optional

from .settings import settings

def random_file(path: Path) -> Optional[Path]:
    path = Path(path)
    chosen = None
    count = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                count += 1
                if random.randint(1, count) == 1:
                    chosen = Path(entry.path)
    return chosen

def random_company() -> str:
    return random_file(settings.company_storage).name.split('-')[0]