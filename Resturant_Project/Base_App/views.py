from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from Base_App.models import BookTable, AboutUs, Feedback, ItemList, Items, Cart, Order, OrderLine
from django.contrib.auth import logout
from django.urls import reverse_lazy, reverse
from urllib.parse import urlencode
from django.utils.dateparse import parse_date, parse_time
from django.utils import timezone
from datetime import timedelta
import time

try:
    import razorpay
except ImportError:
    razorpay = None


def _cart_summary(cart):
    total_bill = sum(entry['price'] * entry['quantity'] for entry in cart.values())
    item_count = sum(entry['quantity'] for entry in cart.values())
    return total_bill, item_count


def add_to_cart(request):
    if request.method == 'POST' and request.user.is_authenticated:
        item_id = request.POST.get('item_id')
        item = get_object_or_404(Items, id=item_id)
        
        print(f'Item ID: {item_id}')  # Debug print
        print(f'Item: {item.Item_name}, Price: {item.Price}')  # Debug print

        # Retrieve or initialize the cart from the session
        cart = request.session.get('cart', {})
        print(f'Cart before update: {cart}')  # Debug print

        # Update the cart
        if item_id in cart:
            cart[item_id]['quantity'] += 1
        else:
            cart[item_id] = {
                'name': item.Item_name,
                'price': item.Price,
                'quantity': 1
            }

        request.session['cart'] = cart
        print(f'Cart after update: {cart}')  # Debug print

        total_bill, item_count = _cart_summary(cart)
        return JsonResponse({
            'message': 'Item added to cart',
            'cart': cart,
            'total_bill': total_bill,
            'item_count': item_count,
        })
    else:
        print('Invalid request')  # Debug print
        return JsonResponse({'error': 'Invalid request'}, status=400)


def get_cart_items(request):
    if request.user.is_authenticated:
        # cart_items = Cart.objects.filter(user=request.user).select_related('item')
        # items = [
        #     {
        #         'name': cart_item.item.Item_name,
        #         'quantity': cart_item.quantity,
        #         'price': cart_item.item.Price,
        #         'total': cart_item.quantity * cart_item.item.Price,
        #     }
        #     for cart_item in cart_items
        # ]

        cart = request.session.get('cart', {})
        items = []
        total_bill = 0

        for item_id, item in cart.items():
            item_total = item['quantity'] * item['price']
            total_bill += item_total

            items.append({
                'id': str(item_id),
                'name': item['name'],
                'quantity': item['quantity'],
                'price': item['price'],
                'total': item_total
            })

        _, item_count = _cart_summary(cart)
        return JsonResponse({
            'items': items,
            'total_bill': total_bill,
            'item_count': item_count,
        })

    return JsonResponse({'error': 'User not authenticated'}, status=401)


def update_cart_quantity(request):
    if request.method != 'POST' or not request.user.is_authenticated:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    item_id = str(request.POST.get('item_id', ''))
    action = request.POST.get('action')
    cart = request.session.get('cart', {})
    if item_id not in cart:
        return JsonResponse({'error': 'Item not in cart'}, status=404)
    if action == 'increment':
        cart[item_id]['quantity'] += 1
    elif action == 'decrement':
        cart[item_id]['quantity'] -= 1
        if cart[item_id]['quantity'] <= 0:
            del cart[item_id]
    else:
        return JsonResponse({'error': 'Invalid action'}, status=400)
    request.session['cart'] = cart
    total_bill, item_count = _cart_summary(cart)
    return JsonResponse({'cart': cart, 'total_bill': total_bill, 'item_count': item_count})


def remove_from_cart(request):
    if request.method != 'POST' or not request.user.is_authenticated:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    item_id = str(request.POST.get('item_id', ''))
    cart = request.session.get('cart', {})
    if item_id in cart:
        del cart[item_id]
    request.session['cart'] = cart
    total_bill, item_count = _cart_summary(cart)
    return JsonResponse({'cart': cart, 'total_bill': total_bill, 'item_count': item_count})


def clear_cart(request):
    if request.method != 'POST' or not request.user.is_authenticated:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    request.session['cart'] = {}
    return JsonResponse({'cart': {}, 'total_bill': 0, 'item_count': 0, 'message': 'Cart cleared'})


