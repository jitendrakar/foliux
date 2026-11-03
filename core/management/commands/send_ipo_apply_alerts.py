import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import IPO
from core.utils import send_ipo_apply_notification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send automated email alert to all registered users for IPOs meeting the APPLY condition (Sub >= 3x and GMP > 30%).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ipo',
            type=str,
            help='Specific IPO name or ID to send alert for'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Target specific email address to receive test alert instead of all registered users'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sending email alert even if apply_email_sent is already True'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Send synchronously rather than in a background thread'
        )

    def handle(self, *args, **options):
        ipo_arg = options.get('ipo')
        target_email = options.get('email')
        force = options.get('force', False)
        async_send = not options.get('sync', False)

        qs = IPO.objects.filter(is_active=True, advise='APPLY')
        if ipo_arg:
            if ipo_arg.isdigit():
                qs = qs.filter(id=int(ipo_arg))
            else:
                qs = qs.filter(name__icontains=ipo_arg)

        if not force:
            qs = qs.filter(apply_email_sent=False)

        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.WARNING("No active APPLY IPOs eligible for email alert."))
            return

        recipient_list = [target_email] if target_email else None

        for ipo in qs:
            gmp_safe = (ipo.gmp_display or 'N/A').replace('₹', 'Rs. ')
            self.stdout.write(
                f"Processing APPLY alert for '{ipo.name}' "
                f"(Sub: {ipo.subscription_display}, GMP: {gmp_safe})..."
            )
            sent = send_ipo_apply_notification(
                ipo=ipo,
                force=force,
                recipient_list=recipient_list,
                async_send=async_send
            )
            if not target_email:
                ipo.apply_email_sent = True
                ipo.apply_email_sent_at = timezone.now()
                ipo.save(update_fields=['apply_email_sent', 'apply_email_sent_at'])
            self.stdout.write(self.style.SUCCESS(
                f"Successfully triggered alert for '{ipo.name}' (Recipients: {sent})."
            ))
