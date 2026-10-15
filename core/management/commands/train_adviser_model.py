"""
Django Management Command: train_adviser_model
Runs the continuous self-learning optimizer for the FOLIUX AI Audio & Voice Investment Adviser.
Analyzes query logs, user feedback (+1 / -1 votes), market volatility regimes,
and updates AdviserLearnedWeight and AdviserVocabularySynonym models.
"""

from django.core.management.base import BaseCommand
from core.audio_adviser import train_and_update_adviser_model
from core.models import AdviserLearnedWeight, AdviserVocabularySynonym, AdviserQueryLog


class Command(BaseCommand):
    help = "Run the continuous self-learning optimization loop for the FOLIUX Audio Investment Adviser."

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Display detailed learned weights across all strategies and regimes.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initiating FOLIUX AI Audio Adviser Continuous Self-Learning Training..."))

        stats = train_and_update_adviser_model()

        self.stdout.write(self.style.SUCCESS("[SUCCESS] Self-learning optimization completed successfully!"))
        self.stdout.write(f"  - Total Queries Analyzed: {stats.get('queries_analyzed', 0)}")
        self.stdout.write(f"  - Positive Feedback Ratio: {stats.get('positive_feedback_ratio', 0.0) * 100:.1f}%")
        self.stdout.write(f"  - Strategy Weights Updated: {stats.get('weights_updated', 0)}")
        self.stdout.write(f"  - Financial Vocabulary Expanded: {stats.get('vocabulary_expanded', 0)}")

        if options.get('verbose'):
            self.stdout.write(self.style.NOTICE("\nCurrent Learned Allocation States:"))
            for learned in AdviserLearnedWeight.objects.all().order_by('strategy_key', 'regime'):
                self.stdout.write(
                    f"  [{learned.strategy_key} | {learned.regime}] "
                    f"Eq: {learned.equity_weight:.0f}% Flex: {learned.flexicap_weight:.0f}% "
                    f"Debt: {learned.debt_weight:.0f}% Gold: {learned.gold_weight:.0f}% | "
                    f"Harvest: {learned.harvest_target_pct:.0f}% Dip: {learned.dip_buy_pct:.1f}% "
                    f"(Conf: {learned.confidence_score * 100:.0f}%, Samples: {learned.sample_count})"
                )

            total_vocab = AdviserVocabularySynonym.objects.count()
            self.stdout.write(f"\nTotal Registered Vocabulary Terms: {total_vocab}")
