from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pathlib import Path
from dotenv import load_dotenv
import os
import json
import gzip
import importlib.resources
import redis
from dramatiq import get_broker

from rich import print_json

from ..company import Company, CompanyList
from ..exceptions import AFReportNotReady, AFNoCompany
from ..tasks import fraud_task
from ..settings import settings
from ..const import REDIS_TASK_QUEUE_NAME, REDIS_TRUSTED_LIST, REDIS_UNTRUSTED_LIST, REDIS_WORKER_STATUS

app = FastAPI()

static_path = importlib.resources.files("antifraud2gis") / "static"
templates_path = importlib.resources.files("antifraud2gis") / "templates"

templates = Jinja2Templates(directory=templates_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

r = redis.Redis(decode_responses=True)


class ReportRequest(BaseModel):
    oid: str

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):


    last_trusted = [json.loads(item) for item in r.lrange(REDIS_TRUSTED_LIST, 0, -1)]
    last_untrusted = [json.loads(item) for item in r.lrange(REDIS_UNTRUSTED_LIST, 0, -1)]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "trusted": last_trusted,
            "untrusted": last_untrusted
            } 
    )


@app.get("/report/{oid}", response_class=HTMLResponse)
async def report(request: Request, oid: str):
    try:
        c = Company(oid)
    except AFNoCompany:
        return RedirectResponse(app.url_path_for("miss", oid=oid))
        # raise HTTPException(status_code=404, detail="Company not found")

    try:
        with gzip.open(c.report_path, "rt") as fh:
            report = json.load(fh)
            # print_json(data=report)
            # print(report['relations'][0])

            for rel in report['relations']:
                rep_path = settings.company_storage / (rel['oid'] + '-report.json.gz')
                if rep_path.exists():
                    with gzip.open(rep_path, "rt") as fh:
                        rel_report = json.load(fh)
                        rel['trusted'] = rel_report['score']['trusted']
                else:
                    rel['trusted'] = None

            last_trusted = [json.loads(item) for item in r.lrange(REDIS_TRUSTED_LIST, 0, -1)]
            last_untrusted = [json.loads(item) for item in r.lrange(REDIS_UNTRUSTED_LIST, 0, -1)]


            return templates.TemplateResponse(
                "report.html", {
                    "request": request,
                    "settings": settings,
                    "c": c,
                    "title": c.title,
                    "score": report['score'],
                    "relations": report['relations'],
                    "trusted": last_trusted,
                    "untrusted": last_untrusted
                    }
            )

    except FileNotFoundError:
        # return 
        return RedirectResponse(app.url_path_for("miss", oid=oid))
        # raise HTTPException(status_code=404, detail="Report not found")

    return "OK"

@app.get("/miss/{oid}", response_class=HTMLResponse)
async def miss(request: Request, oid: str):

    last_trusted = [json.loads(item) for item in r.lrange(REDIS_TRUSTED_LIST, 0, -1)]
    last_untrusted = [json.loads(item) for item in r.lrange(REDIS_UNTRUSTED_LIST, 0, -1)]

    try:
        c = Company(oid)
        assert c.title is not None

    except (AFNoCompany, AssertionError) as e:
        return templates.TemplateResponse(
            "nocompany.html", {
                "request": request, "oid": oid,
                "trusted": last_trusted,
                "untrusted": last_untrusted
            }
        )
        



    return templates.TemplateResponse(
        "miss.html", {
            "request": request, "title": c.title, "oid": c.object_id,   
            "trusted": last_trusted,
            "untrusted": last_untrusted
        }
    )


@app.post("/submit", response_class=HTMLResponse)
async def submit(request: Request, oid: str = Form(...)):
    fraud_task.send(oid)
    r.rpush('af2gis:queue', oid)

    return RedirectResponse(app.url_path_for("progress", oid=oid), status_code=303)


@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    print("search", query)
    return RedirectResponse(app.url_path_for("report", oid=query), status_code=303)


@app.get("/progress/{oid}", response_class=HTMLResponse)
async def progress(request: Request, oid: str):
    try:
        c = Company(oid)
        print("miss for", c)
    except (AFNoCompany, AssertionError):
        return templates.TemplateResponse(
            "nocompany.html", {
                "request": request, "oid": oid,
            }
        )

    if c.report_path.exists():
        return RedirectResponse(app.url_path_for("report", oid=oid))

    wstatus = r.get(REDIS_WORKER_STATUS)
    tasks = r.lrange(REDIS_TASK_QUEUE_NAME, 0, -1)  # возвращает list of bytes    
    queue_size = len(tasks)
    try:
        qpos = tasks.index(oid) + 1
    except ValueError:
        qpos=None
    

    # position = next((i for i, task in enumerate(tasks) if task_id in str(task)), None)
    # print("pos:", position)

    last_trusted = [json.loads(item) for item in r.lrange(REDIS_TRUSTED_LIST, 0, -1)]
    last_untrusted = [json.loads(item) for item in r.lrange(REDIS_UNTRUSTED_LIST, 0, -1)]


    return templates.TemplateResponse(
        "progress.html", {
            "request": request, "title": c.title, "oid": c.object_id,
            "qsize": queue_size, "wstatus": wstatus, "qpos": qpos,
            "trusted": last_trusted,
            "untrusted": last_untrusted
        }
    )


def main():
    global templates    
    import uvicorn
    auto_reload = bool(os.getenv("AUTO_RELOAD", False))
    print("AUTO_RELOAD:", auto_reload)
    load_dotenv()
    uvicorn.run("antifraud2gis.cli.af2web:app", host="0.0.0.0", port=8000, reload=auto_reload)

if __name__ == "__main__":
    main()