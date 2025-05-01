
import os
import time
import re
import json
from datetime import datetime
from typing import List, Dict, Type

import pandas as pd
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, create_model
import html2text
import tiktoken

from dotenv import find_dotenv, load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
from io import BytesIO
import pytesseract
from twocaptcha import TwoCaptcha
from openai import OpenAI
import chromedriver_autoinstaller
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
dotenvpath=find_dotenv()
load_dotenv(dotenvpath)
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
CAPTCHA=os.getenv("CAPTCHA")


def setup_selenium():
    options = Options()

    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    service = Service(r"./chromedriver-win64/chromedriver.exe")  
    chromedriver_autoinstaller.install()  
    driver = webdriver.Chrome()
    return driver

def handle_cookies_and_recaptcha(driver, page_url):

    try:
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accepteren')]"))
        )
        cookie_button.click()
        print("Cookie consent accepted.")
    except Exception as e:
        print("Cookie consent not found or already handled:", e)
    
    try:
        captcha_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='fundaCaptchaInput']"))
        )
        if captcha_container:
            print("reCAPTCHA (by id 'fundaCaptchaInput') detected, attempting to solve.")
            if not solve_recaptcha(driver, page_url):
                print("Failed to solve reCAPTCHA.")
    except Exception as e:

        try:
            recaptcha_present = driver.find_elements(By.XPATH, "//div[@class='g-recaptcha']")
            if recaptcha_present:
                print("reCAPTCHA (by class) detected, attempting to solve.")
                if not solve_recaptcha(driver, page_url):
                    print("Failed to solve reCAPTCHA.")
        except Exception as inner_e:
            print("Error checking for reCAPTCHA:", inner_e)



def solve_recaptcha(driver, page_url):

    try:

        captcha_container = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "fundaCaptchaInput"))
        )

        iframe = captcha_container.find_element(By.TAG_NAME, "iframe")
        src = iframe.get_attribute("src")
        print("Captcha iframe src:", src)
        parsed_url = urlparse(src)
        query_params = parse_qs(parsed_url.query)
        sitekey = query_params.get("k", [None])[0]
        if not sitekey:
            print("Sitekey could not be extracted from the iframe src.")
            return False
        print("Extracted sitekey:", sitekey)
    except Exception as e:
        print("Error locating captcha container/iframe:", e)
        return False


    solver = TwoCaptcha(CAPTCHA) 
    try:

        result = solver.recaptcha(sitekey=sitekey, url=page_url)
        token = result.get('code')
        if not token:
            print("2Captcha did not return a token:", result)
            return False
        print("2Captcha token obtained:", token)
    except Exception as e:
        print("2Captcha error:", e)
        return False

    try:

        driver.execute_script(
            "document.getElementById('g-recaptcha-response').value = arguments[0];", token
        )
        driver.execute_script(
            "document.getElementById('g-recaptcha-response').style.display = 'block';"
        )
        print("Token injected into g-recaptcha-response.")
        
        driver.execute_script(
            "if (typeof fundaCaptchaDoneCallback === 'function') { fundaCaptchaDoneCallback(); }"
        )
        print("Attempted to trigger fundaCaptchaDoneCallback.")
        return True
    except Exception as e:
        print("Failed to inject token or trigger callback:", e)
        return False
    try:
        driver.execute_script("document.getElementById('g-recaptcha-response').innerHTML = arguments[0];", token)
        print("2Captcha token injected successfully.")
        return True
    except Exception as e:
        print("Failed to inject token:", e)
        return False

def extract_text_from_image(captcha_image):

    png = captcha_image.screenshot_as_png
    image = Image.open(BytesIO(png))
    image = image.convert("L")
    text = pytesseract.image_to_string(image)
    return text.strip()
