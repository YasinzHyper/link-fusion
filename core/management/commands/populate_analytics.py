from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import Click
from core.utils import parse_user_agent, get_location_from_ip


class Command(BaseCommand):
    help = 'Populate analytics data (device, browser, OS, location) for existing clicks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if data already exists',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of clicks to process',
        )

    def handle(self, *args, **options):
        force = options['force']
        limit = options['limit']

        # Get clicks that need analytics data
        if force:
            clicks = Click.objects.all()
        else:
            # Only process clicks missing analytics data
            clicks = Click.objects.filter(
                Q(device_type='') | Q(device_type__isnull=True) |
                Q(browser='') | Q(browser__isnull=True) |
                Q(country='') | Q(country__isnull=True)
            )

        if limit:
            clicks = clicks[:limit]

        total_clicks = clicks.count()
        
        if total_clicks == 0:
            self.stdout.write(
                self.style.SUCCESS('No clicks need analytics data population.')
            )
            return

        self.stdout.write(f'Processing {total_clicks} clicks...')

        processed = 0
        updated = 0
        errors = 0

        for click in clicks:
            try:
                # Store original values to check if anything changed
                original_device = click.device_type
                original_browser = click.browser
                original_os = click.operating_system
                original_country = click.country
                original_city = click.city

                # Parse user agent for device/browser/OS info
                if click.user_agent and (force or not click.device_type):
                    ua_data = parse_user_agent(click.user_agent)
                    click.device_type = ua_data['device_type']
                    click.browser = ua_data['browser']
                    click.operating_system = ua_data['operating_system']

                # Get geographic data from IP (only if needed to avoid API limits)
                if click.ip_address and (force or not click.country):
                    # Skip local IPs to avoid unnecessary API calls
                    if click.ip_address not in ['127.0.0.1', '::1']:
                        location_data = get_location_from_ip(click.ip_address)
                        click.country = location_data['country']
                        click.city = location_data['city']
                    else:
                        click.country = 'Local'
                        click.city = 'Local'

                # Check if anything changed
                data_changed = (
                    click.device_type != original_device or
                    click.browser != original_browser or
                    click.operating_system != original_os or
                    click.country != original_country or
                    click.city != original_city
                )

                if data_changed:
                    # Save without triggering the populate_analytics_data again
                    Click.objects.filter(pk=click.pk).update(
                        device_type=click.device_type,
                        browser=click.browser,
                        operating_system=click.operating_system,
                        country=click.country,
                        city=click.city
                    )
                    updated += 1

                processed += 1

                # Progress indicator
                if processed % 10 == 0:
                    self.stdout.write(f'Processed {processed}/{total_clicks} clicks...')

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(f'Error processing click {click.id}: {str(e)}')
                )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Processed: {processed}, Updated: {updated}, Errors: {errors}'
            )
        )

        if errors > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Note: {errors} clicks had errors. This is normal for API rate limits or invalid data.'
                )
            ) 