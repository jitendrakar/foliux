import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from screener.models import Company, QuarterlyResult, ProfitLoss, BalanceSheet, CashFlow, ShareholdingPattern, CompanyDocument, HistoricalPrice

class Command(BaseCommand):
    help = 'Seeds the screener database with detailed, premium sample company data.'

    def handle(self, *args, **options):
        self.stdout.write("Deleting existing screener data...")
        # Since we use cascade, deleting companies deletes all related metrics
        Company.objects.all().delete()

        # Define 4 premium companies
        companies_data = [
            {
                'name': 'Reliance Industries Limited',
                'nse_symbol': 'RELIANCE',
                'bse_symbol': '500325',
                'industry': 'Oil Gas & Petrochemicals',
                'sector': 'Energy',
                'about': 'Reliance Industries Limited is a Fortune 500 company and the largest private sector corporation in India. It has evolved from being a textiles and polyester company into an integrated player across energy, materials, retail, entertainment, and digital services.',
                'current_price': 2450.50,
                'market_cap': 1658420.00,
                'high_52w': 2640.00,
                'low_52w': 2180.00,
                'pe_ratio': 23.40,
                'pb_ratio': 2.10,
                'book_value': 1166.00,
                'eps': 104.72,
                'roe': 9.20,
                'roce': 10.40,
                'dividend_yield': 0.41,
                'debt': 312000.00,
                'cash': 185000.00,
                'intrinsic_value': 2780.00,
                'industry_pe': 18.50,
                'promoter_holding': 50.39,
                'sales_growth': 14.50,
                'profit_growth': 11.20,
                'foliux_score': 85,
                'buy_score': 88,
                'valuation_score': 72,
                'growth_score': 82,
                'health_score': 90,
                'risk_score': 15,
                'technical_score': 78,
            },
            {
                'name': 'Tata Consultancy Services Limited',
                'nse_symbol': 'TCS',
                'bse_symbol': '532540',
                'industry': 'IT Services',
                'sector': 'Technology',
                'about': 'Tata Consultancy Services is an IT services, consulting and business solutions organization that has been partnering with many of the world’s largest businesses in their transformation journeys for over 50 years. TCS offers a consulting-led, cognitive powered, integrated portfolio of business, technology and engineering services and solutions.',
                'current_price': 3820.75,
                'market_cap': 1398250.00,
                'high_52w': 4200.00,
                'low_52w': 3450.00,
                'pe_ratio': 29.80,
                'pb_ratio': 14.20,
                'book_value': 269.00,
                'eps': 128.21,
                'roe': 48.50,
                'roce': 56.40,
                'dividend_yield': 1.25,
                'debt': 8200.00,
                'cash': 14500.00,
                'intrinsic_value': 3910.00,
                'industry_pe': 27.20,
                'promoter_holding': 72.41,
                'sales_growth': 8.60,
                'profit_growth': 9.40,
                'foliux_score': 88,
                'buy_score': 82,
                'valuation_score': 64,
                'growth_score': 78,
                'health_score': 95,
                'risk_score': 10,
                'technical_score': 85,
            },
            {
                'name': 'Infosys Limited',
                'nse_symbol': 'INFY',
                'bse_symbol': '500209',
                'industry': 'IT Services',
                'sector': 'Technology',
                'about': 'Infosys Limited is an Indian multinational information technology company that provides business consulting, information technology and outsourcing services. The company was founded in Pune and is headquartered in Bangalore.',
                'current_price': 1520.40,
                'market_cap': 631450.00,
                'high_52w': 1760.00,
                'low_52w': 1380.00,
                'pe_ratio': 24.10,
                'pb_ratio': 7.80,
                'book_value': 195.00,
                'eps': 63.10,
                'roe': 31.80,
                'roce': 38.60,
                'dividend_yield': 2.15,
                'debt': 6500.00,
                'cash': 12200.00,
                'intrinsic_value': 1610.00,
                'industry_pe': 27.20,
                'promoter_holding': 14.94,
                'sales_growth': 6.20,
                'profit_growth': 5.80,
                'foliux_score': 75,
                'buy_score': 78,
                'valuation_score': 75,
                'growth_score': 68,
                'health_score': 90,
                'risk_score': 20,
                'technical_score': 65,
            },
            {
                'name': 'HDFC Bank Limited',
                'nse_symbol': 'HDFCBANK',
                'bse_symbol': '500180',
                'industry': 'Private Sector Bank',
                'sector': 'Financials',
                'about': 'HDFC Bank Limited is an Indian banking and financial services company headquartered in Mumbai. It is India’s largest private sector bank by assets and the world’s tenth largest bank by market capitalization as of May 2026.',
                'current_price': 1640.25,
                'market_cap': 1248900.00,
                'high_52w': 1790.00,
                'low_52w': 1360.00,
                'pe_ratio': 18.20,
                'pb_ratio': 2.45,
                'book_value': 669.00,
                'eps': 90.12,
                'roe': 17.50,
                'roce': 19.80,
                'dividend_yield': 1.16,
                'debt': 980000.00,  # Deposits & Borrowings for banks
                'cash': 124000.00,
                'intrinsic_value': 1950.00,
                'industry_pe': 16.80,
                'promoter_holding': 25.50,
                'sales_growth': 16.20,
                'profit_growth': 19.40,
                'foliux_score': 82,
                'buy_score': 85,
                'valuation_score': 80,
                'growth_score': 85,
                'health_score': 88,
                'risk_score': 22,
                'technical_score': 72,
            }
        ]

        # Quarters list
        quarters = ['Jun 2025', 'Sep 2025', 'Dec 2025', 'Mar 2026', 'Jun 2026']
        # Years list
        years = ['Mar 2022', 'Mar 2023', 'Mar 2024', 'Mar 2025', 'Mar 2026']

        for c_data in companies_data:
            self.stdout.write(f"Seeding {c_data['name']}...")
            company = Company.objects.create(**c_data)

            # 1. Seed Quarterly Results
            sales_factor = 1.0
            for idx, q in enumerate(quarters):
                sales_factor = 1.0 + (idx * 0.04) + random.uniform(-0.02, 0.02)
                base_sales = float(company.market_cap) * 0.012 * sales_factor
                base_expenses = base_sales * 0.82
                base_op = base_sales - base_expenses
                QuarterlyResult.objects.create(
                    company=company,
                    quarter=q,
                    sales=round(base_sales, 2),
                    expenses=round(base_expenses, 2),
                    operating_profit=round(base_op, 2),
                    opm_percent=round((base_op / base_sales) * 100, 2),
                    other_income=round(base_sales * 0.02, 2),
                    interest=round(base_sales * 0.015, 2),
                    depreciation=round(base_sales * 0.03, 2),
                    profit_before_tax=round(base_op + (base_sales * 0.02) - (base_sales * 0.045), 2),
                    tax_percent=25.00,
                    net_profit=round((base_op + (base_sales * 0.02) - (base_sales * 0.045)) * 0.75, 2),
                    eps=round(((base_op + (base_sales * 0.02) - (base_sales * 0.045)) * 0.75) / 100.0, 2)
                )

            # 2. Seed Yearly Profit & Loss
            for idx, y in enumerate(years):
                growth_factor = 1.0 + (idx * 0.08) + random.uniform(-0.03, 0.03)
                y_sales = float(company.market_cap) * 0.05 * growth_factor
                y_expenses = y_sales * 0.81
                y_op = y_sales - y_expenses
                ProfitLoss.objects.create(
                    company=company,
                    year=y,
                    sales=round(y_sales, 2),
                    expenses=round(y_expenses, 2),
                    operating_profit=round(y_op, 2),
                    opm_percent=round((y_op / y_sales) * 100, 2),
                    other_income=round(y_sales * 0.02, 2),
                    interest=round(y_sales * 0.015, 2),
                    depreciation=round(y_sales * 0.03, 2),
                    profit_before_tax=round(y_op + (y_sales * 0.02) - (y_sales * 0.045), 2),
                    tax_percent=25.00,
                    net_profit=round((y_op + (y_sales * 0.02) - (y_sales * 0.045)) * 0.75, 2),
                    eps=round(float(company.eps) * 0.8 + (idx * 5.2), 2),
                    dividend_payout_percent=20.00
                )

            # 3. Seed Balance Sheet
            for idx, y in enumerate(years):
                growth_factor = 1.0 + (idx * 0.07)
                cap = float(company.market_cap) * 0.008
                res = float(company.market_cap) * 0.15 * growth_factor
                debt_val = float(company.debt) * 0.95 * (1.0 - idx * 0.03)
                other_liab = res * 0.15
                total_l = cap + res + debt_val + other_liab
                
                BalanceSheet.objects.create(
                    company=company,
                    year=y,
                    share_capital=round(cap, 2),
                    reserves=round(res, 2),
                    borrowings=round(debt_val, 2),
                    other_liabilities=round(other_liab, 2),
                    total_liabilities=round(total_l, 2),
                    fixed_assets=round(total_l * 0.55, 2),
                    cwip=round(total_l * 0.05, 2),
                    investments=round(total_l * 0.20, 2),
                    other_assets=round(total_l * 0.20, 2),
                    total_assets=round(total_l, 2)
                )

            # 4. Seed Cash Flow
            for idx, y in enumerate(years):
                growth_factor = 1.0 + (idx * 0.06)
                op_c = float(company.market_cap) * 0.015 * growth_factor
                inv_c = -op_c * 0.7
                fin_c = -op_c * 0.25
                net_cf = op_c + inv_c + fin_c
                CashFlow.objects.create(
                    company=company,
                    year=y,
                    operating_cash=round(op_c, 2),
                    investing_cash=round(inv_c, 2),
                    financing_cash=round(fin_c, 2),
                    net_cash_flow=round(net_cf, 2)
                )

            # 5. Seed Shareholding Pattern
            prom = float(company.promoter_holding)
            for idx, q in enumerate(quarters):
                fii = 20.0 + idx * 0.2 + random.uniform(-0.1, 0.1)
                dii = 15.0 - idx * 0.15 + random.uniform(-0.1, 0.1)
                govt = 1.5 + random.uniform(-0.05, 0.05)
                pub = 100.0 - (prom + fii + dii + govt)
                ShareholdingPattern.objects.create(
                    company=company,
                    period=q,
                    promoters=round(prom, 2),
                    fiis=round(fii, 2),
                    diis=round(dii, 2),
                    public=round(pub, 2),
                    government=round(govt, 2)
                )

            # 6. Seed Company Documents
            CompanyDocument.objects.create(
                company=company,
                title=f"Annual Report FY 2025-26 - {company.nse_symbol}",
                category="Annual Reports",
                url="https://foliux.com/media/annual_reports/mock_report.pdf",
                date=datetime.now().date() - timedelta(days=60)
            )
            CompanyDocument.objects.create(
                company=company,
                title=f"Investor Presentation Q1 FY27 - {company.nse_symbol}",
                category="Investor Presentations",
                url="https://foliux.com/media/investor_presentations/mock_presentation.pdf",
                date=datetime.now().date() - timedelta(days=15)
            )
            CompanyDocument.objects.create(
                company=company,
                title=f"Concall Transcript Q1 FY27 - {company.nse_symbol}",
                category="Concall Transcripts",
                url="https://foliux.com/media/concalls/mock_transcript.pdf",
                date=datetime.now().date() - timedelta(days=12)
            )

            # 7. Seed Daily Historical Prices for the last 300 days (for Candlestick Chart)
            base_price = float(company.current_price)
            current_date = datetime.now() - timedelta(days=300)
            close_price = base_price * 0.85  # Start lower and walk up

            historical_price_list = []
            for day in range(300):
                current_date += timedelta(days=1)
                # Skip weekends
                if current_date.weekday() in (5, 6):
                    continue
                
                open_p = close_price
                change = open_p * random.uniform(-0.018, 0.02)
                close_p = open_p + change
                
                high_p = max(open_p, close_p) * random.uniform(1.001, 1.015)
                low_p = min(open_p, close_p) * random.uniform(0.985, 0.999)
                vol = random.randint(500000, 4500000)
                
                # Check for extreme swings
                if high_p < low_p:
                    high_p, low_p = low_p, high_p
                
                historical_price_list.append(
                    HistoricalPrice(
                        company=company,
                        date=current_date.date(),
                        open_price=round(open_p, 2),
                        high_price=round(high_p, 2),
                        low_price=round(low_p, 2),
                        close_price=round(close_p, 2),
                        volume=vol
                    )
                )
                close_price = close_p  # Next open is this close

            HistoricalPrice.objects.bulk_create(historical_price_list)
            self.stdout.write(f"Seeded 300 historical price points for {company.nse_symbol}")

        self.stdout.write(self.style.SUCCESS("Screener database seeding complete!"))
