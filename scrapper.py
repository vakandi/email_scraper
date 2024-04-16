from googlesearch import search as googlesearch
import sys
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time
import urllib.request
from urllib.parse import urlparse
import os
import xml.etree.ElementTree as ET
current_directory = os.getcwd()
file_path = os.path.join(current_directory, 'emails.list')
email_count = 0
visited_pages = set()
max_sitemap_pages = 60
#
def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def get_sitemap(url):
    try:
        sitemap_url = urljoin(url, '/sitemap.xml')
        response = requests.get(sitemap_url)
        if response.status_code == 200:
            return response.content
        else:
            print("Trying robots.txt")
            robots_url = urljoin(url, '/robots.txt')
            response = requests.get(robots_url)
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if 'Sitemap' in line:
                        sitemap_url = line.split(' ')[1]
                        response = requests.get(sitemap_url)
                        if response.status_code == 200:
                            return response.content
                        else:
                            print(f"Failed to retrieve sitemap from {sitemap_url}")
            else:
                print(f"Failed to retrieve robots.txt, trying sitemap-index.xml")
                sitemap_url = urljoin(url, '/sitemap-index.xml')
                response = requests.get(sitemap_url)
                if response.status_code == 200:
                    return response.content
                else:
                    #try to get sitemap from /sitemap_index.xml
                    print(f"FTrying sitemap_index.xml")
                    sitemap_url = urljoin(url, '/sitemap_index.xml')
                    response = requests.get(sitemap_url)
                    if response.status_code == 200:
                        return response.content
                    else:
                        print(f"Trying sitemap.xml.gz")
                        sitemap_url = urljoin(url, '/sitemap.xml.gz')
                        response = requests.get(sitemap_url)
                        if response.status_code == 200:
                            return response.content
                        else:
                            print(f"Trying sitemap.php")
                            sitemap_url = urljoin(url, '/sitemap.php')
                            response = requests.get(sitemap_url)
                            if response.status_code == 200:
                                return response.content
                            else:
                                print(f"Trying sitemap/sitemap.xml")
                                sitemap_url = urljoin(url, '/sitemap/sitemap.xml')
                                response = requests.get(sitemap_url)
                                if response.status_code == 200:
                                    return response.content
                                else:
                                    print(f"Trying sitemap.xml.gz")
                                    sitemap_url = urljoin(url, '/sitemap.xml.gz')
                                    response = requests.get(sitemap_url)
                                    if response.status_code == 200:
                                        return response.content
                                    else:
                                        return None
    except Exception as e:
        print(f"Failed to retrieve sitemap from {url}: {e}")
        print("Trying robots.txt")
    return None

def remove_duplicate_emails(emails):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines:
                email = line.split(",")[0]
                if email in emails:
                    emails.remove(email)
    except FileNotFoundError:
        pass


def extract_urls_from_sitemap(sitemap_content):
    urls = []
    try:
        root = ET.fromstring(sitemap_content)
        for child in root:
            if 'url' in child.tag:
                for subchild in child:
                    if 'loc' in subchild.tag:
                        urls.append(subchild.text)
    except Exception as e:
        print(f"Failed to extract URLs from sitemap: {e}")
    return urls

def process_website(url, title):
    """Function that visits a website and extracts emails from all pages recursively"""
    global email_count, visited_pages
    if url in visited_pages:
        return
    visited_pages.add(url)
    try:
        source = requests.get(url, timeout=5)
        soup = BeautifulSoup(source.text, 'lxml')
        find_emails = soup.find_all(text=re.compile('[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'))
        find_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', source.text)
        #remove duplicates
        find_emails = list(set(find_emails))
        #process the emails, if there is two special characters in the email, skip the email like .. or $$ or @@
        find_emails = [email for email in find_emails if email.count('.') < 2 and email.count('$') < 2 and email.count('@') < 2]
        #if therec is "yourdomain" in the email,remove it
        find_emails = [email for email in find_emails if "yourdomain" not in email]
        #remove duolicate in the file emails.list vy calling
        remove_duplicate_emails(find_emails)
        nb_email_found = len(find_emails)
        if nb_email_found > 0:
            print(f'__________________________________\nEmail(s) found : {find_emails}\n__________________________________')
        email_count += nb_email_found
        print(f'{nb_email_found} email(s) found on {url}')
        for email in find_emails:
            email_name = email.split("@")[0]
            if '.' in email_name:
                print(email_name)
                first_name, last_name = email_name.split('.')
            else:
                first_name = email_name
                last_name = None
            #get the domain name even if there is a - or any acceptable character accepted by domain providers
            domain = email.split("@")[1]
            #if  domain finish by .png or .jpg skip the loop
            if domain.endswith('.png') or domain.endswith('.jpg'):
                continue
            try:
                with open(file_path, "a", encoding="utf-8") as file:
                    file.write(f"{email},{domain},{first_name},{last_name},{title}\n")
                    print(f"{email} saved to emails.list")
            except OSError:
                print(f"Cannot write to {file_path}. Do you have permission to create files in this directory?")
        
        for a in soup.find_all("a", href=True):
            if is_valid_url(a["href"]) and not re.search("^(http|www)", a["href"]):
                new_link = urljoin(url, a["href"])
                #check if the link is not already visited and valid
                if new_link not in visited_pages and is_valid_url(new_link):
                    print(f'Searching for emails on {new_link}')
                    process_website(new_link, title)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

choice_arg = input("[1] Simple search\n[2] Domain Search\n")

if choice_arg == "1":
    search_string = input("Enter the search string:")
    number_of_results = input("How many Google results do you want? ")
    number_of_results = int(number_of_results)
    #results = list(googlesearch(search_string, num_results=number_of_results))
    results = list(googlesearch(search_string, stop=number_of_results))
    print("Searching... " + search_string)
    print(f'{len(results)} websites found')
elif choice_arg == "2":
    search_string = input("Enter the domain:")
    number_of_results = input("How many Google results do you want? ")
    number_of_results = int(number_of_results)
    url = f"https://www.google.com/search?q=site%3A{search_string}"
    results = requests.get(url)
    print("Domain searching... " + search_string)
else:
    print("Invalid search type. Please enter 1 for simple string search or 2 for domain search.")
    sys.exit()


for i, link in enumerate(results):
    print(f"Website {i + 1} / {len(results)}")
    print(f'Searching for emails on {link}')
    try:
        #get the domain of the website
        title = urlparse(link).netloc
        print(f":::: Domain : {title} ::::")
        if choice_arg == "2" or choice_arg == "1":
            process_website(link, title)
            sitemap_content = get_sitemap(link)
            if sitemap_content:
                print("Sitemap found")
                sitemap_urls = extract_urls_from_sitemap(sitemap_content)
                #for sitemap_url in sitemap_urls:
                for i, sitemap_url in enumerate(sitemap_urls):
                    print(f"Sitemap Page {i + 1} / {len(sitemap_urls)}")
                    process_website(sitemap_url, title)
                    if i > max_sitemap_pages:
                        print(f"Max sitemap pages reached. Skipping to the next website.")
                        break
        else:
            process_website(link, title)
    #except keyboard interrupt
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")
        sys.exit()
    except requests.exceptions.RequestException as e:
        print(f"Couldn't connect to {link}. Error: {e}")

print(f'{email_count} email(s) found in total')
