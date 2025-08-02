#!/usr/bin/env python3
"""
Naukri Job Matcher - Main Entry Point
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper.naukri_scraper import NaukriScraper
from src.matcher.matcher import JobMatcher
from src.notifier.email_notifier import EmailNotifier
from src.notifier.desktop_notifier import DesktopNotifier
from src.database.db_manager import DatabaseManager
from src.utils.logger import setup_logger
from src.utils.helpers import load_config, load_environment


class NaukriJobMatcherApp:
    """Main application class for Naukri Job Matcher"""
    
    def __init__(self):
        """Initialize the application"""
        self.logger = setup_logger(__name__)
        self.config = load_config()
        load_environment()
        
        # Initialize components
        self.db = DatabaseManager()
        self.scraper = NaukriScraper(self.config['scraper'])
        self.matcher = JobMatcher(self.config['matcher'])
        self.email_notifier = EmailNotifier(self.config['notifications']['email'])
        self.desktop_notifier = DesktopNotifier()
        
    def scrape_jobs(self) -> List[Dict]:
        """Scrape jobs from Naukri"""
        self.logger.info("Starting job scraping...")
        
        jobs = []
        for search_config in self.config['searches']:
            try:
                scraped_jobs = self.scraper.search_jobs(
                    keywords=search_config['keywords'],
                    location=search_config['location'],
                    experience_range=search_config.get('experience', [0, 20])
                )
                jobs.extend(scraped_jobs)
                self.logger.info(f"Scraped {len(scraped_jobs)} jobs for {search_config['keywords']}")
            except Exception as e:
                self.logger.error(f"Error scraping jobs: {e}")
                
        # Save to database
        new_jobs = self.db.save_jobs(jobs)
        self.logger.info(f"Saved {len(new_jobs)} new jobs to database")
        
        return new_jobs
    
    def match_jobs(self, jobs: List[Dict] = None) -> List[Dict]:
        """Match jobs with resumes"""
        self.logger.info("Starting job matching...")
        
        # Get jobs from database if not provided
        if jobs is None:
            jobs = self.db.get_unmatched_jobs()
            
        # Get resume files
        resume_dir = Path("resumes")
        resume_files = list(resume_dir.glob("*.pdf")) + list(resume_dir.glob("*.docx"))
        
        if not resume_files:
            self.logger.error("No resume files found in resumes/ directory")
            return []
            
        matches = []
        for resume_path in resume_files:
            self.logger.info(f"Processing resume: {resume_path.name}")
            
            try:
                job_matches = self.matcher.match_jobs_with_resume(
                    resume_path=str(resume_path),
                    jobs=jobs,
                    threshold=self.config['matcher']['threshold']
                )
                
                for match in job_matches:
                    match['resume_file'] = resume_path.name
                    matches.append(match)
                    
            except Exception as e:
                self.logger.error(f"Error processing resume {resume_path}: {e}")
                
        # Save matches to database
        self.db.save_matches(matches)
        self.logger.info(f"Found {len(matches)} matching jobs")
        
        return matches
    
    def send_notifications(self, matches: List[Dict]):
        """Send notifications for matched jobs"""
        if not matches:
            self.logger.info("No matches to notify")
            return
            
        self.logger.info(f"Sending notifications for {len(matches)} matches...")
        
        # Group matches by resume
        matches_by_resume = {}
        for match in matches:
            resume = match.get('resume_file', 'Unknown')
            if resume not in matches_by_resume:
                matches_by_resume[resume] = []
            matches_by_resume[resume].append(match)
            
        # Send email notification
        if self.config['notifications']['email']['enabled']:
            try:
                self.email_notifier.send_match_notification(matches_by_resume)
                self.logger.info("Email notification sent successfully")
            except Exception as e:
                self.logger.error(f"Failed to send email: {e}")
                
        # Send desktop notification
        if self.config['notifications']['desktop']['enabled']:
            try:
                summary = f"Found {len(matches)} matching jobs!"
                self.desktop_notifier.notify(
                    title="Naukri Job Matcher",
                    message=summary
                )
            except Exception as e:
                self.logger.error(f"Failed to send desktop notification: {e}")
                
    def run_full_pipeline(self):
        """Run the complete pipeline"""
        self.logger.info("Starting full pipeline run...")
        
        # Scrape new jobs
        new_jobs = self.scrape_jobs()
        
        # Match jobs with resumes
        matches = self.match_jobs(new_jobs)
        
        # Send notifications
        self.send_notifications(matches)
        
        self.logger.info("Pipeline completed successfully")
        
    def generate_report(self):
        """Generate matching report"""
        stats = self.db.get_statistics()
        
        print("\n" + "="*50)
        print("NAUKRI JOB MATCHER REPORT")
        print("="*50)
        print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nTotal Jobs Scraped: {stats['total_jobs']}")
        print(f"Total Matches Found: {stats['total_matches']}")
        print(f"Average Match Score: {stats['avg_match_score']:.1f}%")
        print(f"\nTop Matching Companies:")
        for company in stats['top_companies']:
            print(f"  - {company['name']}: {company['count']} matches")
        print("="*50 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Naukri Job Matcher")
    parser.add_argument(
        "--mode",
        choices=["scrape", "match", "full", "report"],
        default="full",
        help="Operation mode"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Initialize and run app
    app = NaukriJobMatcherApp()
    
    try:
        if args.mode == "scrape":
            app.scrape_jobs()
        elif args.mode == "match":
            app.match_jobs()
        elif args.mode == "full":
            app.run_full_pipeline()
        elif args.mode == "report":
            app.generate_report()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()  