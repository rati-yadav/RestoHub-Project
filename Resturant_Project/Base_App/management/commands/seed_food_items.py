"""
Sample menu: exactly 6 items per category (8 categories = 48 items).

  python manage.py seed_food_items              # add missing items only
  python manage.py seed_food_items --reset-menu # wipe ALL categories/items, then seed fresh

After seeding, download food photos (internet required):

  python manage.py attach_menu_images

Also merges legacy category named "Burger" into "Burgers" (fixes duplicate filter tabs).
"""
import base64
from collections import Counter

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from Base_App.models import ItemList, Items

_PLACEHOLDER_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAosB9Y8Qr5wAAAAASUVORK5CYII='
)

# Each category must have exactly 6 rows. Category_name ≤15 chars, Item_name ≤40.
MENU = [
    # —— Burgers (6) ——
    ('Burgers', 'Classic Veg Burger', 'Crispy patty, lettuce, tomato, house sauce.', 129),
    ('Burgers', 'Cheese Burst Burger', 'Double cheese, caramelized onions, brioche bun.', 179),
    ('Burgers', 'Paneer Tikka Burger', 'Grilled paneer, mint chutney, pickled onion.', 169),
    ('Burgers', 'Mushroom Swiss Burger', 'Sautéed mushrooms, melted cheese, garlic aioli.', 189),
    ('Burgers', 'Aloo Tikki Burger', 'Spiced potato patty, green chutney, onion.', 139),
    ('Burgers', 'Veggie Crunch Burger', 'Crispy veg patty, coleslaw, thousand island.', 159),
    # —— Pizza (6) ——
    ('Pizza', 'Margherita Pizza', 'Fresh mozzarella, basil, tomato sauce.', 249),
    ('Pizza', 'Farmhouse Pizza', 'Capsicum, onion, tomato, sweet corn, olives.', 299),
    ('Pizza', 'Paneer Tikka Pizza', 'Tandoori paneer, onion, capsicum, mint drizzle.', 349),
    ('Pizza', 'Peppy Paneer Pizza', 'Paneer, red paprika, spicy peri-peri sprinkle.', 329),
    ('Pizza', 'Veggie Supreme Pizza', 'Loaded vegetables, extra cheese, herbs.', 379),
    ('Pizza', 'Corn & Cheese Pizza', 'Golden corn, creamy cheese blend.', 279),
    # —— Pasta (6) ——
    ('Pasta', 'Pink Sauce Pasta', 'Penne in creamy tomato sauce.', 229),
    ('Pasta', 'Arrabbiata Pasta', 'Spicy tomato, garlic, chili flakes.', 219),
    ('Pasta', 'Alfredo Pasta', 'Rich white sauce, parmesan hint, herbs.', 239),
    ('Pasta', 'Pesto Pasta', 'Basil pesto, pine nuts, olive oil.', 259),
    ('Pasta', 'Mac n Cheese Bowl', 'Elbow macaroni, cheddar, baked top.', 199),
    ('Pasta', 'Mushroom Pasta', 'Creamy mushroom sauce, parsley.', 249),
    # —— Beverages (6) ——
    ('Beverages', 'Masala Chai', 'Kadak chai with ginger & cardamom.', 49),
    ('Beverages', 'Cold Coffee', 'Blended coffee, ice, light cream.', 99),
    ('Beverages', 'Fresh Lime Soda', 'Sweet or salted — your choice.', 69),
    ('Beverages', 'Mango Lassi', 'Thick yogurt mango smoothie.', 89),
    ('Beverages', 'Mint Mojito Mocktail', 'Mint, lime, soda — no alcohol.', 119),
    ('Beverages', 'Berry Smoothie', 'Mixed berries, yogurt, honey.', 129),
    # —— Desserts (6) ——
    ('Desserts', 'Chocolate Brownie', 'Warm brownie with vanilla scoop.', 149),
    ('Desserts', 'Gulab Jamun 2pc', 'Soft milk dumplings in rose syrup.', 79),
    ('Desserts', 'Ice Cream Scoop', 'Choice: vanilla, chocolate, strawberry.', 69),
    ('Desserts', 'Choco Lava Cake', 'Molten center, dusted cocoa.', 169),
    ('Desserts', 'Rasmalai', 'Soft chenna in saffron milk.', 99),
    ('Desserts', 'Cheesecake Slice', 'Baked cheesecake, berry compote.', 189),
    # —— Indian Food (6) ——
    ('Indian Food', 'Dal Makhani', 'Slow-cooked black lentils, butter, cream.', 189),
    ('Indian Food', 'Paneer Butter Masala', 'Cottage cheese in rich tomato gravy.', 229),
    ('Indian Food', 'Palak Paneer', 'Spinach gravy with soft paneer cubes.', 219),
    ('Indian Food', 'Chole Bhature', 'Spicy chickpeas with fried bread (2).', 159),
    ('Indian Food', 'Veg Biryani', 'Basmati rice, mixed veg, raita side.', 199),
    ('Indian Food', 'Dal Tadka', 'Yellow lentils, tempered spices.', 129),
    # —— Chinese Food (6) ——
    ('Chinese Food', 'Veg Manchurian', 'Fried balls in Indo-Chinese sauce.', 179),
    ('Chinese Food', 'Hakka Noodles', 'Stir-fried noodles, vegetables.', 159),
    ('Chinese Food', 'Schezwan Fried Rice', 'Spicy rice with veg, schezwan.', 169),
    ('Chinese Food', 'Spring Rolls 6pc', 'Crispy rolls with veg filling.', 129),
    ('Chinese Food', 'Hot & Sour Soup', 'Tofu, vegetables, tangy broth.', 119),
    ('Chinese Food', 'Chilli Paneer Dry', 'Crispy paneer, capsicum, soy glaze.', 199),
    # —— Breakfast (6) ——
    ('Breakfast', 'Masala Dosa', 'Crispy dosa, potato masala, chutney.', 99),
    ('Breakfast', 'Idli Sambar 4pc', 'Soft idlis, sambar, coconut chutney.', 79),
    ('Breakfast', 'Poha', 'Flattened rice, peanuts, lemon.', 69),
    ('Breakfast', 'Paratha Platter', '2 parathas, curd, pickle.', 119),
    ('Breakfast', 'Bread Toast Butter', 'Golden butter toast, jam side.', 59),
    ('Breakfast', 'Upma', 'Semolina, vegetables, mild spice.', 69),
]

