import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import json
from urllib.parse import urljoin, urlparse
import time

from app.config import settings

logger = logging.getLogger(__name__)

class TenderScraper:
    def __init__(self):
        self.session = None
        self.keywords = settings.tender_keywords
        self.portals = settings.tender_portals
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def search_all_portals(self) -> List[Dict]:
        """Search all configured tender portals for relevant opportunities"""
        all_tenders = []
        
        for region, portals in self.portals.items():
            logger.info(f"Searching {region} portals...")
            
            for portal_url in portals:
                try:
                    tenders = await self.search_portal(portal_url, region)
                    all_tenders.extend(tenders)
                    logger.info(f"Found {len(tenders)} tenders from {portal_url}")
                    
                    # Rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error searching portal {portal_url}: {str(e)}")
                    continue
        
        return all_tenders

    async def search_portal(self, portal_url: str, region: str) -> List[Dict]:
        """Search a specific portal for tenders"""
        domain = urlparse(portal_url).netloc
        
        # Route to specific scraper based on domain
        if "find-tender.service.gov.uk" in domain:
            return await self.scrape_uk_find_tender(portal_url, region)
        elif "contractsfinder.service.gov.uk" in domain:
            return await self.scrape_uk_contracts_finder(portal_url, region)
        elif "ted.europa.eu" in domain:
            return await self.scrape_ted_europa(portal_url, region)
        elif "tenders.gov.au" in domain:
            return await self.scrape_australia_tenders(portal_url, region)
        elif "gebiz.gov.sg" in domain:
            return await self.scrape_singapore_gebiz(portal_url, region)
        elif "eprocure.gov.in" in domain:
            return await self.scrape_india_eprocure(portal_url, region)
        else:
            # Generic scraper for other portals
            return await self.scrape_generic_portal(portal_url, region)

    async def scrape_uk_find_tender(self, base_url: str, region: str) -> List[Dict]:
        """Scrape UK Find a Tender service"""
        tenders = []
        
        try:
            # Search for education-related tenders
            search_terms = ["education", "learning", "software", "technology", "digital"]
            
            for term in search_terms:
                search_url = f"{base_url}Search?keywords={term}&locationLatLng=&services=&regions="
                
                async with self.session.get(search_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Extract tender cards
                        tender_cards = soup.find_all('article', class_='search-result')
                        
                        for card in tender_cards:
                            tender = self.parse_uk_tender_card(card, base_url, region)
                            if tender and self.is_relevant_tender(tender):
                                tenders.append(tender)
                
                # Rate limiting between searches
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error scraping UK Find a Tender: {str(e)}")
        
        return tenders

    def parse_uk_tender_card(self, card, base_url: str, region: str) -> Optional[Dict]:
        """Parse a UK tender card element"""
        try:
            title_elem = card.find('h2', class_='search-result__header')
            title = title_elem.get_text(strip=True) if title_elem else "No title"
            
            # Get tender URL
            link_elem = title_elem.find('a') if title_elem else None
            tender_url = urljoin(base_url, link_elem['href']) if link_elem else ""
            
            # Extract organization
            org_elem = card.find('p', class_='search-result__metadata')
            organization = org_elem.get_text(strip=True) if org_elem else "Unknown"
            
            # Extract description
            desc_elem = card.find('p', class_='search-result__summary')
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Extract value if available
            value_elem = card.find('dd', string=re.compile(r'£'))
            value = self.extract_value(value_elem.get_text() if value_elem else "")
            
            # Extract closing date
            date_elem = card.find('time')
            closing_date = self.parse_date(date_elem.get_text() if date_elem else "")
            
            return {
                "tender_id": self.generate_tender_id(tender_url),
                "title": title,
                "description": description,
                "organization": organization,
                "location": "United Kingdom",
                "country": "United Kingdom",
                "region": region,
                "value": value,
                "currency": "GBP",
                "closing_date": closing_date,
                "tender_url": tender_url,
                "source_portal": base_url,
                "publication_date": datetime.now(),
                "cpv_codes": [],
                "keywords": self.extract_keywords(f"{title} {description}")
            }
            
        except Exception as e:
            logger.warning(f"Error parsing UK tender card: {str(e)}")
            return None

    async def scrape_ted_europa(self, base_url: str, region: str) -> List[Dict]:
        """Scrape TED (Tenders Electronic Daily) - EU portal"""
        tenders = []
        
        try:
            # TED API search for education-related notices
            api_url = "https://ted.europa.eu/api/v3/notices/search"
            
            for keyword in ["education", "learning management", "educational software", "e-learning"]:
                params = {
                    "q": keyword,
                    "pageSize": 50,
                    "reverseOrder": True,
                    "scope": 3  # EU notices
                }
                
                async with self.session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for notice in data.get('results', []):
                            tender = self.parse_ted_notice(notice, region)
                            if tender and self.is_relevant_tender(tender):
                                tenders.append(tender)
                
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error scraping TED Europa: {str(e)}")
        
        return tenders

    def parse_ted_notice(self, notice: Dict, region: str) -> Optional[Dict]:
        """Parse a TED notice"""
        try:
            return {
                "tender_id": notice.get('id', ''),
                "title": notice.get('title', ''),
                "description": notice.get('shortDescription', ''),
                "organization": notice.get('organisation', {}).get('name', ''),
                "location": notice.get('organisation', {}).get('address', {}).get('town', ''),
                "country": notice.get('organisation', {}).get('address', {}).get('country', ''),
                "region": region,
                "value": self.extract_value(notice.get('value', {}).get('amount', '')),
                "currency": notice.get('value', {}).get('currency', 'EUR'),
                "closing_date": self.parse_date(notice.get('deadlineDate', '')),
                "tender_url": f"https://ted.europa.eu/udl?uri=TED:NOTICE:{notice.get('id', '')}",
                "source_portal": "https://ted.europa.eu/",
                "publication_date": self.parse_date(notice.get('publicationDate', '')),
                "cpv_codes": [cpv.get('code', '') for cpv in notice.get('cpvs', [])],
                "keywords": self.extract_keywords(f"{notice.get('title', '')} {notice.get('shortDescription', '')}")
            }
        except Exception as e:
            logger.warning(f"Error parsing TED notice: {str(e)}")
            return None

    async def scrape_australia_tenders(self, base_url: str, region: str) -> List[Dict]:
        """Scrape Australian Government Tenders"""
        tenders = []
        
        try:
            # Search Australian tenders
            search_url = f"{base_url}Search/KeywordSearch"
            
            for keyword in ["education", "learning", "software", "digital"]:
                params = {
                    "Keywords": keyword,
                    "AgencyId": "",
                    "CategoryId": "",
                    "State": "",
                    "SortBy": "PublishDate"
                }
                
                async with self.session.get(search_url, params=params) as response:
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Parse tender listings
                        tender_rows = soup.find_all('tr', class_='row-data')
                        
                        for row in tender_rows:
                            tender = self.parse_australia_tender_row(row, base_url, region)
                            if tender and self.is_relevant_tender(tender):
                                tenders.append(tender)
                
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error scraping Australian tenders: {str(e)}")
        
        return tenders

    def parse_australia_tender_row(self, row, base_url: str, region: str) -> Optional[Dict]:
        """Parse an Australian tender row"""
        try:
            cells = row.find_all('td')
            if len(cells) < 4:
                return None
            
            title_cell = cells[0]
            title = title_cell.get_text(strip=True)
            
            # Get tender URL
            link = title_cell.find('a')
            tender_url = urljoin(base_url, link['href']) if link else ""
            
            agency = cells[1].get_text(strip=True)
            category = cells[2].get_text(strip=True)
            close_date = cells[3].get_text(strip=True)
            
            return {
                "tender_id": self.generate_tender_id(tender_url),
                "title": title,
                "description": category,
                "organization": agency,
                "location": "Australia",
                "country": "Australia",
                "region": region,
                "value": None,
                "currency": "AUD",
                "closing_date": self.parse_date(close_date),
                "tender_url": tender_url,
                "source_portal": base_url,
                "publication_date": datetime.now(),
                "cpv_codes": [],
                "keywords": self.extract_keywords(f"{title} {category}")
            }
            
        except Exception as e:
            logger.warning(f"Error parsing Australian tender row: {str(e)}")
            return None

    async def scrape_generic_portal(self, portal_url: str, region: str) -> List[Dict]:
        """Generic scraper for other portals"""
        tenders = []
        
        try:
            async with self.session.get(portal_url) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Look for common tender-related elements
                    tender_elements = (
                        soup.find_all('div', class_=re.compile(r'tender|notice|opportunity')) +
                        soup.find_all('article') +
                        soup.find_all('tr', class_=re.compile(r'tender|row'))
                    )
                    
                    for element in tender_elements[:20]:  # Limit to first 20
                        tender = self.parse_generic_tender_element(element, portal_url, region)
                        if tender and self.is_relevant_tender(tender):
                            tenders.append(tender)
                            
        except Exception as e:
            logger.error(f"Error scraping generic portal {portal_url}: {str(e)}")
        
        return tenders

    def parse_generic_tender_element(self, element, portal_url: str, region: str) -> Optional[Dict]:
        """Parse a generic tender element"""
        try:
            # Extract text content
            text = element.get_text(strip=True)
            if len(text) < 50:  # Skip elements with too little content
                return None
            
            # Look for links
            links = element.find_all('a', href=True)
            tender_url = urljoin(portal_url, links[0]['href']) if links else portal_url
            
            # Extract title (usually first heading or strong text)
            title_elem = (
                element.find(['h1', 'h2', 'h3', 'h4']) or
                element.find('strong') or
                element.find('b')
            )
            title = title_elem.get_text(strip=True) if title_elem else text[:100]
            
            return {
                "tender_id": self.generate_tender_id(tender_url),
                "title": title,
                "description": text[:500],
                "organization": "Unknown",
                "location": "Unknown",
                "country": self.guess_country_from_url(portal_url),
                "region": region,
                "value": None,
                "currency": "USD",
                "closing_date": None,
                "tender_url": tender_url,
                "source_portal": portal_url,
                "publication_date": datetime.now(),
                "cpv_codes": [],
                "keywords": self.extract_keywords(text)
            }
            
        except Exception as e:
            logger.warning(f"Error parsing generic tender element: {str(e)}")
            return None

    def is_relevant_tender(self, tender: Dict) -> bool:
        """Check if tender is relevant to Wayground's keywords"""
        text = f"{tender.get('title', '')} {tender.get('description', '')}".lower()
        
        # Check for education-related keywords
        education_keywords = [
            'education', 'learning', 'school', 'student', 'teacher', 'curriculum',
            'e-learning', 'lms', 'digital', 'technology', 'software', 'ai',
            'artificial intelligence', 'edtech', 'pedagogy', 'training'
        ]
        
        return any(keyword.lower() in text for keyword in education_keywords)

    def extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        if not text:
            return []
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords

    def extract_value(self, value_text: str) -> Optional[float]:
        """Extract monetary value from text"""
        if not value_text:
            return None
        
        # Remove currency symbols and clean text
        cleaned = re.sub(r'[£$€¥₹]', '', value_text)
        cleaned = re.sub(r'[,\s]', '', cleaned)
        
        # Look for numeric values
        matches = re.findall(r'\d+(?:\.\d+)?', cleaned)
        
        if matches:
            try:
                value = float(matches[0])
                # Handle millions, thousands, etc.
                if 'million' in value_text.lower() or 'm' in value_text.lower():
                    value *= 1000000
                elif 'thousand' in value_text.lower() or 'k' in value_text.lower():
                    value *= 1000
                return value
            except ValueError:
                pass
        
        return None

    def parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse date from various formats"""
        if not date_text:
            return None
        
        # Common date formats
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d %H:%M:%S",
            "%d %B %Y",
            "%B %d, %Y",
            "%d %b %Y"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_text.strip(), fmt)
            except ValueError:
                continue
        
        return None

    def generate_tender_id(self, url: str) -> str:
        """Generate a unique tender ID from URL"""
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def guess_country_from_url(self, url: str) -> str:
        """Guess country from domain"""
        domain = urlparse(url).netloc.lower()
        
        country_mappings = {
            '.uk': 'United Kingdom',
            '.au': 'Australia',
            '.sg': 'Singapore',
            '.in': 'India',
            '.my': 'Malaysia',
            '.za': 'South Africa',
            '.ae': 'United Arab Emirates',
            '.de': 'Germany',
            '.fr': 'France',
            '.es': 'Spain',
            '.it': 'Italy',
            '.nl': 'Netherlands'
        }
        
        for tld, country in country_mappings.items():
            if tld in domain:
                return country
        
        return "Unknown"

    async def get_tender_details(self, tender_url: str) -> Dict:
        """Fetch detailed information for a specific tender"""
        try:
            async with self.session.get(tender_url) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract detailed information
                    details = {
                        "full_description": self.extract_full_description(soup),
                        "requirements": self.extract_requirements(soup),
                        "contact_info": self.extract_contact_info(soup),
                        "documents": self.extract_documents(soup)
                    }
                    
                    return details
                    
        except Exception as e:
            logger.error(f"Error fetching tender details from {tender_url}: {str(e)}")
        
        return {}

    def extract_full_description(self, soup) -> str:
        """Extract full description from tender page"""
        # Look for common description containers
        desc_selectors = [
            'div.description',
            'div.content',
            'div.detail',
            'section.description',
            'div[class*="description"]',
            'div[class*="detail"]'
        ]
        
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return ""

    def extract_requirements(self, soup) -> List[str]:
        """Extract requirements from tender page"""
        requirements = []
        
        # Look for requirement sections
        req_headers = soup.find_all(text=re.compile(r'requirement|specification|criteria', re.I))
        
        for header in req_headers:
            parent = header.parent
            if parent:
                # Look for lists or paragraphs near requirement headers
                lists = parent.find_next_siblings(['ul', 'ol', 'p'])
                for list_elem in lists[:3]:  # Limit to first 3
                    if list_elem.name in ['ul', 'ol']:
                        items = [li.get_text(strip=True) for li in list_elem.find_all('li')]
                        requirements.extend(items)
                    else:
                        requirements.append(list_elem.get_text(strip=True))
        
        return requirements[:10]  # Limit to first 10 requirements

    def extract_contact_info(self, soup) -> Dict:
        """Extract contact information"""
        contact = {}
        
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, soup.get_text())
        if emails:
            contact['email'] = emails[0]
        
        # Look for phone numbers
        phone_pattern = r'[\+]?[1-9]?[0-9]{7,15}'
        phones = re.findall(phone_pattern, soup.get_text())
        if phones:
            contact['phone'] = phones[0]
        
        return contact

    def extract_documents(self, soup) -> List[Dict]:
        """Extract downloadable documents"""
        documents = []
        
        # Look for download links
        doc_links = soup.find_all('a', href=re.compile(r'\.(pdf|doc|docx|xls|xlsx)$', re.I))
        
        for link in doc_links[:5]:  # Limit to first 5 documents
            documents.append({
                'title': link.get_text(strip=True),
                'url': link.get('href'),
                'type': link.get('href', '').split('.')[-1].upper()
            })
        
        return documents