def _cart_lines_for_template(cart):
    lines = []
    total_bill = 0
    for item_id, entry in cart.items():
        line_total = entry['quantity'] * entry['price']
        total_bill += line_total
        lines.append({
            'id': str(item_id),
            'name': entry['name'],
            'quantity': entry['quantity'],
            'price': entry['price'],
            'total': line_total,
        })
    return lines, total_bill


def _save_order_from_session(
    user,
    cart,
    payment_method,
    razorpay_order_id='',
    razorpay_payment_id='',
    fulfillment_type=None,
):
    total_bill, _ = _cart_summary(cart)
    status = 'paid' if payment_method == Order.PAYMENT_RAZORPAY else 'cod_placed'
    if fulfillment_type is None:
        fulfillment_type = Order.FULFILL_DINE_IN
    order = Order.objects.create(
        user=user,
        total_amount=total_bill,
        payment_method=payment_method,
        fulfillment_type=fulfillment_type,
        status=status,
        tracking_status=Order.TRACKING_RECEIVED,
        razorpay_order_id=razorpay_order_id or '',
        razorpay_payment_id=razorpay_payment_id or '',
    )
    for item_id, entry in cart.items():
        item_obj = Items.objects.filter(pk=item_id).first()
        line_total = entry['quantity'] * entry['price']
        OrderLine.objects.create(
            order=order,
            item=item_obj,
            item_name=entry['name'],
            quantity=entry['quantity'],
            unit_price=entry['price'],
            line_total=line_total,
        )
    return order


@login_required
def checkout_view(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, 'Your cart is empty.')
        return redirect('Menu')
    lines, total_bill = _cart_lines_for_template(cart)
    razorpay_ready = bool(
        razorpay
        and settings.RAZORPAY_KEY_ID
        and settings.RAZORPAY_KEY_SECRET
    )
    fake_online_ready = bool(
        getattr(settings, 'FAKE_ONLINE_PAYMENT', False)
        and not razorpay_ready
    )
    is_home_delivery = request.session.get('order_fulfillment') == 'delivery'
    return render(request, 'checkout.html', {
        'cart_lines': lines,
        'total_bill': total_bill,
        'razorpay_ready': razorpay_ready,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID or '',
        'fake_online_ready': fake_online_ready,
        'is_home_delivery': is_home_delivery,
        'razorpay_sdk_installed': razorpay is not None,
        'razorpay_env_file': str(settings.BASE_DIR / '.env'),
    })


@login_required
@require_POST
def place_order_cod(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('Menu')
    fulfillment = (
        Order.FULFILL_DELIVERY
        if request.session.get('order_fulfillment') == 'delivery'
        else Order.FULFILL_DINE_IN
    )
    order = _save_order_from_session(
        request.user, cart, Order.PAYMENT_COD, fulfillment_type=fulfillment,
    )
    request.session['cart'] = {}
    request.session.pop('order_fulfillment', None)
    for key in ('razorpay_order_id', 'razorpay_amount_paise'):
        request.session.pop(key, None)
    messages.success(request, 'Order placed. Pay with cash on delivery. Track your order below.')
    return redirect('order_track', pk=order.pk)


@never_cache
@login_required
@require_POST
def checkout_simulate_online_payment(request):
    """DEBUG-only: complete checkout as paid without Razorpay (local testing)."""
    if not (
        getattr(settings, 'FAKE_ONLINE_PAYMENT', False)
        and not (
            razorpay
            and settings.RAZORPAY_KEY_ID
            and settings.RAZORPAY_KEY_SECRET
        )
    ):
        return JsonResponse({'error': 'Simulated payment is disabled.'}, status=403)
    cart = request.session.get('cart', {})
    if not cart:
        return JsonResponse({'error': 'Your cart is empty.'}, status=400)
    fulfillment = (
        Order.FULFILL_DELIVERY
        if request.session.get('order_fulfillment') == 'delivery'
        else Order.FULFILL_DINE_IN
    )
    order = _save_order_from_session(
        request.user,
        cart,
        Order.PAYMENT_RAZORPAY,
        razorpay_order_id='project_online',
        razorpay_payment_id='project_online',
        fulfillment_type=fulfillment,
    )
    request.session['cart'] = {}
    request.session.pop('order_fulfillment', None)
    for key in ('razorpay_order_id', 'razorpay_amount_paise'):
        request.session.pop(key, None)
    messages.success(request, 'Online payment completed. Track your order below.')
    return JsonResponse({'redirect_url': reverse('order_track', kwargs={'pk': order.pk})})


@never_cache
@login_required
@require_POST
def razorpay_create_order(request):
    if not razorpay or not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return JsonResponse({'error': 'Online payment is not configured.'}, status=503)
    cart = request.session.get('cart', {})
    total_bill, _ = _cart_summary(cart)
    if total_bill <= 0:
        return JsonResponse({'error': 'Your cart is empty.'}, status=400)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    amount_paise = int(total_bill * 100)
    receipt = f'u{request.user.id}_{int(time.time())}'
    try:
        rp_order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': receipt,
            'payment_capture': 1,
        })
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=502)
    request.session['razorpay_order_id'] = rp_order['id']
    request.session['razorpay_amount_paise'] = amount_paise
    prefill = {
        'name': request.user.get_full_name() or request.user.username,
        'email': request.user.email or '',
    }
    return JsonResponse({
        'razorpay_order_id': rp_order['id'],
        'amount': amount_paise,
        'currency': 'INR',
        'key_id': settings.RAZORPAY_KEY_ID,
        'prefill': prefill,
    })


