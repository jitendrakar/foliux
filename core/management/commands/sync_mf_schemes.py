import requests
from django.core.management.base import BaseCommand
from core.models import MutualFundScheme

class Command(BaseCommand):
    help = 'Synchronize the local database with all mutual fund schemes from mfapi.in'

    def handle(self, *args, **options):
        self.stdout.write("Fetching all mutual fund schemes from mfapi.in...")
        try:
            res = requests.get('https://api.mfapi.in/mf', timeout=60)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            self.stderr.write(f"Error fetching data from API: {e}")
            return

        total = len(data)
        self.stdout.write(f"Fetched {total} schemes. Updating database...")

        # Prepare records for insertion/update
        schemes_to_upsert = []
        for item in data:
            code = str(item['schemeCode'])
            name = item['schemeName']
            isin_growth = item.get('isinGrowth')
            isin_div = item.get('isinDivReinvestment')
            
            schemes_to_upsert.append(
                MutualFundScheme(
                    scheme_code=code,
                    scheme_name=name,
                    isin_growth=isin_growth,
                    isin_div_reinvestment=isin_div
                )
            )

        self.stdout.write("Saving to database in batches...")
        batch_size = 5000
        
        # Django bulk_create with update_conflicts
        try:
            for i in range(0, len(schemes_to_upsert), batch_size):
                batch = schemes_to_upsert[i:i+batch_size]
                MutualFundScheme.objects.bulk_create(
                    batch,
                    update_conflicts=True,
                    unique_fields=['scheme_code'],
                    update_fields=['scheme_name', 'isin_growth', 'isin_div_reinvestment']
                )
                self.stdout.write(f"Processed {min(i+batch_size, total)}/{total}...")
        except Exception as e:
            self.stderr.write(f"Error using bulk_create with update_conflicts: {e}")
            self.stdout.write("Falling back to bulk_create with ignore_conflicts...")
            # Fallback
            for i in range(0, len(schemes_to_upsert), batch_size):
                batch = schemes_to_upsert[i:i+batch_size]
                MutualFundScheme.objects.bulk_create(
                    batch,
                    ignore_conflicts=True
                )
                self.stdout.write(f"Processed {min(i+batch_size, total)}/{total}...")

        self.stdout.write(self.style.SUCCESS(f"Successfully synchronized {total} mutual fund schemes!"))
