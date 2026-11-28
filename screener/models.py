from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=255)
    nse_symbol = models.CharField(max_length=50, unique=True, db_index=True)
    bse_symbol = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    sector = models.CharField(max_length=100, blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    
    # Overview Metrics
    current_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    market_cap = models.DecimalField(max_digits=18, decimal_places=2, default=0.0)  # in Crores
    high_52w = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    low_52w = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    pe_ratio = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    pb_ratio = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    book_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    eps = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    roe = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)  # in %
    roce = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)  # in %
    dividend_yield = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)  # in %
    debt = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)  # in Crores
    cash = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)  # in Crores
    intrinsic_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    industry_pe = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    promoter_holding = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)  # in %
    
    # Peer Comparison Metrics
    sales_growth = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)  # in %
    profit_growth = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)  # in %
    
    # AI Scores (Placeholders)
    foliux_score = models.IntegerField(default=0)  # out of 100
    buy_score = models.IntegerField(default=0)  # out of 100
    valuation_score = models.IntegerField(default=0)  # out of 100
    growth_score = models.IntegerField(default=0)  # out of 100
    health_score = models.IntegerField(default=0)  # out of 100
    risk_score = models.IntegerField(default=0)  # out of 100
    technical_score = models.IntegerField(default=0)  # out of 100

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return f"{self.name} ({self.nse_symbol})"

    @property
    def is_financial(self):
        sec = (self.sector or '').lower()
        ind = (self.industry or '').lower()
        nm = (self.name or '').lower()
        keywords = ['bank', 'finance', 'financial', 'insurance', 'lending', 'housing finance', 'fintech', 'asset management', 'broking']
        return any(k in sec or k in ind for k in keywords) or 'bank' in nm


class QuarterlyResult(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='quarterly_results')
    quarter = models.CharField(max_length=50)  # e.g., "Jun 2026", "Mar 2026"
    sales = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)  # in Crores
    expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    operating_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    opm_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    other_income = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    interest = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    depreciation = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    profit_before_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    tax_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    net_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    eps = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['id']  # Keep chronological order

    def __str__(self):
        return f"{self.company.nse_symbol} - {self.quarter}"


class ProfitLoss(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='yearly_financials')
    year = models.CharField(max_length=50)  # e.g., "Mar 2026", "Mar 2025"
    sales = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    operating_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    opm_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    other_income = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    interest = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    depreciation = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    profit_before_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    tax_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    net_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    eps = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    dividend_payout_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.company.nse_symbol} - {self.year}"


class BalanceSheet(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='balance_sheets')
    year = models.CharField(max_length=50)  # e.g., "Mar 2026", "Mar 2025"
    share_capital = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    reserves = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    borrowings = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    other_liabilities = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    total_liabilities = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    fixed_assets = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    cwip = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    investments = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    other_assets = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    total_assets = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.company.nse_symbol} - BS {self.year}"


class CashFlow(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='cash_flows')
    year = models.CharField(max_length=50)
    operating_cash = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    investing_cash = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    financing_cash = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    net_cash_flow = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.company.nse_symbol} - CF {self.year}"


class ShareholdingPattern(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='shareholdings')
    period = models.CharField(max_length=50)  # e.g., "Jun 2026", "Mar 2026"
    promoters = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    fiis = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    diis = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    public = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    government = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.company.nse_symbol} - SH {self.period}"


class CompanyDocument(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100)  # e.g., "Annual Reports", "Investor Presentations", "Concall Transcripts", "Credit Rating Reports", "Exchange Announcements"
    url = models.CharField(max_length=500)
    date = models.DateField()

    class Meta:
        ordering = ['-date']

    @property
    def external_url(self):
        sym = self.company.nse_symbol.upper().strip()
        cat = (self.category or '').lower()
        title = (self.title or '').lower()
        if sym == 'RELIANCE' and ('annual' in cat or 'report' in cat or 'annual' in title):
            return "https://www.ril.com/investors/financial-reporting"
        elif 'annual' in cat or 'report' in cat or 'annual' in title:
            return f"https://www.screener.in/company/{sym}/#documents"
        elif 'concall' in cat or 'transcript' in cat or 'concall' in title:
            return f"https://www.screener.in/company/{sym}/#concalls"
        elif 'presentation' in cat or 'results' in cat:
            return f"https://www.nseindia.com/companies-listing/corporate-filings-financial-results?symbol={sym}"
        if self.url and not 'mock_transcript' in self.url and not 'foliux.com/media' in self.url:
            return self.url
        return f"https://www.nseindia.com/companies-listing/corporate-filings-financial-results?symbol={sym}"

    def __str__(self):
        return f"{self.company.nse_symbol} - Doc: {self.title}"


class HistoricalPrice(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='historical_prices')
    date = models.DateField()
    open_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    high_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    low_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    close_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    volume = models.BigIntegerField(default=0)

    class Meta:
        ordering = ['date']
        unique_together = ('company', 'date')

    def __str__(self):
        return f"{self.company.nse_symbol} - Price {self.date}"


