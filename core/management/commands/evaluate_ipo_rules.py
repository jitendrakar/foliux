from django.core.management.base import BaseCommand
from core.ipo_rules import evaluate_closing_day_ipo_advice

class Command(BaseCommand):
    help = 'Evaluate automated closing day IPO advice rule (Subscription >= 3x AND GMP > 30% -> APPLY)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force evaluation regardless of closing date or time',
        )

    def handle(self, *args, **options):
        force = options['force']
        self.stdout.write("Running automated closing day IPO rule evaluation...")
        
        results = evaluate_closing_day_ipo_advice(force=force)
        for r in results:
            if r['status'] == 'SKIPPED':
                self.stdout.write(f"SKIPPED {r['name']}: {r['reason']}")
            else:
                color = self.style.SUCCESS if r['rule_passed'] else self.style.WARNING
                self.stdout.write(color(
                    f"UPDATED {r['name']} -> Advise: {r['new_advise']} "
                    f"(Sub: {r['subscription']}, GMP: {r['gmp_percent']}%)"
                ))
