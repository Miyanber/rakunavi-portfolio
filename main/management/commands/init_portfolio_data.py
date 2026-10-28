"""
Management command to initialize mock/sample portfolio data.
Creates fictional spots (Building A, Room 101, etc.), exhibitions, and event schedules.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import time, timedelta

from config.models import FestivalDate, Permission, Slogan
from main.models import (
    Spot,
    Floor,
    Exhibition,
    ExhibitionCategory,
    ExhibitionTag,
    Attraction,
    CongestionDegree,
    Performance,
)

class Command(BaseCommand):
    help = "Populate database with fictional campus spots and exhibition data for portfolio demonstration."

    def handle(self, *args, **options):
        self.stdout.write("Initializing portfolio sample data...")

        # 1. Permission flags (Enable home and features for demo)
        perm, _ = Permission.objects.get_or_create(id=1)
        perm.display_home = True
        perm.display_introduction = True
        perm.save()

        # 2. Slogan
        now = timezone.now()
        Slogan.objects.get_or_create(
            year=now.year,
            defaults={
                "main": "Create the Future, Connect Together",
                "sub": "Campus Festival Portfolio Edition",
            }
        )

        # 3. Festival Dates
        t_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        t_end = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        date1, _ = FestivalDate.objects.get_or_create(
            day=1,
            defaults={
                "begin_at": t_start,
                "end_at": t_end,
            }
        )
        date2, _ = FestivalDate.objects.get_or_create(
            day=2,
            defaults={
                "begin_at": t_start + timedelta(days=1),
                "end_at": t_end + timedelta(days=1),
            }
        )

        # 4. Tags
        tag_art, _ = ExhibitionTag.objects.get_or_create(name="Art & Craft")
        tag_tech, _ = ExhibitionTag.objects.get_or_create(name="Tech & Science")
        tag_game, _ = ExhibitionTag.objects.get_or_create(name="Game & Cafe")
        tag_music, _ = ExhibitionTag.objects.get_or_create(name="Music & Stage")

        # 5. Fictional Campus Spots
        spots_data = [
            {"name": "Building A - Room 101", "floor": Floor.FIRST, "start_x": 12.0, "start_y": 18.0, "width": 16.0, "height": 26.0, "is_stage": False},
            {"name": "Building A - Room 102", "floor": Floor.FIRST, "start_x": 32.0, "start_y": 18.0, "width": 16.0, "height": 26.0, "is_stage": False},
            {"name": "Building A - Room 103", "floor": Floor.FIRST, "start_x": 52.0, "start_y": 18.0, "width": 16.0, "height": 26.0, "is_stage": False},
            {"name": "Building B - Room 201", "floor": Floor.SECOND, "start_x": 15.0, "start_y": 20.0, "width": 18.0, "height": 28.0, "is_stage": False},
            {"name": "Building B - Room 202", "floor": Floor.SECOND, "start_x": 38.0, "start_y": 20.0, "width": 18.0, "height": 28.0, "is_stage": False},
            {"name": "Building B - Science Lab", "floor": Floor.SECOND, "start_x": 62.0, "start_y": 20.0, "width": 22.0, "height": 28.0, "is_stage": False},
            {"name": "Central Plaza - Main Stage", "floor": Floor.YOUTH_SQUARE, "start_x": 35.0, "start_y": 25.0, "width": 30.0, "height": 30.0, "is_stage": True},
            {"name": "Central Plaza - Food Booth A", "floor": Floor.YOUTH_SQUARE, "start_x": 12.0, "start_y": 30.0, "width": 18.0, "height": 24.0, "is_stage": False},
            {"name": "Central Plaza - Food Booth B", "floor": Floor.YOUTH_SQUARE, "start_x": 70.0, "start_y": 30.0, "width": 18.0, "height": 24.0, "is_stage": False},
        ]

        created_spots = {}
        for s in spots_data:
            spot, _ = Spot.objects.get_or_create(
                name=s["name"],
                defaults={
                    "floor": s["floor"],
                    "start_x": s["start_x"],
                    "start_y": s["start_y"],
                    "width": s["width"],
                    "height": s["height"],
                    "is_stage": s["is_stage"],
                }
            )
            created_spots[s["name"]] = spot

        # 6. Sample Exhibitions
        exhibitions_data = [
            {
                "title": "Interactive AI & Robotics Showcase",
                "category": ExhibitionCategory.CLUB,
                "overview": "Student-developed AI chat systems and robot demo.",
                "explanation": "<p>A showcase of student-developed AI chat systems, autonomous robots, and micro-drone navigation demo.</p>",
                "spot": created_spots["Building A - Room 101"],
                "tags": [tag_tech],
                "congestion": CongestionDegree.NORMAL,
                "wait_time": 10,
            },
            {
                "title": "Virtual Campus VR Experience",
                "category": ExhibitionCategory.CLASS,
                "overview": "Explore 3D Metaverse campus model with VR goggles.",
                "explanation": "<p>Explore a 3D Metaverse model of our school campus built with Three.js and WebGL. Wear VR goggles to take the tour!</p>",
                "spot": created_spots["Building A - Room 102"],
                "tags": [tag_tech, tag_game],
                "congestion": CongestionDegree.BUSY,
                "wait_time": 25,
            },
            {
                "title": "Student Art & Digital Media Gallery",
                "category": ExhibitionCategory.CLUB,
                "overview": "Original digital illustrations and oil paintings.",
                "explanation": "<p>Original digital illustrations, 3D animations, and oil paintings created by passionate student creators.</p>",
                "spot": created_spots["Building A - Room 103"],
                "tags": [tag_art],
                "congestion": CongestionDegree.EMPTY,
                "wait_time": 0,
            },
            {
                "title": "Science Odyssey & Chemical Illusions",
                "category": ExhibitionCategory.CLUB,
                "overview": "Exciting live chemistry experiments workshop.",
                "explanation": "<p>Exciting live chemistry experiments, fluorescent liquid demonstrations, and crystal growing workshops.</p>",
                "spot": created_spots["Building B - Science Lab"],
                "tags": [tag_tech],
                "congestion": CongestionDegree.NORMAL,
                "wait_time": 5,
            },
        ]

        for ed in exhibitions_data:
            exh, is_new = Exhibition.objects.get_or_create(
                title=ed["title"],
                defaults={
                    "category": ed["category"],
                    "overview": ed["overview"],
                    "explanation": ed["explanation"],
                }
            )
            exh.spots.add(ed["spot"])
            for t in ed["tags"]:
                exh.tags.add(t)

            # Add congestion record
            Attraction.objects.get_or_create(
                exhibition=exh,
                congestion_level=ed["congestion"],
                defaults={
                    "wait_time": ed["wait_time"],
                }
            )

        # 7. Sample Stage Performance
        stage_spot = created_spots["Central Plaza - Main Stage"]
        Performance.objects.get_or_create(
            name="School Music Band",
            defaults={
                "genre": "Pop / Rock",
                "message": "<p>Live acoustic guitar and pop-rock performances by student bands at the open outdoor stage.</p>",
                "spot": stage_spot,
                "date": date1,
                "begin_at": time(11, 0),
                "end_at": time(12, 30),
            }
        )

        self.stdout.write(self.style.SUCCESS("Successfully populated portfolio sample spots and exhibitions!"))
