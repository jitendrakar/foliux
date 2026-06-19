from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from core.tax_utils import calculate_taxes, calc_slab_tax_old, calc_slab_tax_new

class TaxCalculatorTests(TestCase):
    def test_calc_slab_tax_old(self):
        self.assertEqual(calc_slab_tax_old(Decimal('0')), 0)
        self.assertEqual(calc_slab_tax_old(Decimal('250000')), 0)
        self.assertEqual(calc_slab_tax_old(Decimal('300000')), 2500) # (300000-250000)*0.05 = 2500
        self.assertEqual(calc_slab_tax_old(Decimal('600000')), 32500) # 12500 + 100000*0.2 = 32500
        self.assertEqual(calc_slab_tax_old(Decimal('1200000')), 172500) # 112500 + 200000*0.3 = 172500

    def test_calc_slab_tax_new(self):
        self.assertEqual(calc_slab_tax_new(Decimal('0')), 0)
        self.assertEqual(calc_slab_tax_new(Decimal('400000')), 0)
        self.assertEqual(calc_slab_tax_new(Decimal('600000')), 10000) # (600000-400000)*0.05 = 10000
        self.assertEqual(calc_slab_tax_new(Decimal('1000000')), 40000) # 20000 + 200000*0.1 = 40000
        self.assertEqual(calc_slab_tax_new(Decimal('1500000')), 105000) # 60000 + 300000*0.15 = 105000
        self.assertEqual(calc_slab_tax_new(Decimal('2500000')), 330000) # 300000 + 100000*0.3 = 330000

    def test_calculate_taxes_basic(self):
        # Salary 6,00,000, no other details
        state = {
            'salary': Decimal('600000'),
            'section_80c': Decimal('50000'),
            'section_80d': Decimal('10000'),
        }
        res = calculate_taxes(state)
        # Verify New regime standard deduction (75k)
        # Taxable normal income under new regime: 600k - 75k = 525k
        # Slabs tax: (525k - 400k) * 5% = 6250
        # Since 525k <= 12L, u/s 87A rebate applies, rebate = 6250. Net tax = 0!
        self.assertEqual(res['regimes']['new']['deductions'], 75000.0)
        self.assertEqual(res['regimes']['new']['taxable_income'], 525000.0)
        self.assertEqual(res['regimes']['new']['total_tax'], 0.0)

        # Verify Old regime standard deduction (50k)
        # Deductions: standard deduction (50k) + 80C (50k) + 80D (10k) = 110k
        # Taxable normal income under old regime: 600k - 110k = 490k
        # Slabs tax: (490k - 250k) * 5% = 12000
        # Since 490k <= 5L, u/s 87A rebate applies, rebate = 12000. Net tax = 0!
        self.assertEqual(res['regimes']['old']['deductions'], 110000.0)
        self.assertEqual(res['regimes']['old']['taxable_income'], 490000.0)
        self.assertEqual(res['regimes']['old']['total_tax'], 0.0)

    def test_marginal_relief_87a_new_regime(self):
        # Taxable income for rebate is slightly above 12L (e.g. 12,05,000 net taxable normal income after standard deduction)
        # Gross salary 12,80,000 -> net taxable normal: 12,80,000 - 75,000 = 12,05,000
        state = {
            'salary': Decimal('1280000'),
        }
        res = calculate_taxes(state)
        # Without rebate, base tax on 12.05L is:
        # up to 4L: 0
        # 4L - 8L: 20000
        # 8L - 12L: 40000
        # 12L - 12.05L: 5000 * 15% = 750
        # Total base tax = 60750
        # Excess income = 1205000 - 1200000 = 5000
        # Rebate = base_tax - excess_income = 60750 - 5000 = 55750
        # Net tax before cess = 5000
        # Total tax with 4% cess = 5200
        self.assertEqual(res['regimes']['new']['taxable_normal'], 1205000.0)
        self.assertEqual(res['regimes']['new']['rebate'], 55750.0)
        self.assertEqual(res['regimes']['new']['total_tax'], 5200.0)

    def test_null_safety_in_portfolio_data(self):
        from unittest.mock import patch
        from core.tax_utils import get_tax_portfolio_data
        from core.models import FixedAsset, OtherAsset
        from datetime import date
        
        user = User.objects.create_user(username='testtaxuser', password='password')
        
        fa = FixedAsset.objects.create(
            user=user,
            asset_type='RD',
            invested_amount='10000',
            interest_rate='6.5',
            investment_date=date(2025, 4, 1),
            monthly_deposit=1000
        )
        
        oa = OtherAsset.objects.create(
            user=user,
            name='Test Flat',
            asset_type='Flat',
            purchase_date=date(2025, 4, 1),
            purchase_price=Decimal('5000000'),
            monthly_rent=15000
        )
        
        fa.monthly_deposit = None
        oa.monthly_rent = None
        
        with patch('core.models.FixedAsset.objects.filter') as mock_fa_filter, \
             patch('core.models.OtherAsset.objects.filter') as mock_oa_filter:
            
            mock_fa_filter.return_value = [fa]
            mock_oa_filter.return_value = [oa]
            
            try:
                data = get_tax_portfolio_data(user, '2025-2026')
            except TypeError as e:
                self.fail(f"get_tax_portfolio_data failed with TypeError: {e}")
                
            self.assertEqual(data['rental_income'], Decimal('0'))
            self.assertGreaterEqual(data['fd_interest'], Decimal('0'))

    def test_transaction_nulls_and_missing_funds(self):
        from unittest.mock import patch, MagicMock, PropertyMock
        from core.tax_utils import get_tax_portfolio_data
        from core.models import MFTransaction, CoinTransaction, NPSTransaction, PnLStatement
        from datetime import date
        
        user = User.objects.create_user(username='testtaxuser3', password='password')
        
        mft = MagicMock(spec=MFTransaction)
        mft.fund_id = 999
        type(mft).fund = PropertyMock(side_effect=Exception("Fund does not exist"))
        mft.transaction_type = 'BUY'
        mft.units = None
        mft.price = None
        mft.date = date(2025, 6, 1)
        
        ct = MagicMock(spec=CoinTransaction)
        ct.coin_id = 888
        ct.transaction_type = 'SELL'
        ct.units = None
        ct.price = None
        ct.date = date(2025, 6, 1)
        
        pnl = MagicMock(spec=PnLStatement)
        pnl.entry_date = date(2025, 4, 1)
        pnl.exit_date = date(2025, 6, 1)
        pnl.realized_profit = None
        
        with patch('core.models.MFTransaction.objects.filter') as mock_mft_filter, \
             patch('core.models.CoinTransaction.objects.filter') as mock_ct_filter, \
             patch('core.models.PnLStatement.objects.filter') as mock_pnl_filter, \
             patch('core.models.NPSTransaction.objects.filter') as mock_nps_filter:
            
            mock_mft_filter.return_value.order_by.return_value = [mft]
            mock_ct_filter.return_value.order_by.return_value = [ct]
            mock_pnl_filter.return_value = [pnl]
            mock_nps_filter.return_value = []
            
            try:
                data = get_tax_portfolio_data(user, '2025-2026')
            except Exception as e:
                self.fail(f"get_tax_portfolio_data failed with exception: {e}")
                
            self.assertEqual(data['stcg_equity'], Decimal('0'))
            self.assertEqual(data['crypto_gains'], Decimal('0'))



