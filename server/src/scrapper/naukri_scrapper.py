"""
Naukri.com Job Scraper
"""

import time
import json
from typing import List, Dict, Tuple
from datetime import datetime
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

from src.utils.logger import setup_logger


class NaukriScraper:
    """Scraper for Naukri.com job listings"""
    
    BASE_URL = "https://www.naukri.com"
    
    def __init__(self, config: Dict):
        """Initialize the scraper"""
        self.logger = setup_logger(__name__)
        self.config = config
        self.driver = None
        
    def _setup_driver(self):
        """Setup Chrome driver with options"""
        options = Options()
        
        if self.config.get('headless', True):
            options.add_argument('--headless')
            
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User agent
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(
            ChromeDriverManager().install(),
            options=options
        )
        self.driver.implicitly_wait(10)
        
    def _close_driver(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            
    def _build_search_url(self, keywords: str, location: str, experience: Tuple[int, int]) -> str:
        """Build search URL with parameters"""
        params = []
        
        # Keywords
        if keywords:
            params.append(f"k={quote(keywords)}")
            
        # Location
        if location:
            params.append(f"l={quote(location)}")
            
        # Experience
        if experience:
            params.append(f"experience={experience[0]}-{experience[1]}")
            
        query_string = "&".join(params)
        return f"{self.BASE_URL}/jobs?{query_string}"
    
    def _wait_for_element(self, by: By, value: str, timeout: int = 10):
        """Wait for element to be present"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.logger.warning(f"Timeout waiting for element: {value}")
            return None
            
    def _extract_job_details(self, job_element) -> Dict:
        """Extract job details from job card element"""
        job_data = {}
        
        try:
            # Job title
            title_elem = job_element.find_element(By.CSS_SELECTOR, '.title')
            job_data['title'] = title_elem.text.strip()
            job_data['url'] = title_elem.get_attribute('href')
            
            # Company name
            try:
                company_elem = job_element.find_element(By.CSS_SELECTOR, '.comp-name')
                job_data['company'] = company_elem.text.strip()
            except NoSuchElementException:
                job_data['company'] = 'Not specified'
                
            # Location
            try:
                location_elem = job_element.find_element(By.CSS_SELECTOR, '.loc-wrap span')
                job_data['location'] = location_elem.text.strip()
            except NoSuchElementException:
                job_data['location'] = 'Not specified'
                
            # Experience
            try:
                exp_elem = job_element.find_element(By.CSS_SELECTOR, '.exp-wrap span')
                job_data['experience'] = exp_elem.text.strip()
            except NoSuchElementException:
                job_data['experience'] = 'Not specified'
                
            # Salary
            try:
                salary_elem = job_element.find_element(By.CSS_SELECTOR, '.sal-wrap span')
                job_data['salary'] = salary_elem.text.strip()
            except NoSuchElementException:
                job_data['salary'] = 'Not disclosed'
                
            # Skills
            try:
                skills_elem = job_element.find_elements(By.CSS_SELECTOR, '.tags-gt li')
                job_data['skills'] = [skill.text.strip() for skill in skills_elem]
            except NoSuchElementException:
                job_data['skills'] = []
                
            # Posted date
            try:
                posted_elem = job_element.find_element(By.CSS_SELECTOR, '.job-post-day')
                job_data['posted_date'] = posted_elem.text.strip()
            except NoSuchElementException:
                job_data['posted_date'] = 'Not specified'
                
            # Job ID (from URL or data attribute)
            job_data['job_id'] = self._extract_job_id(job_data.get('url', ''))
            
            # Timestamp
            job_data['scraped_at'] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Error extracting job details: {e}")
            
        return job_data
    
    def _extract_job_id(self, url: str) -> str:
        """Extract job ID from URL"""
        if not url:
            return ''
            
        # Naukri job URLs typically have pattern: /job-listings-xyz-123456789
        parts = url.split('-')
        if parts:
            return parts[-1].split('?')[0]
        return ''
        
    def _scrape_job_description(self, job_url: str) -> str:
        """Scrape full job description from job page"""
        try:
            self.driver.get(job_url)
            time.sleep(2)  # Wait for page load
            
            # Wait for job description
            desc_elem = self._wait_for_element(By.CSS_SELECTOR, '.job-desc')
            if desc_elem:
                return desc_elem.text.strip()
                
        except Exception as e:
            self.logger.error(f"Error scraping job description: {e}")
            
        return ''
    
    def search_jobs(self, keywords: str, location: str = '', 
                   experience_range: Tuple[int, int] = (0, 20),
                   max_pages: int = 5) -> List[Dict]:
        """Search for jobs on Naukri"""
        self.logger.info(f"Searching jobs: {keywords} in {location}")
        
        jobs = []
        
        try:
            self._setup_driver()
            
            # Build and navigate to search URL
            search_url = self._build_search_url(keywords, location, experience_range)
            self.logger.debug(f"Search URL: {search_url}")
            self.driver.get(search_url)
            
            # Wait for job listings to load
            self._wait_for_element(By.CSS_SELECTOR, '.list article')
            
            page = 1
            while page <= max_pages:
                self.logger.info(f"Scraping page {page}")
                
                # Get all job cards on current page
                job_elements = self.driver.find_elements(By.CSS_SELECTOR, '.list article')
                
                for job_elem in job_elements:
                    job_data = self._extract_job_details(job_elem)
                    
                    if job_data and job_data.get('title'):
                        # Optionally scrape full job description
                        if self.config.get('scrape_full_description', False):
                            job_data['description'] = self._scrape_job_description(job_data['url'])
                            
                        jobs.append(job_data)
                        
                # Check for next page
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, '.fright.btn-secondary.br2')
                    if 'disabled' in next_button.get_attribute('class'):
                        break
                        
                    next_button.click()
                    time.sleep(2)  # Wait for page load
                    page += 1
                    
                except NoSuchElementException:
                    self.logger.info("No more pages")
                    break
                    
        except Exception as e:
            self.logger.error(f"Error during job search: {e}")
            
        finally:
            self._close_driver()
            
        self.logger.info(f"Scraped {len(jobs)} jobs")
        return jobs
    
    def scrape_job_details(self, job_url: str) -> Dict:
        """Scrape detailed information from a specific job page"""
        self.logger.info(f"Scraping job details: {job_url}")
        
        job_details = {}
        
        try:
            self._setup_driver()
            self.driver.get(job_url)
            
            # Wait for page load
            self._wait_for_element(By.CSS_SELECTOR, '.jd-header')
            
            # Parse page with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Job title
            title_elem = soup.select_one('.jd-header h1')
            if title_elem:
                job_details['title'] = title_elem.text.strip()
                
            # Company
            company_elem = soup.select_one('.jd-header .comp-name')
            if company_elem:
                job_details['company'] = company_elem.text.strip()
                
            # Experience, salary, location
            info_elems = soup.select('.jd-header .exp-sal-loc span')
            if len(info_elems) >= 3:
                job_details['experience'] = info_elems[0].text.strip()
                job_details['salary'] = info_elems[1].text.strip()
                job_details['location'] = info_elems[2].text.strip()
                
            # Job description
            desc_elem = soup.select_one('.job-desc')
            if desc_elem:
                job_details['description'] = desc_elem.text.strip()
                
            # Key skills
            skills_elems = soup.select('.key-skill a')
            job_details['skills'] = [skill.text.strip() for skill in skills_elems]
            
            # Additional details
            details_section = soup.select('.detail span')
            for i in range(0, len(details_section), 2):
                if i + 1 < len(details_section):
                    key = details_section[i].text.strip().replace(':', '')
                    value = details_section[i + 1].text.strip()
                    job_details[key.lower().replace(' ', '_')] = value
                    
        except Exception as e:
            self.logger.error(f"Error scraping job details: {e}")
            
        finally:
            self._close_driver()
            
        return job_details