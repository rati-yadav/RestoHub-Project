from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class ItemList(models.Model):
    Category_name = models.CharField(max_length=15)

    def __str__(self):
        return self.Category_name
    

class Items(models.Model):
    Item_name = models.CharField(max_length=40)
    description = models.TextField(blank=False)
    Price = models.IntegerField()
    Category = models.ForeignKey(ItemList, related_name='Name', on_delete=models.CASCADE)
    Image = models.ImageField(upload_to='items/')

    def __str__(self):
        return self.Item_name

class AboutUs(models.Model):
    Description = models.TextField(blank=False)

class Feedback(models.Model):
    User_name = models.CharField(max_length=15)
    Description = models.TextField(blank=False)
    Rating = models.IntegerField()
    Image = models.ImageField(upload_to='feedback/', blank=True)

    def __str__(self):
        return self.User_name
    

class BookTable(models.Model):
    Name = models.CharField(max_length=15)
    Phone_number = models.IntegerField()
    Email = models.EmailField()
    Total_person = models.IntegerField()
    Booking_date = models.DateField()
    Booking_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return self.Name
    

class Cart(models.Model):
    user = models.ForeignKey(User, related_name='cart', on_delete=models.CASCADE)
    item = models.ForeignKey(Items, related_name='cart_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user.username} - {self.item.Item_name}"


class Order(models.Model):
    PAYMENT_COD = 'cod'
    PAYMENT_RAZORPAY = 'razorpay'
    PAYMENT_CHOICES = [
        (PAYMENT_COD, 'Cash on delivery'),
        (PAYMENT_RAZORPAY, 'Online (UPI / Card)'),
    ]

    TRACKING_RECEIVED = 'received'
    TRACKING_QUEUE = 'queue'
    TRACKING_PREPARING = 'preparing'
    TRACKING_READY = 'ready'
    TRACKING_SERVING = 'serving'
    TRACKING_DELIVERED = 'delivered'
    TRACKING_CHOICES = [
        (TRACKING_RECEIVED, 'Order received'),
        (TRACKING_QUEUE, 'Waiting list'),
        (TRACKING_PREPARING, 'Preparing in kitchen'),
        (TRACKING_READY, 'Ready — assign table'),
        (TRACKING_SERVING, 'Chef bringing to table'),
        (TRACKING_DELIVERED, 'Delivered / completed'),
    ]

    TRACKING_PIPELINE = [
        TRACKING_RECEIVED,
        TRACKING_QUEUE,
        TRACKING_PREPARING,
        TRACKING_READY,
        TRACKING_SERVING,
        TRACKING_DELIVERED,
    ]

    FULFILL_DINE_IN = 'dine_in'
    FULFILL_DELIVERY = 'delivery'
    FULFILLMENT_CHOICES = [
        (FULFILL_DINE_IN, 'Dine-in / pre-order at table'),
        (FULFILL_DELIVERY, 'Home delivery'),
    ]

    user = models.ForeignKey(User, related_name='orders', on_delete=models.CASCADE)
    total_amount = models.PositiveIntegerField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    fulfillment_type = models.CharField(
        max_length=20,
        choices=FULFILLMENT_CHOICES,
        default=FULFILL_DINE_IN,
    )
    status = models.CharField(max_length=30, default='placed')
    tracking_status = models.CharField(
        max_length=20,
        choices=TRACKING_CHOICES,
        default=TRACKING_RECEIVED,
    )
    table_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='Set when food is ready (e.g. 4, A2). Shown to customer on track page.',
    )
    razorpay_order_id = models.CharField(max_length=120, blank=True)
    razorpay_payment_id = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.pk} — {self.user.username} — ₹{self.total_amount}"

    def tracking_step_index(self):
        try:
            return self.TRACKING_PIPELINE.index(self.tracking_status)
        except ValueError:
            return 0

    def tracking_customer_message(self):
        """Headline + detail for the customer order track page (English)."""
        t = self.tracking_status
        table = (self.table_number or '').strip()

        if self.fulfillment_type == self.FULFILL_DELIVERY:
            delivery_map = {
                self.TRACKING_RECEIVED: (
                    'We have received your order',
                    'The kitchen will prepare it for delivery.',
                ),
                self.TRACKING_QUEUE: (
                    'Your order is in the queue',
                    'It will be prepared shortly.',
                ),
                self.TRACKING_PREPARING: (
                    'Your food is being prepared',
                    'We are getting your delivery order ready.',
                ),
                self.TRACKING_READY: (
                    'Ready for dispatch',
                    'Your order is packed and will be handed to delivery soon.',
                ),
                self.TRACKING_SERVING: (
                    'Out for delivery',
                    'Your order is on the way to your address.',
                ),
                self.TRACKING_DELIVERED: (
                    'Delivered',
                    'Enjoy your meal. Thank you for ordering!',
                ),
            }
            return delivery_map.get(t, delivery_map[self.TRACKING_RECEIVED])

        messages_map = {
            self.TRACKING_RECEIVED: (
                'We have received your order',
                'The kitchen will start on it shortly.',
            ),
            self.TRACKING_QUEUE: (
                'Your order is in the queue',
                'It will move to the kitchen soon.',
            ),
            self.TRACKING_PREPARING: (
                'Your food is being prepared',
                'Our chefs are cooking your order right now.',
            ),
            self.TRACKING_READY: (
                'Your order is ready',
                f'Please head to table {table}.' if table else 'Your table number will appear here when assigned.',
            ),
            self.TRACKING_SERVING: (
                'On the way to your table',
                f'A team member is bringing your food to table {table}.' if table else 'A team member is bringing your order to you.',
            ),
            self.TRACKING_DELIVERED: (
                'Enjoy your meal',
                'Thank you for dining with us.',
            ),
        }
        return messages_map.get(t, messages_map[self.TRACKING_RECEIVED])


class OrderLine(models.Model):
    order = models.ForeignKey(Order, related_name='lines', on_delete=models.CASCADE)
    item = models.ForeignKey(Items, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_lines')
    item_name = models.CharField(max_length=40)
    quantity = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField()
    line_total = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.item_name} x{self.quantity}"
