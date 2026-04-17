"""
Download food photos for each menu item (category-based tags, unique per item id).

  python manage.py attach_menu_images
  python manage.py attach_menu_images --max 5    # first 5 items only (test)
  python manage.py attach_menu_images --skip-existing  # keep items that already have non-placeholder image

Uses loremflickr.com (Flickr CC photos). Needs internet. Falls back to Wikimedia Commons if download fails.
"""
import time
import urllib.error
import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from Base_App.models import Items

# Lorem Flickr tag(s) per category name (must match ItemList.Category_name)
CATEGORY_TAG = {
    'Burgers': 'burger',
    'Pizza': 'pizza',
    'Pasta': 'pasta',
    'Beverages': 'juice,drink',
    'Desserts': 'dessert,cake',
    'Indian Food': 'curry,rice',
    'Chinese Food': 'noodles,chinese',
    'Breakfast': 'breakfast,pancake',
 
}

# Stable Wikimedia thumbs if Lorem Flickr is blocked or slow
FALLBACK_URL = {
    'Burgers': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cheeseburger.jpg/640px-Cheeseburger.jpg',
    'Pizza': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Pizza-300739.jpg/640px-Pizza-300739.jpg',
    'Pasta': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Spaghetti_al_pomodoro.jpg/640px-Spaghetti_al_pomodoro.jpg',
    'Beverages': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Orangejuice.jpg/640px-Orangejuice.jpg',
    'Desserts': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Ice_cream_cone.jpg/640px-Ice_cream_cone.jpg',
    'Indian Food': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Butter_chicken_1.jpg/640px-Butter_chicken_1.jpg',
    'Chinese Food': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Chow_mein_in_takeout_box.jpg/640px-Chow_mein_in_takeout_box.jpg',
    'Breakfast': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Masala_dosa.jpg/640px-Masala_dosa.jpg',
}

USER_AGENT = 'RestoHub/1.0 (educational project; menu image setup)'


def _fetch(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


class Command(BaseCommand):
    help = 'Attach downloaded food images to all menu Items (needs internet).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max',
            type=int,
            default=0,
            help='Only process first N items (0 = all).',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip items whose image is not the tiny seed placeholder (name does not contain seed_placeholder).',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.35,
            help='Seconds between Lorem Flickr requests (be polite to their service).',
        )

    def handle(self, *args, **options):
        qs = Items.objects.select_related('Category').order_by('pk')
        max_n = options['max']
        if max_n > 0:
            qs = qs[:max_n]

        ok = 0
        fail = 0
        skip = 0

        for item in qs:
            cat_name = item.Category.Category_name
            img_name = (item.Image.name or '').lower()

            if options['skip_existing'] and 'seed_placeholder' not in img_name:
                skip += 1
                continue

            tag = CATEGORY_TAG.get(cat_name, 'food')
            primary_url = f'https://loremflickr.com/640/480/{tag}?lock={item.pk}'
            fallback_url = FALLBACK_URL.get(cat_name)

            data = None
            try:
                data = _fetch(primary_url)
                if len(data) < 5000:
                    raise ValueError('response too small')
            except Exception:
                data = None

            if data is None and fallback_url:
                try:
                    data = _fetch(fallback_url, timeout=60)
                except Exception:
                    data = None

            if not data or len(data) < 2000:
                self.stdout.write(self.style.ERROR(f'FAIL #{item.pk} {item.Item_name} ({cat_name})'))
                self.stdout.flush()
                fail += 1
                time.sleep(options['delay'])
                continue

            ext = '.jpg'
            if data[:2] == b'\xff\xd8':
                ext = '.jpg'
            elif len(data) >= 8 and data[:8] == b'\x89PNG\r\n\x1a\n':
                ext = '.png'

            fname = f'item_{item.pk}{ext}'
            item.Image.save(fname, ContentFile(data), save=True)
            ok += 1
            self.stdout.write(self.style.SUCCESS(f'OK #{item.pk} {item.Item_name}'))
            self.stdout.flush()
            time.sleep(options['delay'])

        self.stdout.write(
            self.style.SUCCESS(f'Finished. OK={ok}, failed={fail}, skipped={skip}')
        )
