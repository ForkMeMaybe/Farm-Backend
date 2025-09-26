from django.core.management.base import BaseCommand
from livestock.models import (
    Farm, Labourer, Livestock, Drug, Feed, HealthRecord, 
    AMURecord, FeedRecord, YieldRecord
)
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Verify the seeded data and show statistics'

    def handle(self, *args, **options):
        self.stdout.write('=== DATABASE SEEDING VERIFICATION ===\n')
        
        # Count all entities
        users_count = User.objects.count()
        farms_count = Farm.objects.count()
        labourers_count = Labourer.objects.count()
        livestock_count = Livestock.objects.count()
        drugs_count = Drug.objects.count()
        feeds_count = Feed.objects.count()
        health_records_count = HealthRecord.objects.count()
        amu_records_count = AMURecord.objects.count()
        feed_records_count = FeedRecord.objects.count()
        yield_records_count = YieldRecord.objects.count()
        
        self.stdout.write(f'👥 Users: {users_count}')
        self.stdout.write(f'🏡 Farms: {farms_count}')
        self.stdout.write(f'👷 Labourers: {labourers_count}')
        self.stdout.write(f'🐄 Livestock: {livestock_count}')
        self.stdout.write(f'💊 Drugs: {drugs_count}')
        self.stdout.write(f'🌾 Feeds: {feeds_count}')
        self.stdout.write(f'🏥 Health Records: {health_records_count}')
        self.stdout.write(f'💉 AMU Records: {amu_records_count}')
        self.stdout.write(f'🍽️ Feed Records: {feed_records_count}')
        self.stdout.write(f'📈 Yield Records: {yield_records_count}\n')
        
        # Show farm details
        self.stdout.write('=== FARM DETAILS ===')
        for farm in Farm.objects.all():
            livestock_in_farm = Livestock.objects.filter(farm=farm).count()
            self.stdout.write(f'🏡 {farm.name} ({farm.location})')
            self.stdout.write(f'   Owner: {farm.owner.username}')
            self.stdout.write(f'   Livestock: {livestock_in_farm} animals')
            self.stdout.write(f'   Labourers: {Labourer.objects.filter(farm=farm).count()}')
            self.stdout.write('')
        
        # Show livestock by species
        self.stdout.write('=== LIVESTOCK BY SPECIES ===')
        species_counts = {}
        for livestock in Livestock.objects.all():
            species = livestock.species
            species_counts[species] = species_counts.get(species, 0) + 1
        
        for species, count in species_counts.items():
            self.stdout.write(f'🐄 {species}: {count} animals')
        
        # Show AMU insights potential
        self.stdout.write('\n=== AMU INSIGHTS POTENTIAL ===')
        for farm in Farm.objects.all():
            farm_livestock = Livestock.objects.filter(farm=farm)
            total_amu_records = 0
            for livestock in farm_livestock:
                health_records = HealthRecord.objects.filter(livestock=livestock)
                for hr in health_records:
                    total_amu_records += AMURecord.objects.filter(health_record=hr).count()
            
            self.stdout.write(f'🏡 {farm.name}: {total_amu_records} AMU records for insights')
        
        # Show feed and yield data
        self.stdout.write('\n=== FEED & YIELD DATA ===')
        total_feed_cost = sum(float(fr.quantity_kg * (fr.price_per_kg or 0)) for fr in FeedRecord.objects.all())
        total_yield = sum(float(yr.quantity) for yr in YieldRecord.objects.all())
        
        self.stdout.write(f'💰 Total Feed Cost: ${total_feed_cost:.2f}')
        self.stdout.write(f'📈 Total Yield: {total_yield:.2f} units')
        
        # Show recent activity
        self.stdout.write('\n=== RECENT ACTIVITY (Last 30 days) ===')
        from datetime import datetime, timedelta
        recent_date = datetime.now() - timedelta(days=30)
        
        recent_health = HealthRecord.objects.filter(event_date__gte=recent_date.date()).count()
        recent_feed = FeedRecord.objects.filter(date__gte=recent_date.date()).count()
        recent_yield = YieldRecord.objects.filter(date__gte=recent_date.date()).count()
        
        self.stdout.write(f'🏥 Recent Health Records: {recent_health}')
        self.stdout.write(f'🍽️ Recent Feed Records: {recent_feed}')
        self.stdout.write(f'📈 Recent Yield Records: {recent_yield}')
        
        self.stdout.write('\n✅ Database verification complete!')
        self.stdout.write('🎯 The data is ready for testing insights and analytics!')