@never_cache
@login_required
@require_POST
def razorpay_verify_payment(request):
    if not razorpay or not settings.RAZORPAY_KEY_SECRET:
        return JsonResponse({'error': 'Online payment is not configured.'}, status=503)
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_signature = request.POST.get('razorpay_signature')
    expected_oid = request.session.get('razorpay_order_id')
    if not expected_oid or expected_oid != razorpay_order_id:
        return JsonResponse({'error': 'Invalid or expired checkout session.'}, status=400)
    cart = request.session.get('cart', {})
    if not cart:
        return JsonResponse({'error': 'Your cart is empty.'}, status=400)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except Exception:
        return JsonResponse({'error': 'Payment verification failed.'}, status=400)
    fulfillment = (
        Order.FULFILL_DELIVERY
        if request.session.get('order_fulfillment') == 'delivery'
        else Order.FULFILL_DINE_IN
    )
    order = _save_order_from_session(
        request.user,
        cart,
        Order.PAYMENT_RAZORPAY,
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id or '',
        fulfillment_type=fulfillment,
    )
    request.session['cart'] = {}
    request.session.pop('order_fulfillment', None)
    for key in ('razorpay_order_id', 'razorpay_amount_paise'):
        request.session.pop(key, None)
    messages.success(request, 'Payment successful. Track your order below.')
    return JsonResponse({'redirect_url': reverse('order_track', kwargs={'pk': order.pk})})


ETA_BY_STEP_MINUTES = {
    Order.TRACKING_RECEIVED: 35,
    Order.TRACKING_QUEUE: 28,
    Order.TRACKING_PREPARING: 18,
    Order.TRACKING_READY: 10,
    Order.TRACKING_SERVING: 4,
    Order.TRACKING_DELIVERED: 0,
}

DELIVERY_ETA_BY_STEP_MINUTES = {
    Order.TRACKING_RECEIVED: 45,
    Order.TRACKING_QUEUE: 35,
    Order.TRACKING_PREPARING: 25,
    Order.TRACKING_READY: 16,
    Order.TRACKING_SERVING: 8,
    Order.TRACKING_DELIVERED: 0,
}

TRACKING_NEXT_ACTION = {
    Order.TRACKING_RECEIVED: 'Kitchen team will pick your order shortly.',
    Order.TRACKING_QUEUE: 'You are in line. We are preparing orders ahead of yours.',
    Order.TRACKING_PREPARING: 'Chefs are preparing your dishes right now.',
    Order.TRACKING_READY: 'Food is ready. Staff assignment in progress.',
    Order.TRACKING_SERVING: 'Final handoff in progress.',
    Order.TRACKING_DELIVERED: 'Order completed successfully.',
}


