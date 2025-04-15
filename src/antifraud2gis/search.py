import subprocess

from .settings import settings
from .company import Company
import json
import fcntl

def is_safe_search(query):
    # Проверяем, что строка состоит из букв, цифр и пробелов
    if all(char.isalnum() or char.isspace() for char in query):
        return True
    else:
        return False

def search(query: str, limit=50):
    if not is_safe_search(query):
        print("Unsafe search query:", query)
        return list()
    
    # (.title // "" | test("вкус"; "i")) and (.title // "" | test("хинкал"; "i"))

    query_parts = [f'(.searchstr // "" | test("{word}"; "i"))' for word in query.split(' ')]

    query = ' and '.join(query_parts)

    r = subprocess.run(['jq', '-c', f'. | select({query})', settings.search], capture_output=True, text=True)
    try:
        result = [json.loads(line) for line in r.stdout.splitlines()[:limit]]
        return result
    except json.JSONDecodeError:
        print("Error decoding JSON:", r.stdout)
        return list()

def index_company(c: Company):

    if company_indexed(c.object_id):
        print(f"{c.object_id} already indexed")
        return
    
    # tmp
    return
    with open(settings.searchnew, "a", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps(c.export()) + "\n")
        fcntl.flock(fh, fcntl.LOCK_UN)

def company_indexed(oid: str, path = None):
    if path is None:
        for index in [settings.search, settings.searchnew]:
            if company_indexed(oid, index):
                print(f"{oid} already indexed in {index}")
                return True
        return False
    
    if not path.exists():
        return False
    
    query = f'(.oid == "{oid}")'
    r = subprocess.run(['jq', '-c', f'. | select({query})', path], capture_output=True, text=True)
    print(f"indexed? {path} {r.returncode} {len(r.stdout)}")
