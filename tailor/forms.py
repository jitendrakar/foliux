from django import forms
from .models import TailorAppointment, TailorMeasurement, TailorUser, TailorService

class TailorAppointmentForm(forms.ModelForm):
    class Meta:
        model = TailorAppointment
        fields = [
            'customer_name', 'mobile', 'email', 'gender', 
            'service', 'appointment_date', 'appointment_time', 'home_visit', 'message'
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter mobile number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'gender': forms.Select(choices=[('', 'Select Gender'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], attrs={'class': 'form-select'}),
            'service': forms.Select(attrs={'class': 'form-select'}),
            'appointment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'home_visit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any specific styling or fabric notes?'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = TailorService.objects.filter(status=True)


class TailorMeasurementForm(forms.ModelForm):
    class Meta:
        model = TailorMeasurement
        fields = ['height', 'chest', 'waist', 'hip', 'shoulder', 'sleeve', 'neck', 'inseam', 'notes']
        widgets = {
            'height': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Height (e.g. 175 cm / 5.8 ft)'}),
            'chest': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chest size in inches'}),
            'waist': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Waist size in inches'}),
            'hip': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hip size in inches'}),
            'shoulder': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Shoulder width in inches'}),
            'sleeve': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sleeve length in inches'}),
            'neck': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Neck size in inches'}),
            'inseam': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Inseam length in inches'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any fit preferences (tight, comfort, loose)?'}),
        }


class CustomerRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}))

    class Meta:
        model = TailorUser
        fields = ['name', 'mobile', 'email', 'address', 'gender']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter name'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter mobile number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Billing/Delivery Address'}),
            'gender': forms.Select(choices=[('', 'Select Gender'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], attrs={'class': 'form-select'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if TailorUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if TailorUser.objects.filter(mobile=mobile).exists():
            raise forms.ValidationError("A user with this mobile number already exists.")
        return mobile

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")


class TailorLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}))