def _eta_minutes_for_order(order):
    table = (
        DELIVERY_ETA_BY_STEP_MINUTES
        if order.fulfillment_type == Order.FULFILL_DELIVERY
        else ETA_BY_STEP_MINUTES
    )
    return table.get(order.tracking_status, 0)


def _tracking_payload(order):
    step_index = order.tracking_step_index()
    max_steps = max(len(order._TRACKING_STEP_ORDER) - 1, 1)
    progress_percent = int((step_index / max_steps) * 100)
    eta_minutes = _eta_minutes_for_order(order)
    eta_at = timezone.localtime(timezone.now() + timedelta(minutes=eta_minutes))
    status_title, status_detail = order.tracking_customer_message()
    return {
        'tracking_status': order.tracking_status,
        'table_number': order.table_number or '',
        'status_title': status_title,
        'status_detail': status_detail,
        'step_index': step_index,
        'progress_percent': progress_percent,
        'next_action': TRACKING_NEXT_ACTION.get(order.tracking_status, 'Please stay on this page for updates.'),
        'eta_minutes': eta_minutes,
        'eta_time_display': eta_at.strftime('%I:%M %p').lstrip('0') if eta_minutes else 'Completed',
        'updated_at': timezone.localtime(order.tracking_updated_at).strftime('%d %b, %I:%M %p'),
        'is_done': order.tracking_status == Order.TRACKING_DELIVERED,
    }


@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('lines')
    return render(request, 'order_history.html', {'orders': orders})


@never_cache
@login_required
def order_track_view(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related('lines'), pk=pk, user=request.user)
    tracking = _tracking_payload(order)
    return render(request, 'order_track.html', {
        'order': order,
        'tracking': tracking,
    })


@never_cache
@login_required
def order_track_poll(request, pk):
    order = get_object_or_404(Order.objects.select_related('user'), pk=pk, user=request.user)
    return JsonResponse(_tracking_payload(order))


class LoginView(AuthLoginView):
    template_name = 'login.html'
    def get_success_url(self):
        # Check if the user is an admin
        if self.request.user.is_staff:
            return reverse_lazy('admin:index')  # Redirects to the Django admin panel
        return reverse_lazy('Home')  # Redirects to the home page if not an admin

