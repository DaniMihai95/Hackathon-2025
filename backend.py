import os
import sys
import smtplib
import ssl
from email.message import EmailMessage

import re
import json

from openai import OpenAI
import os

from fastapi.responses import JSONResponse

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from PC.GPU import RTX_TEMPLATE

from utils.email_reading import list_inbox_emails, get_email_content_by
from utils.email_writing import send_official_email
from utils.basic import get_product_specs


#############################
# BACKEND (FastAPI) SECTION
#############################
app = FastAPI()

# ====== Configuration for Email/IMAP/SMTP ======
EMAIL_USER = 'mhackathon2o25@gmail.com'
EMAIL_PASSWORD = 'axdv gkxt dpax pmxd'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = '587'
IMAP_SERVER = 'imap.gmail.com'
IMAP_PORT = '993'

# ====== LLM (OpenAI) Config ======
client = OpenAI(api_key='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')


# ====== Email Sending (Official via SMTP) ======
def send_official_email(to_address: str, subject: str, body: str):
    """
    Sends an email via SMTP with the given parameters.
    You must have your EMAIL_USER, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT set.
    """
    if not all([EMAIL_USER, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT]):
        raise ValueError("Email environment variables are not fully set.")

    msg = EmailMessage()
    msg["From"] = EMAIL_USER
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        # SMTP over TLS
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls(context=context)
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        raise RuntimeError(f"Failed to send email: {e}")

# ====== Models ======
class ProductRequest(BaseModel):
    product_name: str

class EmailRequest(BaseModel):
    company_name: str
    company_email: str
    product_name: str

class RetrieveEmailRequest(BaseModel):
    sender: str
    title: str


# ====== FastAPI Endpoints ======

@app.post("/api/scrape_specs")
def scrape_specs(req: ProductRequest):
    """
    Scrape product specifications from trusted sites and return the raw text.
    """
    product = req.product_name
    specs_text = get_product_specs(product)
    return {"scraped_specs": specs_text}


@app.post("/api/fill_template")
def fill_template(req: ProductRequest):
    """
    Use GPT-4 (ChatCompletion) to fill in the RTX template with relevant specs.
    If unknown, leave blank.
    """
    product = req.product_name
    if 'rtx' in product.lower():
        template_json = RTX_TEMPLATE

    # Create a prompt that instructs the model how to fill the template
    specs_text = get_product_specs(product)
    user_prompt = (
        f"You are a helpful AI. We have the following product: {product}.\n"
        "We scraped these specifications:\n\n"
        f"{specs_text}\n\n"
        "Using this information, fill in the JSON template as best as you can. You must focus on filling it in!!!\n"
        "If something is unknown, leave it blank.\n\n"
        f"Template:\n{template_json}\n\n"
        "Return only valid JSON."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_prompt}
        ],
    )

    if not response.choices or not response.choices[0].message:
        return JSONResponse(status_code=500, content={"error": "Invalid response from LLM: No choices or message content available."})

    content = response.choices[0].message.content if response.choices[0].message.content else ""

    if not content.strip():
        return JSONResponse(status_code=500, content={"error": "Response content is empty or invalid."})

    # Remove markdown code block delimiters
    json_string = re.sub(r"^```json|\n```$", "", content.strip(), flags=re.MULTILINE)

    try:
        json_data = json.loads(json_string)
    except json.JSONDecodeError as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to parse JSON: {str(e)}"})

    with open("output.json", "w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, indent=4)

    return JSONResponse(
        status_code=200,
        content={
            "message": "Extracted JSON successfully",
            "data": json_data
        }
    )

@app.post("/api/send_email")
def api_send_email(req: EmailRequest):
    """
    Officially send an email to a company to request product specifications.
    """
    to_address = f"<{req.company_email}>"
    subject = f"Request for {req.product_name} Specs"
    body = (
        f"Hello {req.company_name},\n\n"
        f"We would love to receive detailed specifications for your upcoming product: {req.product_name}.\n"
        "Please let us know as soon as possible.\n\n"
        "Best regards,\nMegekko"
    )

    try:
        send_official_email(to_address, subject, body)
        return {
            "status": "Email sent successfully",
            "recipient": to_address,
            "subject": subject,
            "body": body
        }
    except Exception as e:
        return {"status": "Failed to send email", "error": str(e)}


@app.get("/api/get_inbox")
def api_get_inbox():
    """
    Return a list of emails in the real IMAP inbox (sender + subject),
    newest first (index 0 is the newest).
    """
    try:
        inbox_list = list_inbox_emails()
        return {"inbox": inbox_list}
    except Exception as e:
        return {"error": str(e), "inbox": []}


@app.post("/api/get_email_content")
def api_get_email_content(req: RetrieveEmailRequest):
    """
    Return the full content of an email based on the sender and title.
    """
    try:
        content = get_email_content_by(req.sender, req.title)
        return {"content": content}
    except Exception as e:
        return {"error": str(e), "content": ""}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
