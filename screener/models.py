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
