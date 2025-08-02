# Naukri Job Matcher

An automated job matching system that scrapes Naukri.com for relevant job postings and matches them against your resume(s) using AI-powered similarity analysis.

## Features

- 🔍 Automated job scraping from Naukri.com
- 📄 Resume parsing and analysis
- 🎯 AI-powered job description matching (70%+ threshold)
- 📧 Email/Desktop notifications for matching jobs
- 📊 Dashboard for tracking applications
- 🔄 Scheduled automated runs
- 📈 Match score analytics

## Prerequisites

- Python 3.8+
- Chrome/Chromium browser (for Selenium)
- Gmail account (for notifications)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/naukri-job-matcher.git
cd naukri-job-matcher
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Download ChromeDriver:
```bash
python scripts/setup_chromedriver.py
```

5. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Edit the `config/settings.yaml` file:

```yaml
search:
  keywords: ["Python Developer", "Data Scientist"]
  location: "Bangalore"
  experience: [2, 5]  # Min and max years

matching:
  threshold: 70  # Minimum match percentage
  
notifications:
  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
```

## Usage

### 1. Upload Your Resume(s)

Place your resume files in the `resumes/` directory:
```bash
cp /path/to/your/resume.pdf resumes/
```

### 2. Run the Scraper

```bash
python src/main.py --mode scrape
```

### 3. Run the Matcher

```bash
python src/main.py --mode match
```

### 4. Run Complete Pipeline

```bash
python src/main.py --mode full
```

### 5. Schedule Automated Runs

```bash
# Using cron (Linux/Mac)
crontab -e
# Add: 0 9,17 * * * cd /path/to/project && python src/main.py --mode full

# Using Task Scheduler (Windows)
python scripts/setup_windows_scheduler.py
```

## Project Structure

```
naukri-job-matcher/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── naukri_scraper.py
│   │   └── job_parser.py
│   ├── matcher/
│   │   ├── __init__.py
│   │   ├── resume_parser.py
│   │   ├── similarity_engine.py
│   │   └── matcher.py
│   ├── notifier/
│   │   ├── __init__.py
│   │   ├── email_notifier.py
│   │   └── desktop_notifier.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── db_manager.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── helpers.py
├── config/
│   ├── settings.yaml
│   └── logging_config.yaml
├── resumes/
├── data/
│   ├── jobs.db
│   └── logs/
├── tests/
├── scripts/
│   ├── setup_chromedriver.py
│   └── setup_windows_scheduler.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

## API Documentation

### Scraper Module

```python
from src.scraper import NaukriScraper

scraper = NaukriScraper()
jobs = scraper.search_jobs(
    keywords="Python Developer",
    location="Bangalore",
    experience_range=(2, 5)
)
```

### Matcher Module

```python
from src.matcher import JobMatcher

matcher = JobMatcher()
matches = matcher.match_jobs_with_resume(
    resume_path="resumes/my_resume.pdf",
    jobs=jobs,
    threshold=70
)
```

## Testing

Run tests with pytest:
```bash
pytest tests/ -v
```

## Troubleshooting

### Common Issues

1. **ChromeDriver version mismatch**
   ```bash
   python scripts/setup_chromedriver.py --update
   ```

2. **Login issues**
   - Ensure 2FA is disabled for automation account
   - Check if Naukri has updated their UI

3. **Low match scores**
   - Optimize resume keywords
   - Adjust matching algorithm weights in config

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for personal use only. Please respect Naukri's Terms of Service and implement appropriate rate limiting to avoid overloading their servers.

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/yourusername/naukri-job-matcher/issues) page.