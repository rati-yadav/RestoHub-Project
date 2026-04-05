from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from Base_App.views import *

urlpatterns = [
    path('admin/', admin.site.urls, name='admin_pannel'),
    path('login/', LoginView.as_view(), name='login'),
    path('signup/', SignupView, name='signup'),
    path('logout/', LogoutView, name='logout'),
    path('', HomeView, name='Home'),
    path('start/table-only/', start_table_only, name='start_table_only'),
    path('start/table-preorder/', start_table_preorder, name='start_table_preorder'),
    path('start/home-delivery/', start_home_delivery, name='start_home_delivery'),
    path('book_table/', BookTableView, name='Book_Table'),
    path('book_table/preorder/', book_table_preorder_prompt_view, name='book_table_preorder_prompt'),
    path('book_table/skip-preorder/', book_table_skip_preorder, name='book_table_skip_preorder'),
    path('menu/', MenuView, name='Menu'),
    path('about/', AboutView, name='About'),
    path('feedback/', FeedbackView, name='Feedback_Form'),
    path('add-to-cart/', add_to_cart, name='add_to_cart'),
    path('get-cart-items/', get_cart_items, name='get_cart_items'),
    path('update-cart-quantity/', update_cart_quantity, name='update_cart_quantity'),
    path('remove-from-cart/', remove_from_cart, name='remove_from_cart'),
    path('clear-cart/', clear_cart, name='clear_cart'),
    path('checkout/', checkout_view, name='Checkout'),
    path('place-order-cod/', place_order_cod, name='place_order_cod'),
    path('razorpay/create-order/', razorpay_create_order, name='razorpay_create_order'),
    path('razorpay/verify/', razorpay_verify_payment, name='razorpay_verify_payment'),
    path('checkout/simulate-online-pay/', checkout_simulate_online_payment, name='checkout_simulate_online'),
    path('orders/', order_history_view, name='order_history'),
    path('orders/<int:pk>/track/', order_track_view, name='order_track'),
    path('orders/<int:pk>/track/poll/', order_track_poll, name='order_track_poll'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
