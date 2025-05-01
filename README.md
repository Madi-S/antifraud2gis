# Antifraud2GIS

Searching for fake (suspicious) reviews in 2gis.

This project is absolutely unofficial, not related to 2GIS.ru.

## Installation
~~~
pipx install git+https://github.com/yaroslaff/antifraud2gis
~~~


## Fraud detection
~~~
# by OID:
af2gis fraud 141265769338187

# by alias
af2gis fraud nskzoo

# list all aliases:
af2gis aliases
~~~

## Export and analyse data with JQ

~~~shell
# Export to JSONL
af2gis c export  > /tmp/export.jsonl

# or to local search jsonl
af2gis export > ~/.af2gis-storage/search.jsonl

# find specific record
jq 'select(.oid == "70000001041490377")' /tmp/export.jsonl

# list providers for review
zcat ~/.af2gis-storage/companies/141265770459396-reviews.json.gz | jq '.[].provider'
zcat ~/.af2gis-storage/companies/141265770459396-reviews.json.gz | jq '.[] | {id, provider}'

zcat ~/.af2gis-storage/companies/70000001021506525-reviews.json.gz | jq '.[] | select(.provider == "2gis") | .date_created'

# get length (number of companies)r
jq -s 'length' /tmp/export.jsonl

# Get top-10 by WSS score
jq -s 'sort_by(.score.WSS) | reverse | .[:10]' /tmp/export.jsonl

# Average (mean)
jq -s 'map(.score.WSS) | add / length' /tmp/export.jsonl

# WSS higher then 0.5 (0.5 is random here)
jq -s 'map(select(.score.WSS > 0.5))' /tmp/export.jsonl
jq -s '.[] | select(.score.WSS > 0.5)' /tmp/export.jsonl

# raw files
zcat .af2gis-storage/companies/nnnnnn-reviews.json.gz | jq 'length'

~~~

## Start worker (for web app)
~~~
af2worker -p1 -t1 antifraud2gis.tasks 
~~~