from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
import random

from livestock.models import (
    Farm, Labourer, Livestock, Drug, Feed, HealthRecord, 
    AMURecord, FeedRecord, YieldRecord
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with comprehensive dummy data for testing insights'

    def handle(self, *args, **options):
        self.stdout.write('Starting data seeding...')
        
        # Clear existing data
        self.clear_existing_data()
        
        # Create users and farms
        farms, users = self.create_farms_and_users()
        
        # Create labourers
        labourers = self.create_labourers(users)
        
        # Create drugs and feeds
        drugs = self.create_drugs()
        feeds = self.create_feeds()
        
        # Create livestock
        livestock_list = self.create_livestock(farms)
        
        # Create health records with AMU records
        self.create_health_records(livestock_list, drugs)
        
        # Create feed records
        self.create_feed_records(livestock_list, feeds)
        
        # Create yield records
        self.create_yield_records(livestock_list)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded database with comprehensive test data!')
        )

    def clear_existing_data(self):
        """Clear existing data in reverse dependency order"""
        self.stdout.write('Clearing existing data...')
        AMURecord.objects.all().delete()
        HealthRecord.objects.all().delete()
        FeedRecord.objects.all().delete()
        YieldRecord.objects.all().delete()
        Livestock.objects.all().delete()
        Labourer.objects.all().delete()
        Farm.objects.all().delete()
        Drug.objects.all().delete()
        Feed.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def create_farms_and_users(self):
        """Create farm owners and their farms"""
        self.stdout.write('Creating farms and users...')
        
        farms = []
        users = []
        
        # Create 3 farm owners with different farm types
        farm_data = [
            {
                'username': 'greenpastures_farm',
                'email': 'owner@greenpastures.com',
                'farm_name': 'Green Pastures Dairy Farm',
                'location': 'Nairobi, Kenya'
            },
            {
                'username': 'sunrise_poultry',
                'email': 'owner@sunrisepoultry.com', 
                'farm_name': 'Sunrise Poultry Farm',
                'location': 'Kampala, Uganda'
            },
            {
                'username': 'mountain_cattle',
                'email': 'owner@mountaincattle.com',
                'farm_name': 'Mountain Cattle Ranch',
                'location': 'Arusha, Tanzania'
            }
        ]
        
        for data in farm_data:
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password='testpass123'
            )
            users.append(user)
            
            farm = Farm.objects.create(
                owner=user,
                name=data['farm_name'],
                location=data['location']
            )
            farms.append(farm)
            
        return farms, users

    def create_labourers(self, users):
        """Create labourers for different farms"""
        self.stdout.write('Creating labourers...')
        
        labourers = []
        
        # Create labourers for each farm
        labourer_data = [
            {'username': 'john_worker', 'email': 'john@greenpastures.com', 'farm_index': 0, 'status': 'approved'},
            {'username': 'mary_worker', 'email': 'mary@greenpastures.com', 'farm_index': 0, 'status': 'approved'},
            {'username': 'peter_worker', 'email': 'peter@sunrisepoultry.com', 'farm_index': 1, 'status': 'approved'},
            {'username': 'sarah_worker', 'email': 'sarah@sunrisepoultry.com', 'farm_index': 1, 'status': 'pending'},
            {'username': 'david_worker', 'email': 'david@mountaincattle.com', 'farm_index': 2, 'status': 'approved'},
        ]
        
        farms = Farm.objects.all()
        
        for data in labourer_data:
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password='testpass123'
            )
            
            labourer = Labourer.objects.create(
                user=user,
                farm=farms[data['farm_index']],
                status=data['status']
            )
            labourers.append(labourer)
            
        return labourers

    def create_drugs(self):
        """Create comprehensive drug database"""
        self.stdout.write('Creating drugs...')
        
        drugs = []
        drug_data = [
            {
                'name': 'Oxytetracycline 20%',
                'active_ingredient': 'Oxytetracycline',
                'species_target': 'Cattle',
                'recommended_dosage_min': 5.0,
                'recommended_dosage_max': 10.0,
                'unit': 'ml',
                'notes': 'Broad spectrum antibiotic for bacterial infections'
            },
            {
                'name': 'Penicillin G',
                'active_ingredient': 'Benzylpenicillin',
                'species_target': 'Cattle',
                'recommended_dosage_min': 2.0,
                'recommended_dosage_max': 5.0,
                'unit': 'ml',
                'notes': 'For gram-positive bacterial infections'
            },
            {
                'name': 'Amoxicillin 15%',
                'active_ingredient': 'Amoxicillin',
                'species_target': 'Poultry',
                'recommended_dosage_min': 1.0,
                'recommended_dosage_max': 3.0,
                'unit': 'ml',
                'notes': 'Beta-lactam antibiotic for respiratory infections'
            },
            {
                'name': 'Enrofloxacin 10%',
                'active_ingredient': 'Enrofloxacin',
                'species_target': 'Poultry',
                'recommended_dosage_min': 0.5,
                'recommended_dosage_max': 2.0,
                'unit': 'ml',
                'notes': 'Fluoroquinolone for severe bacterial infections'
            },
            {
                'name': 'Ivermectin 1%',
                'active_ingredient': 'Ivermectin',
                'species_target': 'Cattle',
                'recommended_dosage_min': 1.0,
                'recommended_dosage_max': 2.0,
                'unit': 'ml',
                'notes': 'Antiparasitic for internal and external parasites'
            },
            {
                'name': 'Meloxicam',
                'active_ingredient': 'Meloxicam',
                'species_target': 'Cattle',
                'recommended_dosage_min': 0.5,
                'recommended_dosage_max': 1.0,
                'unit': 'ml',
                'notes': 'NSAID for pain relief and inflammation'
            }
        ]
        
        for data in drug_data:
            drug = Drug.objects.create(**data)
            drugs.append(drug)
            
        return drugs

    def create_feeds(self):
        """Create feed catalog"""
        self.stdout.write('Creating feeds...')
        
        feeds = []
        feed_data = [
            {'name': 'Dairy Meal', 'cost_per_kg': 45.0, 'notes': 'High protein feed for dairy cattle'},
            {'name': 'Maize Bran', 'cost_per_kg': 25.0, 'notes': 'Energy-rich feed supplement'},
            {'name': 'Layers Mash', 'cost_per_kg': 35.0, 'notes': 'Complete feed for laying hens'},
            {'name': 'Broiler Starter', 'cost_per_kg': 40.0, 'notes': 'High protein feed for young broilers'},
            {'name': 'Hay', 'cost_per_kg': 15.0, 'notes': 'Roughage for cattle'},
            {'name': 'Silage', 'cost_per_kg': 20.0, 'notes': 'Fermented feed for cattle'},
            {'name': 'Wheat Bran', 'cost_per_kg': 30.0, 'notes': 'Fiber-rich feed supplement'},
            {'name': 'Soybean Meal', 'cost_per_kg': 55.0, 'notes': 'High protein supplement'}
        ]
        
        for data in feed_data:
            feed = Feed.objects.create(**data)
            feeds.append(feed)
            
        return feeds

    def create_livestock(self, farms):
        """Create diverse livestock across farms"""
        self.stdout.write('Creating livestock...')
        
        livestock_list = []
        
        # Green Pastures Dairy Farm - Dairy cattle
        dairy_cattle = [
            {'tag_id': 'COW-001', 'species': 'Cattle', 'breed': 'Holstein Friesian', 'gender': 'F', 'date_of_birth': '2020-03-15', 'current_weight_kg': 450.0},
            {'tag_id': 'COW-002', 'species': 'Cattle', 'breed': 'Holstein Friesian', 'gender': 'F', 'date_of_birth': '2019-07-22', 'current_weight_kg': 480.0},
            {'tag_id': 'COW-003', 'species': 'Cattle', 'breed': 'Jersey', 'gender': 'F', 'date_of_birth': '2021-01-10', 'current_weight_kg': 380.0},
            {'tag_id': 'COW-004', 'species': 'Cattle', 'breed': 'Holstein Friesian', 'gender': 'F', 'date_of_birth': '2018-11-05', 'current_weight_kg': 520.0},
            {'tag_id': 'COW-005', 'species': 'Cattle', 'breed': 'Holstein Friesian', 'gender': 'F', 'date_of_birth': '2020-09-18', 'current_weight_kg': 460.0},
        ]
        
        # Sunrise Poultry Farm - Chickens
        poultry = [
            {'tag_id': 'CHK-001', 'species': 'Poultry', 'breed': 'Rhode Island Red', 'gender': 'F', 'date_of_birth': '2023-06-01', 'current_weight_kg': 2.5},
            {'tag_id': 'CHK-002', 'species': 'Poultry', 'breed': 'Rhode Island Red', 'gender': 'F', 'date_of_birth': '2023-06-15', 'current_weight_kg': 2.3},
            {'tag_id': 'CHK-003', 'species': 'Poultry', 'breed': 'Leghorn', 'gender': 'F', 'date_of_birth': '2023-05-20', 'current_weight_kg': 2.1},
            {'tag_id': 'CHK-004', 'species': 'Poultry', 'breed': 'Rhode Island Red', 'gender': 'F', 'date_of_birth': '2023-07-10', 'current_weight_kg': 2.2},
            {'tag_id': 'CHK-005', 'species': 'Poultry', 'breed': 'Leghorn', 'gender': 'F', 'date_of_birth': '2023-05-05', 'current_weight_kg': 2.0},
        ]
        
        # Mountain Cattle Ranch - Beef cattle
        beef_cattle = [
            {'tag_id': 'BEEF-001', 'species': 'Cattle', 'breed': 'Angus', 'gender': 'M', 'date_of_birth': '2021-04-12', 'current_weight_kg': 600.0},
            {'tag_id': 'BEEF-002', 'species': 'Cattle', 'breed': 'Hereford', 'gender': 'F', 'date_of_birth': '2020-08-30', 'current_weight_kg': 550.0},
            {'tag_id': 'BEEF-003', 'species': 'Cattle', 'breed': 'Angus', 'gender': 'M', 'date_of_birth': '2022-02-14', 'current_weight_kg': 580.0},
            {'tag_id': 'BEEF-004', 'species': 'Cattle', 'breed': 'Hereford', 'gender': 'F', 'date_of_birth': '2021-12-03', 'current_weight_kg': 520.0},
        ]
        
        # Create livestock for each farm
        for i, farm in enumerate(farms):
            if i == 0:  # Green Pastures - Dairy
                for data in dairy_cattle:
                    livestock = Livestock.objects.create(
                        farm=farm,
                        **data,
                        health_status='healthy'
                    )
                    livestock_list.append(livestock)
            elif i == 1:  # Sunrise Poultry
                for data in poultry:
                    livestock = Livestock.objects.create(
                        farm=farm,
                        **data,
                        health_status='healthy'
                    )
                    livestock_list.append(livestock)
            else:  # Mountain Cattle - Beef
                for data in beef_cattle:
                    livestock = Livestock.objects.create(
                        farm=farm,
                        **data,
                        health_status='healthy'
                    )
                    livestock_list.append(livestock)
                    
        return livestock_list

    def create_health_records(self, livestock_list, drugs):
        """Create comprehensive health records with AMU data"""
        self.stdout.write('Creating health records and AMU records...')
        
        # Create health records over the past 12 months
        start_date = datetime.now() - timedelta(days=365)
        
        for livestock in livestock_list:
            # Create 2-5 health records per animal over the year
            num_records = random.randint(2, 5)
            
            for _ in range(num_records):
                # Random date within the past year
                days_ago = random.randint(1, 365)
                event_date = datetime.now() - timedelta(days=days_ago)
                
                # Different event types with realistic scenarios
                event_types = ['vaccination', 'sickness', 'check-up', 'treatment']
                event_type = random.choice(event_types)
                
                # Create realistic diagnoses and outcomes
                if event_type == 'sickness':
                    diagnoses = ['Mastitis', 'Respiratory infection', 'Digestive upset', 'Lameness', 'Fever']
                    outcomes = ['Recovered', 'Under treatment', 'Recovering']
                elif event_type == 'treatment':
                    diagnoses = ['Bacterial infection', 'Parasitic infestation', 'Injury', 'Inflammation']
                    outcomes = ['Completed', 'Ongoing', 'Recovered']
                elif event_type == 'vaccination':
                    diagnoses = ['Routine vaccination', 'Booster vaccination', 'Annual vaccination']
                    outcomes = ['Successful', 'No reactions']
                else:  # check-up
                    diagnoses = ['Routine health check', 'Weight monitoring', 'General examination']
                    outcomes = ['Healthy', 'Good condition', 'Normal']
                
                diagnosis = random.choice(diagnoses)
                outcome = random.choice(outcomes)
                
                health_record = HealthRecord.objects.create(
                    livestock=livestock,
                    event_type=event_type,
                    event_date=event_date.date(),
                    notes=f"Health event for {livestock.tag_id}",
                    diagnosis=diagnosis,
                    treatment_outcome=outcome
                )
                
                # Create AMU records for treatment and sickness events
                if event_type in ['treatment', 'sickness'] and random.random() > 0.3:
                    # Select appropriate drug based on species
                    if livestock.species == 'Cattle':
                        available_drugs = [d for d in drugs if d.species_target == 'Cattle']
                    else:  # Poultry
                        available_drugs = [d for d in drugs if d.species_target == 'Poultry']
                    
                    if available_drugs:
                        drug = random.choice(available_drugs)
                        
                        # Calculate dosage based on weight and drug recommendations
                        if livestock.current_weight_kg:
                            if drug.recommended_dosage_min and drug.recommended_dosage_max:
                                dosage_min = float(drug.recommended_dosage_min)
                                dosage_max = float(drug.recommended_dosage_max)
                                dosage = random.uniform(dosage_min, dosage_max)
                                dosage_str = f"{dosage:.1f} {drug.unit}"
                            else:
                                dosage_str = f"{random.uniform(1, 5):.1f} {drug.unit}"
                        else:
                            dosage_str = f"{random.uniform(1, 3):.1f} {drug.unit}"
                        
                        # Withdrawal period based on drug type
                        withdrawal_periods = {
                            'Oxytetracycline': 7,
                            'Penicillin G': 3,
                            'Amoxicillin': 5,
                            'Enrofloxacin': 10,
                            'Ivermectin': 14,
                            'Meloxicam': 2
                        }
                        
                        withdrawal = withdrawal_periods.get(drug.active_ingredient, 7)
                        
                        AMURecord.objects.create(
                            health_record=health_record,
                            drug=drug,
                            dosage=dosage_str,
                            withdrawal_period=withdrawal
                        )

    def create_feed_records(self, livestock_list, feeds):
        """Create feed consumption records"""
        self.stdout.write('Creating feed records...')
        
        # Create feed records for the past 6 months
        start_date = datetime.now() - timedelta(days=180)
        
        for livestock in livestock_list:
            # Create 15-30 feed records per animal over 6 months
            num_records = random.randint(15, 30)
            
            for _ in range(num_records):
                # Random date within the past 6 months
                days_ago = random.randint(1, 180)
                feed_date = datetime.now() - timedelta(days=days_ago)
                
                # Select appropriate feed based on species
                if livestock.species == 'Cattle':
                    available_feeds = [f for f in feeds if f.name in ['Dairy Meal', 'Maize Bran', 'Hay', 'Silage', 'Wheat Bran', 'Soybean Meal']]
                else:  # Poultry
                    available_feeds = [f for f in feeds if f.name in ['Layers Mash', 'Broiler Starter', 'Maize Bran', 'Wheat Bran', 'Soybean Meal']]
                
                if available_feeds:
                    feed = random.choice(available_feeds)
                    
                    # Realistic quantities based on species
                    if livestock.species == 'Cattle':
                        quantity = random.uniform(5.0, 15.0)  # kg per day
                    else:  # Poultry
                        quantity = random.uniform(0.1, 0.3)  # kg per day
                    
                    # Use feed cost or random price
                    if feed.cost_per_kg:
                        price_per_kg = float(feed.cost_per_kg) + random.uniform(-5, 5)
                    else:
                        price_per_kg = random.uniform(20, 60)
                    
                    FeedRecord.objects.create(
                        livestock=livestock,
                        feed_type=feed.name,
                        feed=feed,
                        quantity_kg=Decimal(str(round(quantity, 2))),
                        price_per_kg=Decimal(str(round(price_per_kg, 2))),
                        date=feed_date.date()
                    )

    def create_yield_records(self, livestock_list):
        """Create production yield records"""
        self.stdout.write('Creating yield records...')
        
        # Create yield records for the past 6 months
        start_date = datetime.now() - timedelta(days=180)
        
        for livestock in livestock_list:
            # Create 60-120 yield records per animal over 6 months (daily production)
            num_records = random.randint(60, 120)
            
            for _ in range(num_records):
                # Random date within the past 6 months
                days_ago = random.randint(1, 180)
                yield_date = datetime.now() - timedelta(days=days_ago)
                
                # Different yield types based on species
                if livestock.species == 'Cattle':
                    yield_type = 'Milk'
                    # Realistic milk production (liters per day)
                    if livestock.breed == 'Holstein Friesian':
                        quantity = random.uniform(20, 35)
                    elif livestock.breed == 'Jersey':
                        quantity = random.uniform(15, 25)
                    else:
                        quantity = random.uniform(10, 20)
                    unit = 'liters'
                else:  # Poultry
                    yield_type = 'Eggs'
                    # Realistic egg production (eggs per day)
                    quantity = random.uniform(0, 1)  # Not all hens lay daily
                    unit = 'units'
                
                if quantity > 0:  # Only record if there's actual production
                    YieldRecord.objects.create(
                        livestock=livestock,
                        yield_type=yield_type,
                        quantity=Decimal(str(round(quantity, 2))),
                        unit=unit,
                        date=yield_date.date()
                    )