_counts = Counter(row[0] for row in MENU)
assert len(_counts) == 8 and all(c == 6 for c in _counts.values()), f'Bad MENU counts: {_counts}'


def _merge_burger_categories_into_burgers(stdout, style):
    """Merge legacy category name 'Burger' into 'Burgers'."""
    for old in list(ItemList.objects.all()):
        name = (old.Category_name or '').strip()
        if name.lower() == 'burger':
            proper, created = ItemList.objects.get_or_create(Category_name='Burgers')
            if old.pk != proper.pk:
                n = Items.objects.filter(Category=old).update(Category=proper)
                if n and stdout:
                    stdout.write(
                        style.SUCCESS(
                            f'Merged {n} items from "{old.Category_name}" into Burgers'
                        )
                    )
                old.delete()
            elif created and stdout:
                stdout.write(style.NOTICE('Using category Burgers'))


class Command(BaseCommand):
    help = 'Menu seed: 6 items per category. Use --reset-menu to replace entire menu.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-menu',
            action='store_true',
            help='Delete ALL categories and items, then seed 48 items (cart entries for those items are removed).',
        )

    def handle(self, *args, **options):
        _merge_burger_categories_into_burgers(self.stdout, self.style)

        if options['reset_menu']:
            self.stdout.write(self.style.WARNING('Removing all menu items and categories...'))
            Items.objects.all().delete()
            ItemList.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Menu cleared.'))

        media_root = settings.MEDIA_ROOT
        (media_root / 'items').mkdir(parents=True, exist_ok=True)

        cats = {}
        for cat_name in dict.fromkeys(row[0] for row in MENU):
            obj, created = ItemList.objects.get_or_create(Category_name=cat_name)
            cats[cat_name] = obj
            if created:
                self.stdout.write(self.style.SUCCESS(f'+ category: {cat_name}'))

        shared_image_name = None
        added = 0
        skipped = 0

        for cat_name, iname, desc, price in MENU:
            cat = cats[cat_name]
            if Items.objects.filter(Category=cat, Item_name=iname).exists():
                skipped += 1
                continue

            item = Items.objects.create(
                Category=cat,
                Item_name=iname,
                description=desc,
                Price=price,
            )
            if shared_image_name is None:
                item.Image.save(
                    'seed_placeholder.png',
                    ContentFile(_PLACEHOLDER_PNG),
                    save=True,
                )
                shared_image_name = item.Image.name
            else:
                item.Image.name = shared_image_name
                item.save(update_fields=['Image'])

            added += 1

        self.stdout.write(
            self.style.SUCCESS(f'Done. Added {added} items, skipped {skipped} (already present).')
        )

        # Warn if orphan categories (e.g. old Pizza duplicate) still have items
        extra = ItemList.objects.exclude(Category_name__in=list(cats.keys()))
        for orphan in extra:
            cnt = Items.objects.filter(Category=orphan).count()
            if cnt:
                self.stdout.write(
                    self.style.WARNING(
                        f'Orphan category "{orphan.Category_name}" still has {cnt} items - '
                        f'remove in admin or run with --reset-menu.'
                    )
                )
