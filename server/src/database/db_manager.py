"""
Database Manager for storing jobs and matches
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import func, desc, create_engine, Column, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from src.utils.logger import setup_logger

Base = declarative_base()


class Job(Base):
    """Job model"""
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String, unique=True, index=True)
    title = Column(String)
    company = Column(String)
    location = Column(String)
    experience = Column(String)
    salary = Column(String)
    url = Column(String)
    skills = Column(JSON)
    description = Column(Text)
    posted_date = Column(String)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    matched = Column(Integer, default=0)
    

class Match(Base):
    """Match model"""
    __tablename__ = 'matches'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String, index=True)
    resume_file = Column(String)
    match_score = Column(Float)
    score_breakdown = Column(JSON)
    matched_skills = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    notified = Column(Integer, default=0)
    applied = Column(Integer, default=0)
    

class DatabaseManager:
    """Manage database operations"""
    
    def __init__(self, db_url: str = None):
        """Initialize database connection"""
        self.logger = setup_logger(__name__)
        
        if not db_url:
            db_url = os.getenv('DATABASE_URL', 'sqlite:///data/jobs.db')
            
        # Create data directory if it doesn't exist
        if 'sqlite' in db_url:
            db_path = db_url.replace('sqlite:///', '')
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
    def save_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Save jobs to database"""
        new_jobs = []
        
        for job_data in jobs:
            try:
                # Check if job already exists
                existing = self.session.query(Job).filter_by(
                    job_id=job_data.get('job_id')
                ).first()
                
                if not existing:
                    job = Job(
                        job_id=job_data.get('job_id'),
                        title=job_data.get('title'),
                        company=job_data.get('company'),
                        location=job_data.get('location'),
                        experience=job_data.get('experience'),
                        salary=job_data.get('salary'),
                        url=job_data.get('url'),
                        skills=job_data.get('skills', []),
                        description=job_data.get('description', ''),
                        posted_date=job_data.get('posted_date'),
                        scraped_at=datetime.fromisoformat(job_data.get('scraped_at', datetime.now().isoformat()))
                    )
                    self.session.add(job)
                    new_jobs.append(job_data)
                    
            except IntegrityError:
                self.session.rollback()
                continue
                
        self.session.commit()
        self.logger.info(f"Saved {len(new_jobs)} new jobs")
        return new_jobs
    
    def get_unmatched_jobs(self) -> List[Dict]:
        """Get jobs that haven't been matched yet"""
        jobs = self.session.query(Job).filter_by(matched=0).all()
        
        return [self._job_to_dict(job) for job in jobs]
    
    def get_all_jobs(self) -> List[Dict]:
        """Get all jobs from database"""
        jobs = self.session.query(Job).all()
        return [self._job_to_dict(job) for job in jobs]
    
    def save_matches(self, matches: List[Dict]):
        """Save job matches to database"""
        for match_data in matches:
            try:
                # Check if match already exists
                existing = self.session.query(Match).filter_by(
                    job_id=match_data.get('job_id'),
                    resume_file=match_data.get('resume_file')
                ).first()
                
                if not existing:
                    match = Match(
                        job_id=match_data.get('job_id'),
                        resume_file=match_data.get('resume_file'),
                        match_score=match_data.get('match_score'),
                        score_breakdown=match_data.get('score_breakdown'),
                        matched_skills=match_data.get('matched_skills', [])
                    )
                    self.session.add(match)
                    
                    # Mark job as matched
                    job = self.session.query(Job).filter_by(
                        job_id=match_data.get('job_id')
                    ).first()
                    if job:
                        job.matched = 1
                        
            except Exception as e:
                self.logger.error(f"Error saving match: {e}")
                self.session.rollback()
                continue
                
        self.session.commit()
        
    def get_recent_matches(self, days: int = 7) -> List[Dict]:
        """Get recent matches"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        matches = self.session.query(Match).filter(
            Match.created_at >= cutoff_date
        ).all()
        
        results = []
        for match in matches:
            job = self.session.query(Job).filter_by(job_id=match.job_id).first()
            if job:
                match_dict = self._match_to_dict(match)
                match_dict.update({
                    'job_title': job.title,
                    'company': job.company,
                    'location': job.location,
                    'job_url': job.url
                })
                results.append(match_dict)
                
        return results
    
    def mark_as_applied(self, job_id: str, resume_file: str):
        """Mark a match as applied"""
        match = self.session.query(Match).filter_by(
            job_id=job_id,
            resume_file=resume_file
        ).first()
        
        if match:
            match.applied = 1
            self.session.commit()
            
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        total_jobs = self.session.query(Job).count()
        total_matches = self.session.query(Match).count()
        
        # Get average match score
        avg_score = self.session.query(
            func.avg(Match.match_score)
        ).scalar() or 0
        
        # Get top matching companies
        top_companies = self.session.query(
            Job.company,
            func.count(Match.id).label('match_count')
        ).join(Match, Job.job_id == Match.job_id).group_by(
            Job.company
        ).order_by(desc('match_count')).limit(5).all()
        
        return {
            'total_jobs': total_jobs,
            'total_matches': total_matches,
            'avg_match_score': avg_score,
            'top_companies': [
                {'name': company, 'count': count}
                for company, count in top_companies
            ]
        }
    
    def _job_to_dict(self, job: Job) -> Dict:
        """Convert Job object to dictionary"""
        return {
            'job_id': job.job_id,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'experience': job.experience,
            'salary': job.salary,
            'url': job.url,
            'skills': job.skills or [],
            'description': job.description,
            'posted_date': job.posted_date,
            'scraped_at': job.scraped_at.isoformat() if job.scraped_at else None
        }
    
    def _match_to_dict(self, match: Match) -> Dict:
        """Convert Match object to dictionary"""
        return {
            'job_id': match.job_id,
            'resume_file': match.resume_file,
            'match_score': match.match_score,
            'score_breakdown': match.score_breakdown or {},
            'matched_skills': match.matched_skills or [],
            'created_at': match.created_at.isoformat() if match.created_at else None,
            'applied': match.applied
        }
    
    def close(self):
        """Close database connection"""
        self.session.close()
