"""
Job-Resume Matcher using AI/ML techniques
"""

import re
from typing import List, Dict, Tuple
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import spacy
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from src.matcher.resume_parser import ResumeParser
from src.utils.logger import setup_logger


class JobMatcher:
    """Match jobs with resumes using NLP techniques"""
    
    def __init__(self, config: Dict):
        """Initialize the matcher"""
        self.logger = setup_logger(__name__)
        self.config = config
        self.resume_parser = ResumeParser()
        
        # Download required NLTK data
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
        except:
            pass
            
        # Load models
        self._load_models()
        
    def _load_models(self):
        """Load NLP models"""
        # Load spaCy model for NER
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            self.logger.warning("spaCy model not found. Installing...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")
            
        # Load sentence transformer for semantic similarity
        if self.config.get('use_semantic_matching', True):
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            self.sentence_model = None
            
        # Initialize TF-IDF vectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for matching"""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^a-zA-Z0-9\s\+\#]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from text using NER and pattern matching"""
        skills = set()
        
        # Common tech skills patterns
        tech_patterns = [
            r'\b(python|java|javascript|c\+\+|c#|ruby|go|rust|php|swift|kotlin|scala|r|matlab|perl)\b',
            r'\b(react|angular|vue|django|flask|spring|nodejs|express|fastapi|rails|laravel)\b',
            r'\b(tensorflow|pytorch|keras|scikit-learn|pandas|numpy|opencv|nltk|spacy)\b',
            r'\b(aws|azure|gcp|docker|kubernetes|jenkins|git|terraform|ansible)\b',
            r'\b(mysql|postgresql|mongodb|redis|elasticsearch|cassandra|oracle|sql server)\b',
            r'\b(machine learning|deep learning|nlp|computer vision|data science|ai|ml|dl)\b',
            r'\b(html|css|sass|less|bootstrap|tailwind|jquery|ajax|rest|api|graphql)\b',
            r'\b(linux|unix|windows|bash|shell|powershell|vim|vscode|intellij|eclipse)\b',
            r'\b(agile|scrum|kanban|jira|confluence|slack|teams|devops|ci/cd)\b'
        ]
        
        # Extract using patterns
        for pattern in tech_patterns:
            matches = re.findall(pattern, text.lower())
            skills.update(matches)
            
        # Extract using spaCy NER (for organizations, technologies)
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT', 'WORK_OF_ART']:
                skill = ent.text.lower()
                if len(skill) > 2 and not skill.isdigit():
                    skills.add(skill)
                    
        return list(skills)
    
    def _calculate_keyword_match(self, resume_text: str, job_text: str) -> float:
        """Calculate keyword-based matching score"""
        # Extract important keywords from both texts
        resume_keywords = set(self._preprocess_text(resume_text).split())
        job_keywords = set(self._preprocess_text(job_text).split())
        
        # Remove stopwords
        stop_words = set(stopwords.words('english'))
        resume_keywords = {w for w in resume_keywords if w not in stop_words and len(w) > 2}
        job_keywords = {w for w in job_keywords if w not in stop_words and len(w) > 2}
        
        # Calculate Jaccard similarity
        if not job_keywords:
            return 0.0
            
        intersection = resume_keywords.intersection(job_keywords)
        union = resume_keywords.union(job_keywords)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_tfidf_similarity(self, resume_text: str, job_text: str) -> float:
        """Calculate TF-IDF based similarity"""
        try:
            # Fit and transform texts
            tfidf_matrix = self.tfidf_vectorizer.fit_transform([resume_text, job_text])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
        except Exception as e:
            self.logger.error(f"Error calculating TF-IDF similarity: {e}")
            return 0.0
    
    def _calculate_semantic_similarity(self, resume_text: str, job_text: str) -> float:
        """Calculate semantic similarity using sentence transformers"""
        if not self.sentence_model:
            return 0.0
            
        try:
            # Encode texts
            resume_embedding = self.sentence_model.encode(resume_text)
            job_embedding = self.sentence_model.encode(job_text)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(
                resume_embedding.reshape(1, -1),
                job_embedding.reshape(1, -1)
            )[0][0]
            
            return float(similarity)
        except Exception as e:
            self.logger.error(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def _calculate_skills_match(self, resume_skills: List[str], job_skills: List[str]) -> float:
        """Calculate skills matching score"""
        if not job_skills:
            return 1.0  # If no specific skills required, give full score
            
        resume_skills_set = set([s.lower() for s in resume_skills])
        job_skills_set = set([s.lower() for s in job_skills])
        
        matched_skills = resume_skills_set.intersection(job_skills_set)
        
        return len(matched_skills) / len(job_skills_set)
    
    def calculate_match_score(self, resume_data: Dict, job_data: Dict) -> Tuple[float, Dict]:
        """Calculate overall match score between resume and job"""
        scores = {}
        
        # Prepare texts
        resume_text = f"{resume_data.get('text', '')} {' '.join(resume_data.get('skills', []))}"
        job_text = f"{job_data.get('title', '')} {job_data.get('description', '')} {' '.join(job_data.get('skills', []))}"
        
        # 1. Keyword matching (20%)
        scores['keyword'] = self._calculate_keyword_match(resume_text, job_text)
        
        # 2. TF-IDF similarity (25%)
        scores['tfidf'] = self._calculate_tfidf_similarity(resume_text, job_text)
        
        # 3. Semantic similarity (25%)
        scores['semantic'] = self._calculate_semantic_similarity(resume_text, job_text)
        
        # 4. Skills matching (30%)
        resume_skills = resume_data.get('skills', []) + self._extract_skills(resume_text)
        job_skills = job_data.get('skills', []) + self._extract_skills(job_text)
        scores['skills'] = self._calculate_skills_match(resume_skills, job_skills)
        
        # Calculate weighted average
        weights = self.config.get('weights', {
            'keyword': 0.20,
            'tfidf': 0.25,
            'semantic': 0.25,
            'skills': 0.30
        })
        
        overall_score = sum(scores[key] * weights.get(key, 0.25) for key in scores)
        
        # Convert to percentage
        overall_score = min(overall_score * 100, 100)
        
        return overall_score, scores
    
    def match_jobs_with_resume(self, resume_path: str, jobs: List[Dict], 
                              threshold: float = 70.0) -> List[Dict]:
        """Match multiple jobs with a resume"""
        self.logger.info(f"Matching {len(jobs)} jobs with resume: {resume_path}")
        
        # Parse resume
        resume_data = self.resume_parser.parse_resume(resume_path)
        if not resume_data:
            self.logger.error(f"Failed to parse resume: {resume_path}")
            return []
            
        matches = []
        
        for job in jobs:
            try:
                # Calculate match score
                score, score_breakdown = self.calculate_match_score(resume_data, job)
                
                if score >= threshold:
                    match = {
                        'job_id': job.get('job_id'),
                        'job_title': job.get('title'),
                        'company': job.get('company'),
                        'location': job.get('location'),
                        'job_url': job.get('url'),
                        'match_score': round(score, 2),
                        'score_breakdown': score_breakdown,
                        'matched_skills': list(set(resume_data.get('skills', [])) & 
                                             set(job.get('skills', []))),
                        'job_data': job,
                        'resume_data': {
                            'name': resume_data.get('name'),
                            'email': resume_data.get('email'),
                            'phone': resume_data.get('phone'),
                            'skills_count': len(resume_data.get('skills', []))
                        }
                    }
                    matches.append(match)
                    
            except Exception as e:
                self.logger.error(f"Error matching job {job.get('title')}: {e}")
                continue
                
        # Sort by match score
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        self.logger.info(f"Found {len(matches)} matches above {threshold}% threshold")
        
        return matches
    
    def find_best_matches(self, resume_path: str, jobs: List[Dict], 
                         top_n: int = 10) -> List[Dict]:
        """Find top N best matching jobs for a resume"""
        # Match all jobs
        all_matches = self.match_jobs_with_resume(resume_path, jobs, threshold=0)
        
        # Return top N
        return all_matches[:top_n]
    
    def generate_match_report(self, matches: List[Dict]) -> str:
        """Generate a detailed match report"""
        report = []
        report.append("="*70)
        report.append("JOB MATCHING REPORT")
        report.append("="*70)
        report.append("")
        
        for i, match in enumerate(matches, 1):
            report.append(f"{i}. {match['job_title']} at {match['company']}")
            report.append(f"   Match Score: {match['match_score']}%")
            report.append(f"   Location: {match['location']}")
            report.append(f"   URL: {match['job_url']}")
            
            if match.get('matched_skills'):
                report.append(f"   Matched Skills: {', '.join(match['matched_skills'])}")
                
            report.append(f"   Score Breakdown:")
            for key, value in match['score_breakdown'].items():
                report.append(f"     - {key.capitalize()}: {value*100:.1f}%")
                
            report.append("")
            
        return "\n".join(report)