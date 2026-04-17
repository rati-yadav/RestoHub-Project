from django.conf import settings
from django.db import models


class AboutUs(models.Model):
    Description = models.TextField()

    def __str__(self):
        return f'AboutUs #{self.pk}'


class ItemList(models.Model):
    Category_name = models.CharField(max_length=15)

    def __str__(self):
        return self.Category_name


class Items(models.Model):
    Item_name = models.CharField(max_length=40)
    description = models.TextField()
    Price = models.IntegerField()
    Image = models.ImageField(upload_to='items/')
    Category = models.ForeignKey(
        ItemList,
        on_delete=models.CASCADE,
        related_name='Name',
    )

    def __str__(self):
        return self.Item_name


class Feedback(models.Model):
    User_name = models.CharField(max_length=15)
    Description = models.TextField()
    Rating = models.IntegerField()
    Image = models.ImageField(blank=True, upload_to='feedback/')

    def __str__(self):
        return f'{self.User_name} ({self.Rating})'


class BookTable(models.Model):
    Name = models.CharField(max_length=15)
    Phone_number = models.IntegerField()
    Email = models.EmailField(max_length=254)
    Total_person = models.IntegerField()
    Booking_date = models.DateField()
    Booking_time = models.TimeField(blank=True, null=True)

    def __str__(self):
        return f'{self.Name} — {self.Booking_date}'


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
    )
    item = models.ForeignKey(
        Items,
        on_delete=models.CASCADE,
        related_name='cart_items',
    )
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.user_id} × {self.item_id}'


class Order(models.Model):
    PAYMENT_COD = 'cod'
    PAYMENT_RAZORPAY = 'razorpay'
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_COD, 'Cash on delivery'),
        (PAYMENT_RAZORPAY, 'Online (UPI / Card)'),
    ]

    FULFILL_DINE_IN = 'dine_in'
    FULFILL_DELIVERY = 'delivery'
    FULFILLMENT_CHOICES = [
        (FULFILL_DINE_IN, 'Dine-in / pre-order at table'),
        (FULFILL_DELIVERY, 'Home delivery'),
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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    total_amount = models.PositiveIntegerField()
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
    )
    status = models.CharField(max_length=30, default='placed')
    razorpay_order_id = models.CharField(max_length=120, blank=True)
    razorpay_payment_id = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    table_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='Set when food is ready (e.g. 4, A2). Shown to customer on track page.',
    )
    tracking_status = models.CharField(
        max_length=20,
        choices=TRACKING_CHOICES,
        default=TRACKING_RECEIVED,
    )
    tracking_updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Latest status/assignment update timestamp shown on tracking page.',
    )
    fulfillment_type = models.CharField(
        max_length=20,
        choices=FULFILLMENT_CHOICES,
        default=FULFILL_DINE_IN,
    )

    class Meta:
        ordering = ['-created_at']

    _TRACKING_STEP_ORDER = (
        TRACKING_RECEIVED,
        TRACKING_QUEUE,
        TRACKING_PREPARING,
        TRACKING_READY,
        TRACKING_SERVING,
        TRACKING_DELIVERED,
    )

    def tracking_step_index(self):
        try:
            return self._TRACKING_STEP_ORDER.index(self.tracking_status)
        except ValueError:
            return 0

    def tracking_customer_message(self):
        """Short title + detail for track page header (dine-in vs delivery wording)."""
        s = self.tracking_status
        if self.fulfillment_type == self.FULFILL_DELIVERY:
            messages = {
                self.TRACKING_RECEIVED: ('Order received', 'We have your delivery order and will prepare it soon.'),
                self.TRACKING_QUEUE: ('In the queue', 'Your order is waiting for the kitchen.'),
                self.TRACKING_PREPARING: ('Being cooked', 'Your food is being prepared.'),
                self.TRACKING_READY: ('Packed', 'Your order is packed and ready to go out for delivery.'),
                self.TRACKING_SERVING: ('On the way', 'Your order is on the way to your address.'),
                self.TRACKING_DELIVERED: ('Delivered', 'Order completed. Enjoy your meal!'),
            }
        else:
            messages = {
                self.TRACKING_RECEIVED: ('Order received', 'We have your order and will send it to the kitchen.'),
                self.TRACKING_QUEUE: ('In the queue', 'Waiting for the kitchen to start your order.'),
                self.TRACKING_PREPARING: ('Preparing', 'Your food is being prepared in the kitchen.'),
                self.TRACKING_READY: ('Ready', 'Food is ready. Please check your table number when shown.'),
                self.TRACKING_SERVING: ('Coming to you', 'Staff is bringing your order to the table.'),
                self.TRACKING_DELIVERED: ('Completed', 'Thank you — enjoy your meal!'),
            }
        return messages.get(s, ('Status update', self.get_tracking_status_display()))

    def __str__(self):
        return f'Order #{self.pk} — {self.user_id}'


class OrderLine(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    item = models.ForeignKey(
        Items,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='order_lines',
    )
    item_name = models.CharField(max_length=40)
    quantity = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField()
    line_total = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.item_name} × {self.quantity}'