def LogoutView(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect(' Home')  # Redirect to a page after logout, e.g., the home page

def SignupView(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('Home')
        else:
            messages.error(request, 'Error during signup. Please try again.')
    else:
        form = UserCreationForm()
    return render(request, 'login.html', {'form': form, 'tab': 'signup'})


def HomeView(request):
    items =  Items.objects.all()
    list = ItemList.objects.all()
    review = Feedback.objects.all().order_by('-id')[:5]
    return render(request, 'home.html',{'items': items, 'list': list, 'review': review})


def AboutView(request):
    data = AboutUs.objects.all()
    return render(request, 'about.html',{'data': data})


def MenuView(request):
    items = Items.objects.all()
    list = ItemList.objects.all()
    return render(request, 'menu.html', {
        'items': items,
        'list': list,
        'home_delivery_mode': request.session.get('order_fulfillment') == 'delivery',
    })


def start_table_only(request):
    request.session['table_booking_mode'] = 'simple'
    request.session.pop('order_fulfillment', None)
    return redirect('Book_Table')


def start_table_preorder(request):
    request.session['table_booking_mode'] = 'preorder'
    request.session.pop('order_fulfillment', None)
    return redirect('Book_Table')


def start_home_delivery(request):
    if not request.user.is_authenticated:
        login_url = reverse('login')
        next_url = reverse('start_home_delivery')
        return redirect(f'{login_url}?{urlencode({"next": next_url})}')
    request.session['order_fulfillment'] = 'delivery'
    request.session.pop('table_booking_mode', None)
    messages.success(
        request,
        'Home delivery: add dishes to your cart, then checkout. We will deliver to your address.',
    )
    return redirect('Menu')


def book_table_skip_preorder(request):
    """After booking, user chose not to pre-order — confirm and go home."""
    messages.success(
        request,
        'Your table is reserved. We look forward to seeing you — no pre-order was added.',
    )
    return redirect('Home')


def book_table_preorder_prompt_view(request):
    """Shows pre-order choice after a successful booking (GET after redirect)."""
    data = request.session.pop('book_table_preorder_context', None)
    if not data:
        messages.info(request, 'Book a table first, then you can choose to pre-order food.')
        return redirect('Book_Table')
    return render(request, 'book_table_preorder_prompt.html', data)


def BookTableView(request):
    google_maps_api_key = settings.GOOGLE_MAPS_API_KEY

    if request.method == 'GET':
        flow = request.GET.get('flow')
        if flow == 'preorder':
            request.session['table_booking_mode'] = 'preorder'
        elif flow == 'simple':
            request.session['table_booking_mode'] = 'simple'
        if 'table_booking_mode' not in request.session:
            request.session['table_booking_mode'] = 'simple'

    booking_mode = request.session.get('table_booking_mode', 'simple')

    if request.method == 'POST':
        name = (request.POST.get('user_name') or '').strip()
        phone_raw = request.POST.get('phone_number') or ''
        phone_digits = ''.join(c for c in phone_raw if c.isdigit())
        email = (request.POST.get('user_email') or '').strip()
        total_person = request.POST.get('total_person') or ''
        booking_data = (request.POST.get('booking_data') or '').strip()
        booking_time_raw = (request.POST.get('booking_time') or '').strip()

        valid_persons = {'2', '3', '4', '5'}
        booking_date = parse_date(booking_data) if booking_data else None
        booking_time = parse_time(booking_time_raw) if booking_time_raw else None

        if not name:
            messages.error(request, 'Please enter your name.')
        elif len(phone_digits) != 10:
            messages.error(request, 'Please enter a valid 10-digit phone number (spaces or +91 are OK — we use digits only).')
        elif not email:
            messages.error(request, 'Email is required so we can send your booking confirmation.')
        elif total_person not in valid_persons:
            messages.error(request, 'Please select how many guests are coming.')
        elif not booking_date:
            messages.error(request, 'Please choose a valid booking date.')
        elif not booking_time:
            messages.error(request, 'Please choose a reservation time.')
        else:
            data = BookTable(
                Name=name,
                Phone_number=int(phone_digits),
                Email=email,
                Total_person=int(total_person),
                Booking_date=booking_date,
                Booking_time=booking_time,
            )
            data.save()

            time_display = booking_time.strftime('%I:%M %p').lstrip('0') if booking_time else ''
            subject = 'Booking Confirmation'
            message = (
                f'Hello {name},\n\nYour booking has been successfully received.\n'
                f'Booking details:\nTotal persons: {total_person}\n'
                f'Date: {booking_data}\nTime: {time_display}\n\nThank you for choosing us!'
            )
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]

            email_sent = False
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                email_sent = True
            except Exception:
                messages.warning(
                    request,
                    'Your booking was saved, but we could not send the confirmation email. You can still continue below.',
                )

            mode = request.session.get('table_booking_mode', 'simple')
            if mode == 'preorder':
                request.session['book_table_preorder_context'] = {
                    'guest_name': name,
                    'booking_date': booking_data,
                    'booking_time_display': time_display,
                    'total_person': total_person,
                    'email_sent': email_sent,
                }
                return redirect('book_table_preorder_prompt')

            messages.success(
                request,
                f'Table reserved for {booking_data} at {time_display}. See you at the restaurant!',
            )
            return redirect('Home')

    return render(request, 'book_table.html', {
        'google_maps_api_key': google_maps_api_key,
        'booking_mode': booking_mode,
    })


def FeedbackView(request):
    if request.method == 'POST':
        # Get data from the form
        name = request.POST.get('User_name')
        feedback = request.POST.get('Description')  # Assuming 'Feedback' field is a description
        rating = request.POST.get('Rating')
        image = request.FILES.get('Selfie')  # 'Selfie' field from the form

        # Print to check the values
        print('-->', name, feedback, rating, image)

        # Check if the name is provided
        if name != '':
            # Save the feedback data to the Feedback model
            feedback_data = Feedback(
                User_name=name,
                Description=feedback,
                Rating=rating,
                Image=image  # Save the uploaded image
            )
            feedback_data.save()

            # Add success message
            messages.success(request, 'Feedback submitted successfully!')

            # Optionally, you can redirect or return a success message
            return render(request, 'feedback.html', {'success': 'Feedback submitted successfully!'})

    return render(request, 'feedback.html')

