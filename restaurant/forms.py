from django import forms
from .models import Reservation, ContactMessage, NewsletterSubscription
import datetime

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['name', 'email', 'phone', 'date', 'time', 'guests', 'special_request']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name', 'required': 'true'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email', 'required': 'true'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number', 'required': 'true'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': 'true'}),
            'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'required': 'true'}),
            'guests': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Number of Guests', 'required': 'true'}),
            'special_request': forms.Textarea(attrs={'class': 'form-control', 'rows': '3', 'placeholder': 'Any special request or dietary requirements...'}),
        }

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date < datetime.date.today():
            raise forms.ValidationError("You cannot book a reservation for a past date.")
        return date

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name', 'required': 'true'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email', 'required': 'true'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject', 'required': 'true'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': '5', 'placeholder': 'Your Message', 'required': 'true'}),
        }

class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscription
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address', 'required': 'true'}),
        }
