from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for, flash
from scraper import GeneralizedLeadGenScraper
import pandas as pd
import io
import os
import logging
import time

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ---------- Helpers ---------- #

def create_excel_file(results, url, pages_crawled, duration):
    """Creates an in-memory Excel file with leads, summary, and metadata."""
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Main leads sheet
        results.to_excel(writer, sheet_name='Leads', index=False)

        # Summary sheet
        summary = pd.DataFrame({
            'Type': ['Emails', 'Phone Numbers', 'LinkedIn Profiles', 'Total'],
            'Count': [
                len(results[results['Contact Type'] == 'Email']),
                len(results[results['Contact Type'] == 'Phone']),
                len(results[results['Contact Type'] == 'LinkedIn']),
                len(results)
            ]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)

        # Metadata sheet
        metadata = pd.DataFrame({
            'Property': ['URL Scraped', 'Pages Crawled', 'Duration (seconds)', 'Date Scraped'],
            'Value': [
                url,
                pages_crawled,
                f"{duration:.2f}",
                pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
        })
        metadata.to_excel(writer, sheet_name='Metadata', index=False)

        # Format "Leads" sheet
        workbook = writer.book
        worksheet = writer.sheets['Leads']

        # Apply filters and header styling
        worksheet.autofilter(0, 0, len(results), len(results.columns) - 1)
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})

        for col_num, value in enumerate(results.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Adjust column widths for readability
        worksheet.set_column('A:A', 15)  # Contact Type
        worksheet.set_column('B:B', 40)  # Value
        worksheet.set_column('C:C', 30)  # Name
        worksheet.set_column('D:D', 40)  # Job Title
        worksheet.set_column('E:E', 60)  # Source URL

    output.seek(0)
    return output


# ---------- Routes ---------- #

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        max_pages = int(request.form.get('max_pages', 15))
        delay = float(request.form.get('delay', 1.0))

        try:
            start_time = time.time()
            logger.info(f"Scraping started: {url}, max_pages={max_pages}, delay={delay}s")

            scraper = GeneralizedLeadGenScraper(max_pages=max_pages, delay=delay)
            results = scraper.scrape(url)
            duration = time.time() - start_time

            if results.empty:
                flash(f"No leads found after scanning {len(scraper.visited_urls)} pages. "
                      f"Try a different URL or adjust the crawl settings.")
                return redirect(url_for('index'))

            output = create_excel_file(results, url, len(scraper.visited_urls), duration)
            logger.info(f"Scraping finished in {duration:.2f}s with {len(results)} results")

            return send_file(
                output,
                as_attachment=True,
                download_name='leads.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        except Exception as e:
            logger.error(f"Scraping error: {str(e)}")
            flash(f"Something went wrong while scraping: {str(e)}")
            return redirect(url_for('index'))

    return render_template('index.html')


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """
    REST API endpoint to perform scraping based on provided JSON input.
    """
    data = request.json

    if not data or 'url' not in data:
        return jsonify({'error': 'Missing required parameter: url'}), 400

    url = data['url']
    max_pages = data.get('max_pages', 15)
    delay = data.get('delay', 1.0)

    try:
        start_time = time.time()
        scraper = GeneralizedLeadGenScraper(max_pages=max_pages, delay=delay)
        results = scraper.scrape(url)
        duration = time.time() - start_time

        if results.empty:
            return jsonify({
                'status': 'no_results',
                'message': 'No contact details found.',
                'stats': {
                    'pages_crawled': len(scraper.visited_urls),
                    'duration_seconds': round(duration, 2)
                }
            }), 200

        return jsonify({
            'status': 'success',
            'data': results.to_dict(orient='records'),
            'stats': {
                'emails': len(results[results['Contact Type'] == 'Email']),
                'phones': len(results[results['Contact Type'] == 'Phone']),
                'linkedin': len(results[results['Contact Type'] == 'LinkedIn']),
                'total': len(results),
                'pages_crawled': len(scraper.visited_urls),
                'duration_seconds': round(duration, 2)
            }
        })

    except Exception as e:
        logger.error(f"API scraping error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
