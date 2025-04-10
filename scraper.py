import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from urllib.parse import urljoin, urlparse
import logging
import time
from requests.exceptions import RequestException
import phonenumbers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GeneralizedLeadGenScraper:
    def __init__(self, max_pages=15, delay=1):
        # Initialize the scraper with configuration settings
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.max_pages = max_pages
        self.delay = delay
        self.visited_urls = set()
        self.all_contacts = []
        self.domain = ""
        self.page_data = {}

    def fetch(self, url):
        # Fetch a URL with error handling and return the HTML content
        try:
            logger.info(f"Fetching: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def is_valid_url(self, url):
        # Check if URL belongs to the same domain and is not already visited
        parsed = urlparse(url)
        return parsed.netloc == self.domain and url not in self.visited_urls

    def is_high_value_url(self, url):
        # Identify URLs that are likely to contain contact information
        high_value_patterns = [
            r'/contact', r'/about', r'/team', r'/staff', r'/people',
            r'/leadership', r'/management', r'/directory', r'/faculty',
            r'/meet', r'/our-team', r'/who-we-are', r'/employees'
        ]
        
        url_lower = url.lower()
        for pattern in high_value_patterns:
            if re.search(pattern, url_lower):
                return True
        return False

    def extract_urls(self, soup, base_url):
        # Extract and prioritize URLs from a page, putting high-value URLs first
        urls = []
        high_priority_urls = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(base_url, href)
            
            if not full_url.startswith(('http://', 'https://')) or '#' in full_url:
                continue
                
            if self.is_valid_url(full_url):
                if self.is_high_value_url(full_url):
                    high_priority_urls.append(full_url)
                else:
                    urls.append(full_url)
        
        return high_priority_urls + urls

    def clean_text(self, text):
        # Remove extra whitespace and normalize text
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_emails(self, text):
        # Find and validate email addresses in text
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        valid_emails = []
        for email in emails:
            if len(email) <= 320 and '.' in email.split('@')[1]:
                valid_emails.append(email)
        
        return valid_emails

    def extract_phone_numbers(self, text, country=None):
        # Extract and validate phone numbers from text
        phone_patterns = [
            r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            r'\b\+\d{1,3}\s?\d{3,14}\b',
        ]
        
        potential_numbers = []
        for pattern in phone_patterns:
            potential_numbers.extend(re.findall(pattern, text))
            
        validated_numbers = []
        for number in potential_numbers:
            cleaned = re.sub(r'[^\d+]', '', number)
            
            try:
                if not cleaned.startswith('+') and country:
                    phone_obj = phonenumbers.parse(cleaned, country)
                else:
                    phone_obj = phonenumbers.parse(cleaned)
                
                if phonenumbers.is_valid_number(phone_obj):
                    formatted = phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                    validated_numbers.append(formatted)
            except:
                if len(cleaned) >= 10:  
                    validated_numbers.append(cleaned)
                    
        return validated_numbers

    def extract_names(self, soup):
        # Identify potential person names from HTML using multiple heuristics
        names = []
        
        person_elements = soup.find_all(itemtype=re.compile(r'schema.org/Person'))
        for elem in person_elements:
            name_elem = elem.find(itemprop="name")
            if name_elem:
                names.append(self.clean_text(name_elem.get_text()))
        
        for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'strong', 'span', 'div']):
            text = self.clean_text(elem.get_text())
            if len(text) > 40 or len(text) < 4:
                continue
                
            words = text.split()
            if 2 <= len(words) <= 3:
                if all(word[0].isupper() for word in words if len(word) > 1):
                    skip_words = ['home', 'about', 'contact', 'us', 'page', 'team', 'services']
                    if not any(word.lower() in skip_words for word in words):
                        names.append(text)
        
        for elem in soup.find_all(class_=re.compile(r'team|member|staff|person|profile|card|contact', re.I)):
            header = elem.find(['h2', 'h3', 'h4', 'strong'])
            if header:
                text = self.clean_text(header.get_text())
                if 4 <= len(text) <= 40 and 2 <= len(text.split()) <= 4:
                    names.append(text)
        
        unique_names = []
        for name in names:
            if name not in unique_names:
                unique_names.append(name)
                
        return unique_names

    def extract_linkedin_profiles(self, soup, base_url, text):
        # Find LinkedIn profile URLs from both HTML links and text content
        linkedin_links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            if 'linkedin.com/in/' in href or 'linkedin.com/company/' in href:
                full_url = urljoin(base_url, a['href'])
                linkedin_links.append(full_url)
        
        linkedin_text_pattern = r'linkedin\.com/(?:in|company)/[\w-]+'
        for match in re.findall(linkedin_text_pattern, text.lower()):
            linkedin_links.append(f"https://{match}")
        
        linkedin_links = list(set(linkedin_links))
        
        return linkedin_links

    def extract_job_titles(self, soup, text):
        # Extract job titles using patterns and structured data
        titles = []
        
        title_pattern = r'\b(?:CEO|CTO|CFO|COO|Director|Manager|VP|Vice President|President|Founder|Owner|Partner|Senior|Lead|Chief|Head|Principal)\s+(?:\w+\s+)*(?:Engineer|Developer|Designer|Architect|Consultant|Advisor|Analyst|Officer|Manager|Director)\b'
        
        for elem in soup.find_all(itemtype=re.compile(r'schema.org/Person')):
            job_elem = elem.find(itemprop="jobTitle")
            if job_elem:
                titles.append(self.clean_text(job_elem.get_text()))
        
        for elem in soup.find_all(class_=re.compile(r'team|member|staff|person|profile|card', re.I)):
            for child in elem.find_all(['p', 'span', 'div']):
                child_text = self.clean_text(child.get_text())
                if re.search(title_pattern, child_text) and len(child_text) < 100:
                    titles.append(child_text)
        
        for match in re.finditer(title_pattern, text):
            titles.append(match.group(0))
        
        titles = list(set(titles))
        
        return titles

    def associate_contacts_with_context(self, soup, url, emails, phones, linkedin_profiles, names, titles):
        # Connect contacts with their names, titles and other context
        contacts = []
        
        team_cards = soup.find_all(class_=re.compile(r'team|member|staff|person|profile|card', re.I))
        
        for card in team_cards:
            card_text = card.get_text()
            card_email = None
            card_phone = None
            card_linkedin = None
            card_name = None
            card_title = None
            
            name_elem = card.find(['h2', 'h3', 'h4', 'strong'])
            if name_elem:
                card_name = self.clean_text(name_elem.get_text())
                if len(card_name) > 40 or len(card_name.split()) > 4:
                    card_name = None
            
            card_emails = self.extract_emails(card_text)
            if card_emails:
                card_email = card_emails[0]
            
            card_phones = self.extract_phone_numbers(card_text)
            if card_phones:
                card_phone = card_phones[0]
            
            for a in card.find_all('a', href=True):
                if 'linkedin.com/in/' in a['href'].lower():
                    card_linkedin = urljoin(url, a['href'])
                    break
            
            title_pattern = r'\b(?:CEO|CTO|CFO|COO|Director|Manager|VP|Vice President|President|Founder|Owner|Partner|Senior|Lead|Chief|Head|Principal)\s+(?:\w+\s+)*(?:Engineer|Developer|Designer|Architect|Consultant|Advisor|Analyst|Officer|Manager|Director)\b'
            for p in card.find_all(['p', 'span', 'div']):
                p_text = self.clean_text(p.get_text())
                if re.search(title_pattern, p_text) and len(p_text) < 100:
                    card_title = p_text
                    break
            
            if card_email or card_phone or card_linkedin:
                contacts.append({
                    'name': card_name,
                    'email': card_email,
                    'phone': card_phone,
                    'linkedin': card_linkedin,
                    'title': card_title,
                    'source': url
                })
                
                if card_email and card_email in emails:
                    emails.remove(card_email)
                if card_phone and card_phone in phones:
                    phones.remove(card_phone)
                if card_linkedin and card_linkedin in linkedin_profiles:
                    linkedin_profiles.remove(card_linkedin)
        
        for email in emails:
            name_guess = None
            
            email_name_part = email.split('@')[0]
            if '.' in email_name_part:
                parts = email_name_part.split('.')
                if len(parts) == 2 and all(part.isalpha() for part in parts):
                    name_guess = f"{parts[0].capitalize()} {parts[1].capitalize()}"
            
            contacts.append({
                'name': name_guess,
                'email': email,
                'phone': None,
                'linkedin': None,
                'title': None,
                'source': url
            })
        
        for phone in phones:
            contacts.append({
                'name': None,
                'email': None,
                'phone': phone,
                'linkedin': None,
                'title': None,
                'source': url
            })
        
        for linkedin in linkedin_profiles:
            name_guess = None
            match = re.search(r'linkedin\.com/in/([\w-]+)', linkedin)
            if match:
                profile_id = match.group(1).replace('-', ' ').title()
                if not any(word.lower() in ['page', 'profile', 'company', 'business'] for word in profile_id.split()):
                    name_guess = profile_id
            
            contacts.append({
                'name': name_guess,
                'email': None,
                'phone': None,
                'linkedin': linkedin,
                'title': None,
                'source': url
            })
        
        return contacts

    def parse_contacts(self, html, base_url):
        # Extract all contact information from a page and associate related data
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        emails = self.extract_emails(text)
        phones = self.extract_phone_numbers(text)
        names = self.extract_names(soup)
        linkedin_links = self.extract_linkedin_profiles(soup, base_url, text)
        titles = self.extract_job_titles(soup, text)
        
        contacts = self.associate_contacts_with_context(
            soup, base_url, emails, phones, linkedin_links, names, titles
        )
        
        logger.info(f"Found {len(emails)} emails, {len(phones)} phones, "
                    f"{len(linkedin_links)} LinkedIn profiles on {base_url}")
        
        return contacts

    def crawl(self, url):
        # Process a single URL, extract contacts, and find links to crawl next
        html = self.fetch(url)
        if not html:
            return None
        
        self.visited_urls.add(url)
        
        contacts = self.parse_contacts(html, url)
        
        self.all_contacts.extend(contacts)
        
        self.page_data[url] = {
            'contacts': contacts,
            'timestamp': time.time()
        }
        
        soup = BeautifulSoup(html, 'html.parser')
        return self.extract_urls(soup, url)

    def crawl_site(self, start_url):
        # Systematically crawl a website to find contact information
        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        
        to_crawl = [start_url]
        
        html = self.fetch(start_url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            high_priority_urls = [url for url in self.extract_urls(soup, start_url) 
                                 if self.is_high_value_url(url)]
            
            to_crawl = high_priority_urls + [url for url in to_crawl if url not in high_priority_urls]
        
        while to_crawl and len(self.visited_urls) < self.max_pages:
            current_url = to_crawl.pop(0)
            
            if current_url in self.visited_urls:
                continue
            
            new_urls = self.crawl(current_url)
            if new_urls:
                high_value = []
                normal_value = []
                
                for url in new_urls:
                    if url not in self.visited_urls and url not in to_crawl:
                        if self.is_high_value_url(url):
                            high_value.append(url)
                        else:
                            normal_value.append(url)
                
                to_crawl = high_value + to_crawl + normal_value
            
            time.sleep(self.delay)
        
        return self.all_contacts

    def organize_results(self):
        # Convert collected contacts into a structured DataFrame
        if not self.all_contacts:
            return pd.DataFrame()
        
        organized_data = []
        
        for contact in self.all_contacts:
            if contact['email']:
                organized_data.append({
                    'Contact Type': 'Email',
                    'Value': contact['email'],
                    'Name': contact['name'] or '',
                    'Job Title': contact['title'] or '',
                    'Source URL': contact['source']
                })
            
            if contact['phone']:
                organized_data.append({
                    'Contact Type': 'Phone',
                    'Value': contact['phone'],
                    'Name': contact['name'] or '',
                    'Job Title': contact['title'] or '',
                    'Source URL': contact['source']
                })
            
            if contact['linkedin']:
                organized_data.append({
                    'Contact Type': 'LinkedIn',
                    'Value': contact['linkedin'],
                    'Name': contact['name'] or '',
                    'Job Title': contact['title'] or '',
                    'Source URL': contact['source']
                })
        
        result_df = pd.DataFrame(organized_data)
        
        result_df = result_df.drop_duplicates(subset=['Contact Type', 'Value'])
        
        result_df = result_df.sort_values(['Contact Type', 'Name'])
        
        return result_df

    def scrape(self, url):
        # Main method that orchestrates the entire scraping process
        logger.info(f"Starting to scrape {url}")
        
        self.visited_urls = set()
        self.all_contacts = []
        self.page_data = {}
        
        default_country = None
        domain_tld = urlparse(url).netloc.split('.')[-1]
        country_map = {
            'us': 'US', 'uk': 'GB', 'ca': 'CA', 'au': 'AU', 
            'de': 'DE', 'fr': 'FR', 'in': 'IN'
        }
        if domain_tld in country_map:
            default_country = country_map[domain_tld]
        
        self.crawl_site(url)
        
        result_df = self.organize_results()
        
        email_count = len(result_df[result_df['Contact Type'] == 'Email'])
        phone_count = len(result_df[result_df['Contact Type'] == 'Phone'])
        linkedin_count = len(result_df[result_df['Contact Type'] == 'LinkedIn'])
        
        logger.info(f"Scraping completed: Found {email_count} unique emails, "
                   f"{phone_count} unique phone numbers, and {linkedin_count} LinkedIn profiles")
        
        return result_df