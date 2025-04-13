import subprocess

from .settings import settings
import json

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
