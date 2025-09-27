# Paralympic India Dashboard

A real-time analytics dashboard for the Paralympics Committee of India, featuring Cloudflare analytics and Paralympic medal tracking.

## Features

- 🏆 **Paralympic Medal Tracking**: Real-time medal updates with AI-generated summaries
- 🌐 **Cloudflare Analytics**: Website traffic, bandwidth, and security metrics
- 📊 **Interactive Visualizations**: Charts and maps using Plotly
- 🎨 **Modern UI**: Responsive design with Paralympic India branding
- ⚡ **Real-time Updates**: Auto-refresh every 5 minutes

## PythonAnywhere Deployment

### 1. Upload Files
Upload all files to your PythonAnywhere account in the `/home/yourusername/PCI_Statistics/` directory.

### 2. Install Dependencies
In the PythonAnywhere console, run:
```bash
pip3.10 install --user -r requirements.txt
```

### 3. Set Environment Variables
In the PythonAnywhere dashboard, go to "Web" tab and add these environment variables:
- `API_TOKEN`: Your Cloudflare API token
- `ZONE_ID`: Your Cloudflare zone ID  
- `OPENAI_API_KEY`: Your OpenAI API key

### 4. Configure WSGI
1. Go to the "Web" tab in PythonAnywhere
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Select Python 3.10
5. In the WSGI configuration file, replace the content with:
```python
import sys
import os

path = '/home/yourusername/PCI_Statistics'  # Replace with your username
if path not in sys.path:
    sys.path.append(path)

from main import app
application = app.server
```

### 5. Reload Web App
Click the green "Reload" button to deploy your app.

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API keys:
```
API_TOKEN=your_cloudflare_token
ZONE_ID=your_zone_id
OPENAI_API_KEY=your_openai_key
```

3. Run the app:
```bash
python main.py
```

## Dependencies

- `dash==2.14.2` - Web framework
- `plotly==5.17.0` - Interactive charts
- `pandas==2.1.4` - Data manipulation
- `requests==2.31.0` - API calls
- `python-dotenv==1.0.0` - Environment variables
- `pycountry==23.12.11` - Country code conversion
- `openai==1.3.7` - AI summary generation
- `gunicorn==21.2.0` - Production server

## API Endpoints

The dashboard fetches data from:
- **Paralympic Medallists**: Live medal data from the official Paralympic feed
- **Cloudflare Analytics**: Website traffic and security metrics via GraphQL API
- **OpenAI**: AI-generated summaries of daily Paralympic highlights
