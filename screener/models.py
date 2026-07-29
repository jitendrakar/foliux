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

    class Meta:
        ordering = ['-overall_score', '-reliability_score_percent']

    def __str__(self):
        return f"{self.company.name} - Reliability Score: {self.overall_score}/100 ({self.reliability_score_percent}%)"