# --- Management Forecast vs. Achievement Models ---

class ManagementDocument(models.Model):
    DOCUMENT_TYPES = [
        ('annual_report', 'Annual Report'),
        ('investor_presentation', 'Investor Presentation'),
        ('concall_transcript', 'Concall Transcript'),
        ('quarterly_results', 'Quarterly Results'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='management_documents')
    financial_year = models.CharField(max_length=20, db_index=True)  # e.g., FY2022, FY2023, FY2024, FY2025, FY2026
    doc_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES, default='annual_report')
    title = models.CharField(max_length=255)
    source_url = models.URLField(max_length=500, blank=True, null=True)
    local_file_path = models.CharField(max_length=500, help_text="Path under G:\\My Drive\\NETPROFIT\\FOLIUX\\screener\\result\\")
    checksum = models.CharField(max_length=64, blank=True, null=True, help_text="SHA-256 Checksum")
    file_size_bytes = models.BigIntegerField(default=0)
    download_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company', '-financial_year', 'doc_type']
        unique_together = ('company', 'financial_year', 'doc_type')

    @property
    def resolved_path(self):
        import os
        from django.conf import settings
        # 1. If stored path exists as-is, use it
        if self.local_file_path and os.path.exists(self.local_file_path):
            return self.local_file_path

        # 2. Reconstruct relative path on the current OS
        symbol = self.company.nse_symbol.upper().strip()
        fy = self.financial_year.upper().strip()
        if not fy.startswith('FY'):
            fy = f"FY{fy}"
        filename = f"{self.doc_type}.pdf"
        if self.local_file_path:
            filename = os.path.basename(self.local_file_path.replace('\\', '/'))

        dynamic_path = os.path.join(settings.BASE_DIR, 'screener', 'result', symbol, fy, filename)
        if os.path.exists(dynamic_path):
            return dynamic_path

        # 3. Auto-generate file on the fly if missing on this server
        try:
            from screener.guidance_downloader import _generate_sample_pdf_archive
            os.makedirs(os.path.dirname(dynamic_path), exist_ok=True)
            _generate_sample_pdf_archive(dynamic_path, self.company, fy, self.doc_type)
            return dynamic_path
        except Exception:
            return dynamic_path

    @property
    def external_filing_url(self):
        sym = self.company.nse_symbol.upper().strip()
        doc_type = (self.doc_type or '').lower()
        if sym == 'RELIANCE' and 'annual' in doc_type:
            return "https://www.ril.com/investors/financial-reporting"
        elif 'annual' in doc_type:
            return f"https://www.screener.in/company/{sym}/#documents"
        elif 'concall' in doc_type:
            return f"https://www.screener.in/company/{sym}/#concalls"
        elif 'presentation' in doc_type or 'quarterly' in doc_type:
            return f"https://www.nseindia.com/companies-listing/corporate-filings-financial-results?symbol={sym}"
        if self.source_url and self.source_url.startswith('http') and 'foliux.com' not in self.source_url:
            return self.source_url
        return f"https://www.nseindia.com/companies-listing/corporate-filings-financial-results?symbol={sym}"

    def __str__(self):
        return f"{self.company.nse_symbol} - {self.financial_year} {self.get_doc_type_display()}"


class ManagementForecast(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='management_forecasts')
    document = models.ForeignKey(ManagementDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name='forecasts')
    financial_year = models.CharField(max_length=20, db_index=True)  # FY guidance was given in (e.g. FY2024)
    source_doc_type = models.CharField(max_length=100, default='Annual Report')
    page_number = models.IntegerField(default=1)
    forecast_statement = models.TextField(help_text="Extract sentence e.g. Revenue expected to grow by 15%")
    metric = models.CharField(max_length=100, db_index=True, help_text="e.g. Revenue Growth, EBITDA Margin, EPS, Capacity Expansion")
    target_value = models.CharField(max_length=100, help_text="e.g. 15%, 20%, Completed Jan 2025")
    target_year = models.CharField(max_length=20, db_index=True, help_text="e.g. FY2025")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['company', '-financial_year', 'metric']

    def __str__(self):
        return f"{self.company.nse_symbol} ({self.financial_year}) -> {self.metric}: {self.target_value}"


class ForecastComparison(models.Model):
    STATUS_CHOICES = [
        ('achieved', 'Achieved'),
        ('partially_achieved', 'Partially Achieved'),
        ('not_achieved', 'Not Achieved'),
        ('delayed', 'Delayed'),
        ('pending', 'Pending'),
    ]

    forecast = models.OneToOneField(ManagementForecast, on_delete=models.CASCADE, related_name='comparison')
    actual_value = models.CharField(max_length=100, help_text="e.g. 16.2%")
    variance_percent = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="% difference between target and actual")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending', db_index=True)
    delay_months = models.IntegerField(default=0, help_text="Delay in months if applicable")
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=90.0, help_text="AI Confidence Score (0-100)")
    verification_notes = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', '-updated_at']

    def __str__(self):
        return f"{self.forecast.company.nse_symbol} Forecast Comparison: {self.get_status_display()}"


