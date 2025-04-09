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

app = FastAPI()

static_path = importlib.resources.files("antifraud2gis") / "static"
templates_path = importlib.resources.files("antifraud2gis") / "templates"

templates = Jinja2Templates(directory=templates_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

dqname="dramatiq:default"

r = redis.Redis(decode_responses=True)


class ReportRequest(BaseModel):
    oid: str

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):


    last_trusted = [json.loads(item) for item in r.lrange('af2gis:last_trusted', 0, -1)]
    last_untrusted = [json.loads(item) for item in r.lrange('af2gis:last_untrusted', 0, -1)]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "trusted": last_trusted,
            "untrusted": last_untrusted
            } 
    )




@app.get("/recent")
async def recent(request: Request):
    data = {
        "trusted": [
            {
                "title": "Новосибирский зоопарк им. Р.А. Шило, Зоопарк",
                "address": "Новосибирск, Тимирязева, 71/1",
                "oid": "141265769338187"
            },
            {
                "title": "Аура, торгово-развлекательный центр",
                "address": "Новосибирск, Военная, 5",
                "oid": "141265770459396"
            },
            {
                "title": "Новосибирск-Главный, железнодорожный вокзал",
                "address": "Новосибирск, Дмитрия Шамшурина, 43",
                "oid": "141265769369926"
            },
        ],
        "untrusted": [
            {
                "title": "Манты-плов, кафе",
                "address": "Новосибирск, Троллейная, 93а",
                "oid": "70000001094664808"
            },
            {
                "title": "Восточное кафе, Кафе",
                "address": "Новосибирск, улица Сибиряков-Гвардейцев, 62а",
                "oid": "70000001086696739"
            },
            {
                "title": "Новотех, апарт-отель",
                "address": "Сургут, улица Югорская, 15",
                "oid": "5489290326835326"
            },
        ]        
    }

    return data

@app.post("/api/report")
async def api_report(data: ReportRequest):
    print("report for", data.oid)
    c = Company(data.oid)
    print("report for", c)

    try:
        print("read report from", c.report_path)
        with gzip.open(c.report_path, "rt") as fh:
            report = json.load(fh)
            return report
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found")

    return "OK"

@app.get("/report/{oid}", response_class=HTMLResponse)
async def report(request: Request, oid: str):
    print("HTML report for", oid)
    try:
        c = Company(oid)
    except AFNoCompany:
        print("redirect.....")
        return RedirectResponse(request.url_for("miss", oid=oid))
        # raise HTTPException(status_code=404, detail="Company not found")
    print("report for", c)

    try:
        print("read report from", c.report_path)
        with gzip.open(c.report_path, "rt") as fh:
            report = json.load(fh)
            # print_json(data=report)
            # print(report['relations'][0])

            last_trusted = [json.loads(item) for item in r.lrange('af2gis:last_trusted', 0, -1)]
            last_untrusted = [json.loads(item) for item in r.lrange('af2gis:last_untrusted', 0, -1)]


            return templates.TemplateResponse(
                "report.html", {
                    "request": request, 
                    "c": c,
                    "title": c.title,
                    "score": report['score'],
                    "relations": report['relations'],
                    "trusted": last_trusted,
                    "untrusted": last_untrusted
                    }
            )

            return report
    except FileNotFoundError:
        # return 
        return RedirectResponse(request.url_for("miss", oid=oid))
        # raise HTTPException(status_code=404, detail="Report not found")

    return "OK"

@app.get("/miss/{oid}", response_class=HTMLResponse)
async def miss(request: Request, oid: str):

    last_trusted = [json.loads(item) for item in r.lrange('af2gis:last_trusted', 0, -1)]
    last_untrusted = [json.loads(item) for item in r.lrange('af2gis:last_untrusted', 0, -1)]

    try:
        c = Company(oid)
        print("miss for", c)

    except (AFNoCompany, AssertionError):
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
    print("submit", oid)
    task_id = fraud_task.send(oid).message_id
    print("submit task_id", task_id)
    task_data = r.get(f"dramatiq:message:{task_id}")
    print("submit task data", task_data)  # Shows serialized task details

    return RedirectResponse(request.url_for("progress", oid=oid, task_id=task_id), status_code=303)


@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    print("search", query)
    return RedirectResponse(request.url_for("report", oid=query), status_code=303)


@app.get("/progress/{oid}/{task_id}", response_class=HTMLResponse)
async def progress(request: Request, oid: str, task_id: str):
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
        return RedirectResponse(request.url_for("report", oid=oid))

    queue_size = r.llen(dqname)    
    print(f"Queue size: {queue_size}")
    
    wstatus = r.get('af2gis:worker_status')
    tasks = r.lrange(dqname, 0, -1)

    print("tasks:", tasks)
    
    task_data = r.get(f"dramatiq:message:{task_id}")
    print("TASK:", task_data)

    position = next((i for i, task in enumerate(tasks) if task_id in str(task)), None)
    print("pos:", position)

    last_trusted = [json.loads(item) for item in r.lrange('af2gis:last_trusted', 0, -1)]
    last_untrusted = [json.loads(item) for item in r.lrange('af2gis:last_untrusted', 0, -1)]


    return templates.TemplateResponse(
        "progress.html", {
            "request": request, "title": c.title, "oid": c.object_id,
            "qsize": queue_size, "position": position, "wstatus": wstatus,
            "trusted": last_trusted,
            "untrusted": last_untrusted
        }
    )


def main():
    global templates    
    import uvicorn
    auto_reload = True
    load_dotenv()
    uvicorn.run("antifraud2gis.cli.af2web:app", host="0.0.0.0", port=8000, reload=auto_reload)

if __name__ == "__main__":
    main()