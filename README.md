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

Next call to fraud detection will show old result unless `--overwrite` option given.

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

## Adjust settings

Settings variables can be overriden in environment or .env file.

You can always see accurate current defaults in [settings.py](src/antifraud2gis/settings.py).

### Common settings

If company has less then `MIN_REVIEWS` (20) it will be considered trusted without any other checks.

Only reviews with age under `MAX_REVIEW_AGE` (730 days) are processed.

`SKIP_OIDS` and `DEBUG_UIDS` are space-separated list of UID/OIDs to ignore/debug. (only for debugging purposes, not for users).

### Relation-specific

Definition: 
Relation between companies A and B is *high* if it has many hits (>= `RISH_HIT`).
Relation is *happy* if avg rating for both A/B companies in relation are >= `RISK_HIGHRATE`

For *sametitle* check: check applied only if company has more then `SAMETITLE_REL` (3) 'happy' relations, and total different titles in relations ( / total happy relations) are under `SAMETITLE_RATIO` (percents). 

For *happy long relations* check: check applied if number of towns are >= `HAPPY_LONG_REL_MIN_TOWNS` (3) and *happy ratio* (ratio of happy hight relations to all high relations) is over `HAPPY_LONG_REL` (50%). *happy_long_rel* calculated as unique_towns / happy_high_relations. (If each happy high relation belongs to different town, *happy_long_rel* will be 1). Detection will be if this value is >= then `HAPPY_LONG_REL` (10).


        self.happy_long_rel_happy_ratio = int(os.getenv('HAPPY_LONG_REL_HAPPY_RATIO', '50'))
        self.happy_long_rel = int(os.getenv('HAPPY_LONG_REL', '10'))
        self.happy_long_rel_min_towns = int(os.getenv('HAPPY_LONG_REL_MIN_TOWNS', '3'))

        # median rpu for relations/printing
        self.risk_median_th = int(os.getenv('RISK_MEDIAN_TH', '15'))
        self.show_hit_th = int(os.getenv('SHOW_HIT_TH', '1000'))



        # for relations and median age
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

