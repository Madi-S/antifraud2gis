from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pathlib import Path
from dotenv import load_dotenv
import os
import json
import gzip
import importlib.resources

from ..company import Company, CompanyList
from ..exceptions import AFReportNotReady, AFNoCompany

app = FastAPI()

static_path = importlib.resources.files("antifraud2gis") / "static"
templates_path = importlib.resources.files("antifraud2gis") / "templates"

print("static_path", static_path)
templates = Jinja2Templates(directory=templates_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")



class ReportRequest(BaseModel):
    oid: str

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}  # FastAPI templates always need the request object
    )


@app.get("/recent")
async def report(request: Request):
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

@app.post("/report")
async def report(data: ReportRequest):
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

def main():
    global templates    
    import uvicorn
    auto_reload = True
    load_dotenv()
    uvicorn.run("antifraud2gis.cli.af2web:app", host="0.0.0.0", port=8000, reload=auto_reload)

