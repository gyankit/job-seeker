"""
Email Notifier for sending job match notifications
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List
from datetime import datetime

from src.utils.logger import setup_logger


class EmailNotifier:
    """Send email notifications for job matches"""
    
    def __init__(self, config: Dict):
        """Initialize email notifier"""
        self.logger = setup_logger(__name__)
        self.config = config
        
        # Get credentials from environment
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.from_email = os.getenv('EMAIL_ADDRESS', config.get('from_email'))
        self.password = os.getenv('EMAIL_PASSWORD')
        self.to_email = os.getenv('NOTIFICATION_EMAIL', config.get('to_email'))
        
    def send_match_notification(self, matches_by_resume: Dict[str, List[Dict]]):
        """Send notification email with job matches"""
        if not self.from_email or not self.password:
            self.logger.error("Email credentials not configured")
            return
            
        try:
            # Create email content
            subject = f"🎯 {sum(len(m) for m in matches_by_resume.values())} New Job Matches Found!"
            body = self._create_email_body(matches_by_resume)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            
            # Add HTML content
            html_part = MIMEText(body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.password)
                server.send_message(msg)
                
            self.logger.info(f"Email notification sent to {self.to_email}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            raise
            
    def _create_email_body(self, matches_by_resume: Dict[str, List[Dict]]) -> str:
        """Create HTML email body"""
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 800px; margin: 0 auto; padding: 20px; }
                .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px; }
                .resume-section { margin: 20px 0; padding: 15px; background-color: #f9f9f9; border-radius: 5px; }
                .job-card { margin: 15px 0; padding: 15px; background-color: white; border: 1px solid #ddd; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .job-title { font-size: 18px; font-weight: bold; color: #2196F3; margin-bottom: 5px; }
                .company { font-size: 16px; color: #666; margin-bottom: 10px; }
                .match-score { display: inline-block; padding: 5px 10px; background-color: #4CAF50; color: white; border-radius: 3px; font-weight: bold; }
                .details { margin: 10px 0; font-size: 14px; }
                .skills { margin: 10px 0; }
                .skill-tag { display: inline-block; padding: 3px 8px; margin: 2px; background-color: #e0e0e0; border-radius: 3px; font-size: 12px; }
                .apply-button { display: inline-block; padding: 10px 20px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 5px; margin-top: 10px; }
                .apply-button:hover { background-color: #1976D2; }
                .footer { margin-top: 30px; padding: 20px; text-align: center; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 New Job Matches Found!</h1>
                    <p>Your automated job matcher has found new opportunities that match your profile</p>
                </div>
        """
        
        total_matches = sum(len(matches) for matches in matches_by_resume.values())
        html += f'<p style="text-align: center; font-size: 18px; margin: 20px 0;">Total Matches: <strong>{total_matches}</strong></p>'
        
        for resume_name, matches in matches_by_resume.items():
            html += f'<div class="resume-section">'
            html += f'<h2>📄 Resume: {resume_name}</h2>'
            html += f'<p>Found {len(matches)} matching positions</p>'
            
            for match in matches[:10]:  # Limit to top 10 per resume
                html += f'''
                <div class="job-card">
                    <div class="job-title">{match.get('job_title', 'N/A')}</div>
                    <div class="company">{match.get('company', 'N/A')} - {match.get('location', 'N/A')}</div>
                    <div class="match-score">Match Score: {match.get('match_score', 0)}%</div>
                    
                    <div class="details">
                        <strong>Score Breakdown:</strong><br>
                '''
                
                if 'score_breakdown' in match:
                    for key, value in match['score_breakdown'].items():
                        html += f'• {key.capitalize()}: {value*100:.1f}%<br>'
                        
                if match.get('matched_skills'):
                    html += '<div class="skills"><strong>Matched Skills:</strong><br>'
                    for skill in match['matched_skills'][:10]:
                        html += f'<span class="skill-tag">{skill}</span>'
                    html += '</div>'
                    
                html += f'''
                    </div>
                    <a href="{match.get('job_url', '#')}" class="apply-button" target="_blank">View & Apply</a>
                </div>
                '''
                
            html += '</div>'
            
        html += '''
                <div class="footer">
                    <p>This is an automated notification from your Naukri Job Matcher</p>
                    <p>Generated at: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
                    <p>To update your search preferences, please modify the configuration file.</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        return html
    
    def send_test_email(self):
        """Send a test email to verify configuration"""
        try:
            subject = "Test Email - Naukri Job Matcher"
            body = """
            <html>
            <body>
                <h2>Test Email Successful!</h2>
                <p>Your email configuration is working correctly.</p>
                <p>You will receive job match notifications at this email address.</p>
            </body>
            </html>
            """
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            
            html_part = MIMEText(body, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.password)
                server.send_message(msg)
                
            self.logger.info("Test email sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Test email failed: {e}")
            return False