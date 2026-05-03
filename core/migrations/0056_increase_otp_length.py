from django.db import migrations, models
import encrypted_model_fields.fields

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0055_hiddensignal'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otp',
            name='code',
            field=encrypted_model_fields.fields.EncryptedCharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='signupotp',
            name='code',
            field=encrypted_model_fields.fields.EncryptedCharField(max_length=255),
        ),
    ]
