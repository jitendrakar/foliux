from django.core.management.base import BaseCommand
from screener.models import Company
from screener.guidance_downloader import download_or_sync_document
from screener.forecast_extractor import extract_and_store_forecasts
from screener.comparison_engine import evaluate_forecast_vs_actuals, update_company_reliability_score

class Command(BaseCommand):
    help = 'Fetches, downloads local corporate filings, extracts AI management guidance, and updates reliability scores.'

    def add_arguments(self, parser):
        parser.add_argument('--symbol', type=str, help='Specific company NSE symbol e.g. TCS')
        parser.add_argument('--years', type=int, default=5, help='Number of financial years to sync (default: 5)')

    def handle(self, *args, **options):
        symbol = options.get('symbol')
        years_count = options.get('years', 5)

        if symbol:
            companies = Company.objects.filter(nse_symbol__iexact=symbol)
            if not companies.exists():
                self.stdout.write(self.style.WARNING(f"Company {symbol} not found. Creating entry..."))
                company = Company.objects.create(
                    name=f"{symbol.upper()} Limited",
                    nse_symbol=symbol.upper(),
                    industry="IT Services & Consulting",
                    sector="Technology"
                )
                companies = [company]
        else:
            companies = Company.objects.all()
            if not companies.exists():
                self.stdout.write(self.style.WARNING("No companies found in database. Initializing top companies..."))
                for s, n in [('TCS', 'Tata Consultancy Services Ltd'), ('INFY', 'Infosys Ltd'), ('RELIANCE', 'Reliance Industries Ltd')]:
                    Company.objects.get_or_create(
                        nse_symbol=s,
                        defaults={'name': n, 'industry': 'IT Services & Consulting', 'sector': 'Technology'}
                    )
                companies = Company.objects.all()

        financial_years = [f"FY{2026 - i}" for i in range(years_count)]

        doc_types = ['annual_report', 'investor_presentation', 'concall_transcript', 'quarterly_results']

        self.stdout.write(self.style.SUCCESS(f"Starting Management Guidance Sync for {len(companies)} company/companies over {financial_years}..."))

        for company in companies:
            self.stdout.write(f"\n---> Processing {company.name} ({company.nse_symbol})...")
            
            for fy in financial_years:
                docs = []
                for dt in doc_types:
                    doc = download_or_sync_document(company, fy, dt)
                    docs.append(doc)
                
                # Extract AI forecasts
                forecasts = extract_and_store_forecasts(company, fy, docs)
                
                # Compare forecasts vs actuals
                for fc in forecasts:
                    evaluate_forecast_vs_actuals(fc)
                
                self.stdout.write(f"     [+] Sync Completed for {fy}: {len(forecasts)} forecasts extracted & evaluated.")
            
            # Compute final management reliability score
            score_obj = update_company_reliability_score(company)
            self.stdout.write(self.style.SUCCESS(f" [OK] {company.name} Reliability Score: {score_obj.overall_score}/100 ({score_obj.reliability_score_percent}% reliability)"))

        self.stdout.write(self.style.SUCCESS("\nManagement Forecast Sync completed successfully! All files archived in result/ directory."))
