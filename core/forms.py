from django import forms
from .models import Portfolio, Profile, Loan, LoanPayment
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    full_name = forms.CharField(max_length=100, required=True, label='Name / Nick Name')
    email = forms.EmailField(required=True, label='Email ID')
    mobile_number = forms.CharField(max_length=15, required=True, label='Mobile Number')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('full_name', 'email', 'mobile_number')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(username=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists. '
                'Please login or reset your password if you forgot it.'
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = user.email  # Set username to email
        if commit:
            user.save()
            # Handle Name and Mobile via Profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.full_name = self.cleaned_data['full_name']
            profile.mobile_number = self.cleaned_data['mobile_number']
            profile.save()
        return user

GENDER_CHOICES = [
    ('', '--- Select Gender ---'),
    ('MALE', 'Male'),
    ('FEMALE', 'Female'),
    ('OTHER', 'Other'),
]

class ProfileForm(forms.ModelForm):
    gender = forms.ChoiceField(choices=GENDER_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}), required=False)

    class Meta:
        model = Profile
        fields = [
            'full_name', 'profile_picture', 'mobile_number', 'date_of_birth', 'gender', 
            'investor_type', 'initial_investment_limit',
            'mf_investment_limit', 'coin_investment_limit',
            'equity_profit_expectation', 'mf_profit_expectation', 'coin_profit_expectation',
            'equity_fixed_charge', 'equity_brokerage_pct',
            'intraday_fixed_charge', 'intraday_brokerage_pct',
            'financial_goal'
        ]
        labels = {
            'full_name': 'Name / Nick Name',
            'profile_picture': 'Profile Photo',
            'mobile_number': 'Mobile Number',
            'date_of_birth': 'Date of Birth',
            'gender': 'Gender',
            'investor_type': 'Investor Type',
            'initial_investment_limit': 'Maximum Investment per Stock/ETF',
            'mf_investment_limit': 'Maximum Investment per Mutual Fund',
            'coin_investment_limit': 'Maximum Investment for Coin (Crypto)',
            'equity_profit_expectation': 'Profit Expectation per Stock/ETF (%)',
            'mf_profit_expectation': 'Profit Expectation per Mutual Fund (%)',
            'coin_profit_expectation': 'Profit Expectation for Coin (Crypto) (%)',
            'equity_fixed_charge': 'Delivery Fixed Charge (0.0)',
            'equity_brokerage_pct': 'Delivery Brokerage Charge (%)',
            'intraday_fixed_charge': 'Intraday Fixed Charge (0.0)',
            'intraday_brokerage_pct': 'Intraday Brokerage Charge (%)',
            'financial_goal': 'Financial Goal',
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name or nick name'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter mobile number'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'investor_type': forms.Select(attrs={'class': 'form-control'}),
            'initial_investment_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'mf_investment_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'coin_investment_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'equity_profit_expectation': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'mf_profit_expectation': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'coin_profit_expectation': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'equity_fixed_charge': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'equity_brokerage_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'intraday_fixed_charge': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'intraday_brokerage_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'financial_goal': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
        }

class EmailOrMobileAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Mobile Number or Email', widget=forms.TextInput(attrs={'autofocus': True, 'class': 'form-control', 'placeholder': 'Enter Mobile Number or Email'}))


class UploadFileForm(forms.Form):
    file = forms.FileField(label="Select CSV/Excel File")

class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['quantity', 'avg_cost']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Quantity'}),
            'avg_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter Avg. Cost'}),
        }

class ManualPortfolioForm(forms.Form):
    company_name = forms.CharField(
        label='COMPANY NAME',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Search company name...',
            'autocomplete': 'off'
        })
    )
    symbol = forms.CharField(
        label='STOCK SYMBOL (AUTO-FILLED)',
        max_length=20, 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Symbol will auto-fill',
            'readonly': 'readonly'
        })
    )
    quantity = forms.IntegerField(
        label='QUANTITY',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Quantity'})
    )
    avg_cost = forms.DecimalField(
        label='AVERAGE COST',
        max_digits=10, 
        decimal_places=2, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter Avg. Cost'})
    )
    date = forms.DateField(
        label='PURCHASE DATE',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    notes = forms.CharField(
        label='NOTES',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional: Why did you select this stock?'}),
        help_text='Visible on hover in portfolio view'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone
        self.fields['date'].widget.attrs['max'] = timezone.now().date().isoformat()

    def clean_date(self):
        date = self.cleaned_data.get('date')
        from django.utils import timezone
        if date and date > timezone.now().date():
            raise forms.ValidationError("Date cannot be in the future.")
        return date

class ManualSellForm(forms.Form):
    company_name = forms.CharField(
        label='COMPANY NAME',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Search company name to sell...',
            'autocomplete': 'off'
        })
    )
    symbol = forms.CharField(
        label='STOCK SYMBOL (AUTO-FILLED)',
        max_length=20, 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Symbol will auto-fill',
            'readonly': 'readonly'
        })
    )
    quantity = forms.IntegerField(
        label='QUANTITY TO SELL',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Quantity to sell'})
    )
    price = forms.DecimalField(
        label='SELL PRICE',
        max_digits=10, 
        decimal_places=2, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter Sell Price'})
    )
    date = forms.DateField(
        label='EXIT DATE',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    notes = forms.CharField(
        label='NOTES (OPTIONAL)',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Why are you selling?'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone
        self.fields['date'].widget.attrs['max'] = timezone.now().date().isoformat()

    def clean_date(self):
        date = self.cleaned_data.get('date')
        from django.utils import timezone
        if date and date > timezone.now().date():
            raise forms.ValidationError("Date cannot be in the future.")
        return date

class EditLotForm(forms.Form):
    quantity = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity'})
    )
    price = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Price'})
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone
        self.fields['date'].widget.attrs['max'] = timezone.now().date().isoformat()

    def clean_date(self):
        date = self.cleaned_data.get('date')
        from django.utils import timezone
        if date and date > timezone.now().date():
            raise forms.ValidationError("Date cannot be in the future.")
        return date

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your registered email'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("No user found with this email address.")
        return email

class VerifyOTPForm(forms.Form):
    otp = forms.CharField(
        label='6-Digit Code',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 6-digit code'})
    )

class SetPasswordForm(forms.Form):
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'})
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = [
            'bank_name', 'category', 'loan_amount', 'start_date', 
            'interest_rate', 'interest_type', 'tenure_months', 
            'emi_amount', 'interest_lock', 'next_emi_date'
        ]
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. HDFC Bank'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'loan_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total Principal'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Annual Rate %'}),
            'interest_type': forms.Select(attrs={'class': 'form-control'}),
            'tenure_months': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total months'}),
            'emi_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Monthly EMI'}),
            'interest_lock': forms.Select(attrs={'class': 'form-control'}),
            'next_emi_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class LoanPaymentForm(forms.ModelForm):
    class Meta:
        model = LoanPayment
        fields = ['payment_type', 'amount', 'date', 'principal_component', 'interest_component']
        widgets = {
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'principal_component': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'interest_component': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

from .models import UserReview
class UserReviewForm(forms.ModelForm):
    class Meta:
        model = UserReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, f"{i} Stars") for i in range(5, 0, -1)], attrs={'class': 'form-select rounded-pill'}),
            'comment': forms.Textarea(attrs={'class': 'form-control rounded-4', 'rows': 4, 'placeholder': 'Tell us about your experience with FOLIUX...'}),
        }
