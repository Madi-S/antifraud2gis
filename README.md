# Antifraud2GIS

Searching for fake (suspicious) reviews in 2gis.

This project is absolutely unofficial, not related to 2GIS.ru.

## Installation
~~~
pipx install git+https://github.com/yaroslaff/antifraud2gis
~~~

## Basic operations

- `af2gis` - main program for most user operations
- `af2dev` - program for developers 
- `af2web` - webserver (probably you do not need it)
- `af2worker` - background worker (probably you do not need it too)

If you want just to run fraud detection on companies by 2GIS object-id, you need to use only `af2gis`.


### Fraud detection
~~~
# by OID:
af2gis fraud 141265769338187

# by alias
af2gis fraud nskzoo

# list all aliases:
af2gis aliases
~~~


### Explore town (crawl, index new companies)
You need to have at least few users already crawled (from previous fraud detections).
Explore will submit jobs to redis queue, and you need to have af2worker running to process queue.

~~~
af2dev explore -t Новосибирск
~~~

`-t` will limit only to specific town.

"Explore" may look slow or even hangs, but you may check summary or queue status in other tab every 3-5 minutes to see progress. (It really hangs only if af2worker is not running)


### local db summary
~~~
$ af2gis summary 
2025-05-04 16:15:35 SUMMARY Companies: total=3, nerr=0 ncalc=3 nncalc=0
2025-05-04 16:15:35 SUMMARY LMDB prefixes: {'object': 12053, 'user': 900}
~~~

Companies (on first line) are companies which are downloaded, objects (on second line) - companies which are known (but not downloaded).

### Queue status
Use `af2dev queue` (or just `q`).
~~~
$ af2dev q
Queue report
Worker status: started...
Dramatiq queue: 0
Tasks (0): [] 
Trusted (5/20):
  141265771582384 СберБанк, Банки (3.6) None
  70000001025692296 Нск Шашлык, Быстрое питание (4.8) None
  70000001026944015 Дивногорский, управляющая компания (3) None
  70000001023639031 Сибкарт моторспорт, картинг-центр (4.7) None
  141265771632879 Подорожник, доступная кофейня (2.2) None
Untrusted (5/11)
  70000001091636066 Культура, рюмочная (5) ['risk_users 84% (222 / 262)']
  70000001091636066 Культура, рюмочная (5) ['risk_users 84% (222 / 262)']
  70000001083008185 Рыдзинский, рюмочная-караоке (4.9) ['risk_users 41% (179 / 432)']
  5348552838629866 Юсуповский Дворец на Мойке, музей (4.9) ['sametitle_rel 20% (5 of 1)']
  5348552838629866 Юсуповский Дворец на Мойке, музей (4.9) ['sametitle_rel 20% (5 of 1)']
~~~

## Search by substring
SQLite database has data about all companies after fraud-detect. Company itself and top of company's *neighbour* (related) companies are added to database.

~~~
$ af2gis search арн -t Новосибирск
{'oid': '70000001075178717', 'title': 'Пекарня, Пекарни', 'address': 'Новосибирск, Урожайная, 8', 'town': 'Новосибирск', 'searchstr': 'новосибирск пекарня, пекарни', 'rating_2gis': 4.7, 'trusted': 1, 'nreviews': 31, 'detections': ''}
{'oid': '70000001041433989', 'title': 'Пекарня, Пекарни', 'address': 'Новосибирск, Чигорина, 3', 'town': 'Новосибирск', 'searchstr': 'новосибирск пекарня, пекарни', 'rating_2gis': 4.6, 'trusted': 1, 'nreviews': 52, 'detections': ''}
~~~

LMDB database has data about all ever seen companies (even if company was once seen in one user reviews)
~~~
mir ~/repo/antifraud2gis $ af2dev lmdb дог
object:70000001007492207
{
  "name": "Хот-дог райский, киоск фастфудной продукции",
  "address": "Новосибирск, проспект Дзержинского, 23"
}
object:70000001017423547
{
  "name": "Хот-дог Мастер, фуд-киоск",
  "address": "Новосибирск, проспект Карла Маркса, 4а"
}
...
~~~
