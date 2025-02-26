from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from playwright.sync_api import sync_playwright
import asyncio
import sys

# Fix for Windows event loop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI()

# Set up Jinja2 for HTML rendering
templates = Jinja2Templates(directory="templates")

CATEGORY_URLS = {
    "engineering": "https://engineering.careers360.com/exams",
    "management": "https://bschool.careers360.com/exams",
    "law": "https://law.careers360.com/exams",
    "design": "https://design.careers360.com/exams",
    "it": "https://it.careers360.com/exams",
    "pharmacy": "https://pharmacy.careers360.com/exams",
    "medical": "https://medicine.careers360.com/exams",
}

def format_exam_link(title: str, base_url: str):
    """Formats the exam detail page link based on the title."""
    title_part = title.split(" - ")[0]  # Take only part before "-"
    formatted_title = title_part.lower().replace(" ", "-")
    return f"{base_url}/{formatted_title}"

def scrape_exams_from_page(page, base_url):
    """Extracts exam details from the current page."""
    exams = []
    exam_containers = page.query_selector_all("div.exam_listing_info")

    for exam in exam_containers:
        title_el = exam.query_selector("div.exam_detail.d-flex > div.school_infooo > div.title > h2 > a")
        title = title_el.inner_text().strip() if title_el else "N/A"

        date_el = exam.query_selector("div.admission_correction > div.online_offline")
        application_date = date_el.inner_text().strip() if date_el else "N/A"

        exam_type_el = exam.query_selector("div.offline ul li:nth-child(1)")
        exam_type = exam_type_el.inner_text().strip() if exam_type_el else "N/A"

        level_el = exam.query_selector("div.offline ul li:nth-child(2)")
        exam_level = level_el.inner_text().strip() if level_el else "N/A"

        frequency_el = exam.query_selector("div.offline ul li:nth-child(3)")
        frequency = frequency_el.inner_text().strip() if frequency_el else "N/A"

        body_el = exam.query_selector("div.offline ul li:nth-child(4)")
        conducting_body = body_el.inner_text().strip() if body_el else "N/A"

        colleges_el = exam.query_selector("div.offline ul li:nth-child(5)")
        accepting_colleges = colleges_el.inner_text().strip() if colleges_el else "N/A"

        seats_el = exam.query_selector("div.offline ul li:nth-child(6)")
        total_seats = seats_el.inner_text().strip() if seats_el else "N/A"

        exam_link = format_exam_link(title, base_url) if title != "N/A" else "N/A"

        exams.append({
            "title": title,
            "application_date": application_date,
            "exam_link": exam_link,
            "exam_type": exam_type,
            "exam_level": exam_level,
            "frequency": frequency,
            "conducting_body": conducting_body,
            "accepting_colleges": accepting_colleges,
            "total_seats": total_seats
        })
    
    return exams

def scrape_all_exams(category: str):
    """Scrapes all exam details from the selected category including pagination."""
    if category not in CATEGORY_URLS:
        return []
    
    base_url = CATEGORY_URLS[category]
    url = base_url
    exams = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        while url:
            page.goto(url, timeout=60000)
            page.wait_for_selector("div.exam_listing_info", timeout=10000)
            exams.extend(scrape_exams_from_page(page, base_url))
            
            next_page_el = page.query_selector("a.pagination_list_last")
            url = next_page_el.get_attribute("href") if next_page_el else None
        
        browser.close()
    
    return exams

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "exams": [], "category": None})

@app.get("/exams/{category}")
def get_exams(request: Request, category: str):
    if category not in CATEGORY_URLS:
        return templates.TemplateResponse("index.html", {"request": request, "exams": [], "category": "Invalid Category"})
    
    exams = scrape_all_exams(category)
    return templates.TemplateResponse("index.html", {"request": request, "exams": exams, "category": category})
