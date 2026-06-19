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