def construct_funda_page_url(base_url: str, page_num: int) -> str:
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query["search_result"] = [str(page_num)]
    new_query = urlencode(query, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
def fetch_pages_html_selenium(base_url: str, pages: int = 6, fetch_all: bool = False) -> List[str]:
    driver = webdriver.Chrome()
    pages_html = []
    try:
        driver.get(base_url)
        handle_cookies_and_recaptcha(driver, base_url)
        driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
        time.sleep(60) 
        pages_html.append(driver.page_source)

        total_pages = max(1, pages)
        for page_num in range(2, total_pages + 1):
            if "funda.nl" in base_url:
                page_url = construct_funda_page_url(base_url, page_num)
            else:
                page_url = base_url.rstrip('/') + f"/p{page_num}/"
            driver.get(page_url)
            handle_cookies_and_recaptcha(driver, page_url)
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
            time.sleep(5)
            pages_html.append(driver.page_source)
    finally:
        driver.quit()
    return pages_html


def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser') 
    for element in soup.find_all(['header', 'footer']):
        element.decompose()
    return str(soup)


def html_to_markdown_with_readability(html_content):
    cleaned_html = clean_html(html_content)  
    markdown_converter = html2text.HTML2Text()
    markdown_converter.ignore_links = False
    markdown_content = markdown_converter.handle(cleaned_html)
    
    return markdown_content


pricing = {
    "gpt-4o-mini": {
        "input": 0.150 / 1_000_000,  # $0.150 per 1M input tokens
        "output": 0.600 / 1_000_000, # $0.600 per 1M output tokens
    },
    "gpt-4o-2024-08-06": {
        "input": 2.5 / 1_000_000,  # $0.150 per 1M input tokens
        "output": 10 / 1_000_000, # $0.600 per 1M output tokens
    },
    "gpt-4.5-preview":{
        "input": 2.5 / 1_000_000,  # $0.150 per 1M input tokens
        "output": 10 / 1_000_000,
    },
     "o1":{
        "input": 2.5 / 1_000_000,  # $0.150 per 1M input tokens
        "output": 10 / 1_000_000,
    },
      "o3-mini":{
        "input": 2.5 / 1_000_000,  # $0.150 per 1M input tokens
        "output": 10 / 1_000_000,
    },

}

model_used="gpt-4o-mini"
    
def save_raw_data(raw_data, timestamp, output_folder='output'):
    os.makedirs(output_folder, exist_ok=True)
    raw_output_path = os.path.join(output_folder, f'rawData_{timestamp}.md')
    with open(raw_output_path, 'w', encoding='utf-8') as f:
        f.write(raw_data)
    print(f"Raw data saved to {raw_output_path}")
    return raw_output_path


def remove_urls_from_file(file_path):

    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    base, ext = os.path.splitext(file_path)
    new_file_path = f"{base}_cleaned{ext}"
    with open(file_path, 'r', encoding='utf-8') as file:
        markdown_content = file.read()
    cleaned_content = re.sub(url_pattern, '', markdown_content)
    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.write(cleaned_content)
    print(f"Cleaned file saved as: {new_file_path}")
    return cleaned_content


def create_dynamic_listing_model(field_names: List[str]) -> Type[BaseModel]:
    field_definitions = {field: (str, ...) for field in field_names}
    return create_model('DynamicListingModel', **field_definitions)


def create_listings_container_model(listing_model: Type[BaseModel]) -> Type[BaseModel]:
    return create_model('DynamicListingsContainer', listings=(List[listing_model], ...))


def trim_to_token_limit(text, model, max_tokens=20000000):
    encoder = tiktoken.encoding_for_model(model)
    tokens = encoder.encode(text)
    if len(tokens) > max_tokens:
        trimmed_text = encoder.decode(tokens[:max_tokens])
        return trimmed_text
    return text

def format_data(data, DynamicListingsContainer):
    client = OpenAI(api_key=OPENAI_API_KEY)
    system_message = """You are an intelligent text extraction and conversion assistant. Your task is to extract literally all structured information 
                        from the given text and convert it into a pure JSON format. The JSON should contain only the structured data extracted from the text, 
                        with no additional commentary, explanations, or extraneous information. 
                        You could encounter cases where you can't find the data of the fields you have to extract or the data will be in a foreign language.
                        Please process the following text and provide the output in pure JSON format with no words before or after the JSON:"""

    user_message = f"Extract the following information from the provided text:\nPage content:\n\n{data}"
    print(user_message)
    completion = client.beta.chat.completions.parse(
        model=model_used,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        response_format=DynamicListingsContainer
    )
    print(completion.choices[0].message.parsed)
    return completion.choices[0].message.parsed
    


def save_formatted_data(formatted_data, timestamp, output_folder='output'):
    import os, json, pandas as pd
    os.makedirs(output_folder, exist_ok=True)

    formatted_data_dict = formatted_data.dict() if hasattr(formatted_data, 'dict') else formatted_data

    json_output_path = os.path.join(output_folder, f'sorted_data_{timestamp}.json')
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_data_dict, f, indent=4)
    print(f"Formatted data saved to JSON at {json_output_path}")

    if isinstance(formatted_data_dict, dict) and "listings" in formatted_data_dict:
        data_for_df = formatted_data_dict["listings"]
    elif isinstance(formatted_data_dict, dict):

        data_for_df = next(iter(formatted_data_dict.values()))
    elif isinstance(formatted_data_dict, list):
        data_for_df = formatted_data_dict
    else:
        raise ValueError("Formatted data is neither a dictionary nor a list, cannot convert to DataFrame")

    try:
       
        df = pd.DataFrame(data_for_df)
        print("DataFrame created successfully. Here's the head:")
        print(df.head())
        
        excel_output_path = os.path.join(output_folder, f'sorted_data_{timestamp}.xlsx')
        
     
        with pd.ExcelWriter(excel_output_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Results')
            workbook  = writer.book
            worksheet = writer.sheets['Results']
    
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
    
            for col_num, col_name in enumerate(df.columns.values):
                worksheet.write(0, col_num, col_name, header_format)
                col_width = max(df[col_name].astype(str).map(len).max(), len(col_name)) + 2
                worksheet.set_column(col_num, col_num, col_width)
                
        abs_path = os.path.abspath(excel_output_path)
        file_size = os.path.getsize(abs_path)
        print(f"Excel file saved successfully at {abs_path} (size: {file_size} bytes)")
        
        return df
    except Exception as e:
        print(f"Error creating DataFrame or saving Excel: {str(e)}")
        return None

def calculate_price(input_text, output_text, model=model_used):
    # Initialize the encoder for the specific model
    encoder = tiktoken.encoding_for_model(model)
    
    # Encode the input text to get the number of input tokens
    input_token_count = len(encoder.encode(input_text))
    
    # Encode the output text to get the number of output tokens
    output_token_count = len(encoder.encode(output_text))
    
    # Calculate the costs
    input_cost = input_token_count * pricing[model]["input"]
    output_cost = output_token_count * pricing[model]["output"]
    total_cost = input_cost + output_cost
    
    return input_token_count, output_token_count, total_cost
