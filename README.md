# Wayground Tender Monitor

An AI-powered intelligent tender monitoring and analysis system designed specifically for Wayground's education technology services. This system automatically searches government tender portals across EUK, APAC, and MEA regions, analyzes opportunities using Google Gemini AI, and provides intelligent recommendations.

## 🚀 Features

### Core Functionality
- **Automated Tender Discovery**: Searches multiple government tender portals across EUK, APAC, and MEA regions
- **AI-Powered Analysis**: Uses Google Gemini to analyze tender relevance and scoring
- **Intelligent Matching**: Matches tenders against Wayground's specific capabilities and keywords
- **Real-time Dashboard**: Modern web interface for monitoring and managing opportunities
- **Smart Notifications**: Alerts for urgent and high-value opportunities

### AI Analysis Capabilities
- **Relevance Scoring**: 0-1 scale relevance assessment for each tender
- **Keyword Matching**: Intelligent matching against education technology keywords
- **Success Probability**: AI-estimated probability of winning each tender
- **Competitive Assessment**: Analysis of competition level and Wayground's advantages
- **Value Assessment**: Evaluation of tender value and ROI potential

### Dashboard Features
- **Overview Dashboard**: KPI cards, alerts, and top opportunities
- **Tender Management**: Full CRUD operations with filtering and search
- **Analysis Insights**: Keyword performance, regional distribution, and trends
- **Detailed Tender Views**: Complete tender information with AI recommendations

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Scraper   │    │   Gemini AI      │    │   Database      │
│   (Multi-region)│    │   Analyzer       │    │   (PostgreSQL)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────────────────────┼─────────────────────────────────┐
│                          FastAPI Backend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐│
│  │   Tenders   │  │  Analysis   │  │  Dashboard  │  │ Monitoring ││
│  │   Router    │  │   Router    │  │   Router    │  │  Service   ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘│
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │    Frontend Dashboard    │
                    │   (HTML/CSS/JavaScript) │
                    └─────────────────────────┘
```

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI/ML**: Google Gemini API
- **Frontend**: HTML5, Bootstrap 5, Chart.js
- **Background Tasks**: Celery with Redis
- **Web Scraping**: aiohttp, BeautifulSoup, Selenium
- **Deployment**: Docker, Docker Compose

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Google Gemini API Key
- Docker (optional)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd wayground-tender-monitor
```

### 2. Set Up Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 3. Install Dependencies
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Database
```bash
# Create PostgreSQL database
createdb wayground_tenders

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://username:password@localhost/wayground_tenders
```

### 5. Set Up Gemini AI
1. Get your Google Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add it to your `.env` file:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

### 6. Start the Application
```bash
# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Access the Dashboard
Open your browser and go to: `http://localhost:8000`

## 🐳 Docker Deployment

### Using Docker Compose
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Docker Build
```bash
# Build the image
docker build -t wayground-tender-monitor .

# Run the container
docker run -d -p 8000:8000 --env-file .env wayground-tender-monitor
```

## 📊 Usage Guide

### Dashboard Overview
1. **KPI Cards**: Quick stats on total tenders, recommendations, urgent opportunities
2. **Top Opportunities**: AI-ranked best matches for Wayground
3. **Regional Distribution**: Chart showing tender distribution by region
4. **Urgent Tenders**: Tenders closing soon that need immediate attention

### Tender Management
1. **Search & Filter**: Use multiple filters to find specific tenders
2. **View Details**: Click on any tender to see full information and AI analysis
3. **Update Status**: Mark tenders as reviewed, applied, or rejected
4. **Manual Analysis**: Trigger AI re-analysis for specific tenders

### AI Analysis
1. **Automatic Scoring**: All tenders automatically scored by AI
2. **Detailed Insights**: Comprehensive analysis including competition assessment
3. **Keyword Performance**: Track which keywords perform best
4. **Success Probability**: AI-estimated win probability for each opportunity

## 🔧 Configuration

### Environment Variables
Key environment variables (see `.env.example` for full list):

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql://user:pass@localhost/db_name

# Optional
SEARCH_INTERVAL_HOURS=6
ANALYSIS_BATCH_SIZE=10
REDIS_URL=redis://localhost:6379
```

### Wayground Profile Customization
Edit `app/config.py` to customize:
- Company description and capabilities
- Target keywords for matching
- Geographic preferences
- Scoring weights

### Adding New Tender Portals
To add new government tender portals:

1. Edit `app/config.py` and add portal URLs to `tender_portals`
2. Implement portal-specific scraper in `app/services/tender_scraper.py`
3. Test the new scraper with sample searches

## 🔄 Automated Monitoring

The system includes automated monitoring that:
- Searches for new tenders every 6 hours
- Analyzes new tenders with AI immediately
- Generates daily and weekly reports
- Sends alerts for urgent opportunities

### Manual Triggers
```bash
# Trigger immediate search
curl -X POST http://localhost:8000/api/tenders/search

# Analyze specific tender
curl -X POST http://localhost:8000/api/tenders/analyze/TENDER_ID
```

## 📈 API Documentation

Once running, visit:
- Interactive API docs: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Key Endpoints
- `GET /api/tenders/` - List all tenders with filters
- `GET /api/tenders/{id}` - Get specific tender details
- `POST /api/tenders/search` - Trigger manual search
- `GET /api/dashboard/overview` - Dashboard statistics
- `GET /api/analysis/insights` - AI analysis insights

## 🔍 Monitoring & Logging

### Health Checks
```bash
# Basic health check
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/api/dashboard/overview
```

### Logs
Application logs include:
- Tender discovery and processing
- AI analysis results
- Error tracking and debugging
- Performance metrics

## 🛡️ Security Considerations

- API key security (never commit to version control)
- Database connection security
- Rate limiting for external API calls
- Input validation and sanitization
- HTTPS for production deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is proprietary software developed for Wayground Ltd.

## 🆘 Support & Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -h localhost -U username -d wayground_tenders
```

**Gemini AI Errors**
- Verify API key is correct
- Check quota limits
- Ensure network connectivity

**Scraping Issues**
- Some portals may block automated requests
- Rate limiting may cause delays
- Portal structure changes may break scrapers

### Performance Optimization
- Adjust `SEARCH_INTERVAL_HOURS` based on needs
- Tune `ANALYSIS_BATCH_SIZE` for optimal AI processing
- Use Redis for caching frequently accessed data

## 🗺️ Roadmap

### Planned Features
- [ ] Email notifications for urgent tenders
- [ ] Slack/Teams integration
- [ ] Machine learning model for win probability
- [ ] Mobile-responsive design improvements
- [ ] Tender document analysis
- [ ] Automated proposal generation assistance
- [ ] Integration with CRM systems
- [ ] Advanced analytics and reporting

### Regional Expansion
- [ ] Additional APAC portals
- [ ] More European country portals
- [ ] Middle East and Africa expansion
- [ ] Portal-specific optimization

---

**Built with ❤️ for Wayground's tender monitoring needs**
