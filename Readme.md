# LeadGen Scraper

![LeadGen Scraper](https://img.shields.io/badge/Status-Active-brightgreen)

A powerful web application for extracting contact information from public websites. LeadGen Scraper identifies emails, phone numbers, and LinkedIn profiles with precision and exports them to a clean, deduplicated CSV format.

## 🚀 Features

- **Simple Interface** - Enter a URL and get results with just one click
- **Intelligent Extraction** - Accurately identifies contact details using regex patterns
- **Data Cleaning** - Automatic deduplication ensures quality results
- **Easy Export** - Download findings instantly as a structured CSV file
- **Privacy Focused** - Only extracts publicly available information

## 📋 Requirements

- Python 3.6+
- Flask
- Requests
- BeautifulSoup4
- Pandas
- Xlsxwriter
- Lxml
- Phonenumbers

## ⚙️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/SuryanshGarg12/LeadGen-Scraper.git
   cd LeadGen-Scraper
   ```

2. **Set up a virtual environment** (recommended)
   ```bash
   python3 -m venv venv
   
   # On macOS/Linux
   source venv/bin/activate
   
   # On Windows
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 🖥️ Usage

1. **Launch the application**
   ```bash
   python app.py
   ```

2. **Access the interface**
   - Open your browser and go to `http://127.0.0.1:5000/`

3. **Start scraping**
   - Enter the target website URL
   - Click "Scrape"
   - Download your results when processing completes

## 📊 Example Output

The CSV output includes the following fields:
- Email Address
- Phone Number
- LinkedIn Profile URL
- Source URL

## ⚠️ Disclaimer

LeadGen Scraper is designed for legitimate business purposes only. Always:
- Respect website terms of service and robots.txt directives
- Follow data protection regulations in your jurisdiction
- Use extracted information in accordance with privacy laws

---
