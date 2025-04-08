# Antifraud2GIS

Searching for fake (suspicious) reviews in 2gis.

This project is absolutely unofficial, not related to 2GIS.ru.

## Export and analyse data with JQ

~~~shell
# Export to JSONL
af2gis c export  > /tmp/export.jsonl

# get length (number of companies)
jq -s 'length' /tmp/export.jsonl

# Get top-10 by WSS score
jq -s 'sort_by(.score.WSS) | reverse | .[:10]' /tmp/export.jsonl

# Average (mean)
jq -s 'map(.score.WSS) | add / length' /tmp/export.jsonl

# WSS higher then 0.5 (0.5 is random here)
jq -s 'map(select(.score.WSS > 0.5))' /tmp/export.jsonl
jq -s '.[] | select(.score.WSS > 0.5)' /tmp/export.jsonl


~~~

## Start worker (for web app)
~~~
af2worker antifraud2gis.tasks -p1 -t1
~~~