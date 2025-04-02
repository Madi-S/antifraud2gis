from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from pathlib import Path
from dotenv import load_dotenv
import os
import importlib.resources


app = FastAPI()

static_path = importlib.resources.files("antifraud2gis") / "static"
templates_path = importlib.resources.files("antifraud2gis") / "templates"

print("static_path", static_path)
templates = Jinja2Templates(directory=templates_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")




@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}  # FastAPI templates always need the request object
    )


@app.post("/", response_class=HTMLResponse)
async def greet(name: str = Form(...)):
    return f"""
    <h1>Привет, {name}!</h1>
    <a href="/">Назад</a>
    """

def main():
    global templates    
    import uvicorn
    load_dotenv()
    
    


    uvicorn.run(app, host="0.0.0.0", port=8000)

