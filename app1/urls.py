from django.urls import path
from .views import *

urlpatterns = [    
    path('',signin,name='signin'),
    path('signin',signin,name='signin'),
    path('signup',signup,name='signup'),
    path('signout',signout,name='signout'),
    path('SuperAdmin_Dashboard',SuperAdmin_Dashboard,name='SuperAdmin_Dashboard'),

    path('add_restaurant',add_restaurant,name='add_restaurant'),
    path('edit_restaurant/<str:id>/', edit_restaurant, name='edit_restaurant'),
    path('delete_restaurant/<str:id>', delete_restaurant, name='delete_restaurant'),
    path('update_all_databases',update_all_databases,name='update_all_databases'),

    path('add_admins', add_admins, name='add_admins'),
    path('edit_admin/<str:id>/', edit_admin, name='edit_admin'),
    path('delete_admin/<str:id>', delete_admin, name='delete_admin'),

    path('Admin_Dashboard',Admin_Dashboard,name='Admin_Dashboard'),

    path('add_staff', add_staff, name='add_staff'),
    path('edit_staff/<str:id>/', edit_staff, name='edit_staff'),
    path('delete_staff/<str:id>', delete_staff, name='delete_staff'),

    path('staff_dashboard',staff_dashboard,name='staff_dashboard'),


    path('ensure_database_connection',ensure_database_connection,name='ensure_database_connection'),

    path('restaurant_mgmt',restaurant_mgmt, name='restaurant_mgmt'),

    path('add_category', add_category, name='add_category'),
    path('edit_category/<str:id>/', edit_category, name='edit_category'),
    path('delete_category/<str:id>', delete_category, name='delete_category'),

    path('add_menuitem', add_menuitem, name='add_menuitem'),
    path('edit_menuitem/<str:id>/', edit_menuitem, name='edit_menuitem'),
    path('delete_menuitem/<str:id>', delete_menuitem, name='delete_menuitem'),

    path('add_table', add_table, name='add_table'),
    path('view_qr_code/<str:id>/', view_qr_code, name='view_qr_code'),
    path('edit_table/<str:id>/', edit_table, name='edit_table'),
    path('delete_table/<str:id>', delete_table, name='delete_table'),

    path('place_order', place_order, name='place_order'),
    path('cancel_order/<str:order_no>', cancel_order, name='cancel_order'),
    path('takeaway_orders', takeaway_orders, name='takeaway_orders'),
    path('all_orders', all_orders, name='all_orders'),

    path('addmore_items/<str:order_no>', addmore_items, name='addmore_items'),

    path('kot_management',kot_management,name='kot_management'),

    path('bill_generate/', bill_generate, name="bill_generate"),  
    path('bill_generate/<str:order_no>/', bill_generate, name="bill_generate_with_order"),
    path('order_invoice/<str:order_no>/', generate_order_pdf, name='order_invoice'),

    path('update_restaurant', update_restaurant, name='update_restaurant'),
    path('pending_kots', pending_kots, name='pending_kots'),

    path('shift_table/<str:order_no>/<str:new_table_no>/', shift_table, name='shift_table'),

    path('waiter_place_order', waiter_place_order, name='waiter_place_order'),

    path('w_addmore_items/<str:order_no>', w_addmore_items, name='w_addmore_items'),

    path('QR_order', QR_order, name='QR_order')
]