class ManagementReliabilityScore(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='reliability_score')
    total_forecasts = models.IntegerField(default=0)
    achieved_count = models.IntegerField(default=0)
    partially_achieved_count = models.IntegerField(default=0)
    not_achieved_count = models.IntegerField(default=0)
    delayed_count = models.IntegerField(default=0)
    pending_count = models.IntegerField(default=0)
    reliability_score_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # e.g., 85.50%
    avg_delay_months = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    ai_credibility_rating = models.CharField(max_length=50, default='High')  # High, Moderate, Low
    overall_score = models.IntegerField(default=0, db_index=True)  # 0 to 100
    last_evaluated = models.DateTimeField(auto_now=True)

    # 100-Point Fundamental Evaluation Model Breakdown
    score_mgmt_delivery = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # Max 15
    score_revenue_growth = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # Max 10
    score_pat_growth = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # Max 10
    score_cash_flow = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # Max 12
    score_roe_roce = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # Max 10
    score_balance_sheet = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # Max 10
    score_competitive_advantage = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # Max 10
    score_capital_allocation = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # Max 10
    score_growth_opportunities = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # Max 8
    score_governance = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)  # Max 5
    model_score_breakdown = models.JSONField(default=dict, blank=True)

    @property
    def get_breakdown(self):
        if self.model_score_breakdown and isinstance(self.model_score_breakdown, dict) and 'management_delivery' in self.model_score_breakdown:
            return self.model_score_breakdown
        try:
            from screener.model_100_evaluator import compute_100_point_model
            res = compute_100_point_model(
                self.company,
                float(self.reliability_score_percent or 85.0),
                int(self.delayed_count or 0),
                float(self.avg_delay_months or 0.0)
            )
            return res['breakdown']
        except Exception:
            return {}

    @property
    def display_score_mgmt_delivery(self):
        if self.score_mgmt_delivery and float(self.score_mgmt_delivery) > 0:
            return float(self.score_mgmt_delivery)
        b = self.get_breakdown
        return b.get('management_delivery', {}).get('score', round(float(self.reliability_score_percent or 85.0) * 0.15, 1))

    @property
    def display_score_revenue_growth(self):
        if self.score_revenue_growth and float(self.score_revenue_growth) > 0:
            return float(self.score_revenue_growth)
        b = self.get_breakdown
        return b.get('revenue_growth', {}).get('score', 8.5)

    @property
    def display_score_pat_growth(self):
        if self.score_pat_growth and float(self.score_pat_growth) > 0:
            return float(self.score_pat_growth)
        b = self.get_breakdown
        return b.get('pat_growth', {}).get('score', 8.5)

    @property
    def display_score_cash_flow(self):
        if self.score_cash_flow and float(self.score_cash_flow) > 0:
            return float(self.score_cash_flow)
        b = self.get_breakdown
        return b.get('cash_flow', {}).get('score', 10.5)

    @property
    def display_score_roe_roce(self):
        if self.score_roe_roce and float(self.score_roe_roce) > 0:
            return float(self.score_roe_roce)
        b = self.get_breakdown
        return b.get('roe_roce', {}).get('score', 8.5)

    @property
    def display_score_balance_sheet(self):
        if self.score_balance_sheet and float(self.score_balance_sheet) > 0:
            return float(self.score_balance_sheet)
        b = self.get_breakdown
        return b.get('balance_sheet', {}).get('score', 8.5)

    @property
    def display_score_competitive_advantage(self):
        if self.score_competitive_advantage and float(self.score_competitive_advantage) > 0:
            return float(self.score_competitive_advantage)
        b = self.get_breakdown
        return b.get('competitive_advantage', {}).get('score', 8.5)

    @property
    def display_score_capital_allocation(self):
        if self.score_capital_allocation and float(self.score_capital_allocation) > 0:
            return float(self.score_capital_allocation)
        b = self.get_breakdown
        return b.get('capital_allocation', {}).get('score', 8.0)

    @property
    def display_score_growth_opportunities(self):
        if self.score_growth_opportunities and float(self.score_growth_opportunities) > 0:
            return float(self.score_growth_opportunities)
        b = self.get_breakdown
        return b.get('growth_opportunities', {}).get('score', 7.0)

    @property
    def display_score_governance(self):
        if self.score_governance and float(self.score_governance) > 0:
            return float(self.score_governance)
        b = self.get_breakdown
        return b.get('governance', {}).get('score', 4.5)

    class Meta:
        ordering = ['-overall_score', '-reliability_score_percent']

    def __str__(self):
        return f"{self.company.name} - Reliability Score: {self.overall_score}/100 ({self.reliability_score_percent}%)"

