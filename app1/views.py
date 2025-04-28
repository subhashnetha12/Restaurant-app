from django.shortcuts import render,redirect,get_object_or_404
from .models import *
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from app1.utils import create_database_and_tables 
from django.core.management import call_command
from django.conf import settings
from django.db import connections, OperationalError, ProgrammingError
from app2.models import *
from django.apps import apps 

from django.utils import timezone

from django.db import connections
from django.core.management import call_command
from django.conf import settings
from django.db.utils import OperationalError
from django.db import connections, DEFAULT_DB_ALIAS
from django.db import connection


import uuid
from django.shortcuts import render, redirect
from django.http import JsonResponse
from datetime import date, datetime, timedelta
from django.utils import timezone
from decimal import Decimal
from django.db.models import Count, Sum

import qrcode
from io import BytesIO
from django.core.files.base import ContentFile


from django.utils.timezone import now


def ensure_database_connection(db_name):
    """
    Ensure that the given database exists, is connected, and has all required tables for `app2`.
    If the database is not configured, it will configure it dynamically.
    """
    # Ensure the database is defined in settings
    if db_name not in settings.DATABASES:
        settings.DATABASES[db_name] = {
            'ENGINE': settings.DATABASES['default']['ENGINE'],
            'NAME': db_name if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3' else f"{db_name}.sqlite3",
            'USER': settings.DATABASES['default'].get('USER', ''),
            'PASSWORD': settings.DATABASES['default'].get('PASSWORD', ''),
            'HOST': settings.DATABASES['default'].get('HOST', 'localhost'),
            'PORT': settings.DATABASES['default'].get('PORT', ''),
            'ATOMIC_REQUESTS': settings.DATABASES['default'].get('ATOMIC_REQUESTS', False),
            'TIME_ZONE': settings.DATABASES['default'].get('TIME_ZONE', settings.TIME_ZONE),
            'CONN_HEALTH_CHECKS': settings.DATABASES['default'].get('CONN_HEALTH_CHECKS', False),
            'CONN_MAX_AGE': settings.DATABASES['default'].get('CONN_MAX_AGE', 0),
            'OPTIONS': settings.DATABASES['default'].get('OPTIONS', {}),
            'DISABLE_SERVER_SIDE_CURSORS': settings.DATABASES['default'].get('DISABLE_SERVER_SIDE_CURSORS', False),
            'AUTOCOMMIT': settings.DATABASES['default'].get('AUTOCOMMIT', True),
        }

    # Check the database connection
    try:
        connections[db_name].ensure_connection()
        print(f"Database connection established for {db_name}")
    except OperationalError as e:
        print(f"Error connecting to database {db_name}: {e}")
        raise

    # Apply migrations for app2 only
    try:
        print(f"Applying migrations for `app2` to database {db_name}...")
        call_command('migrate', 'app2', '--database', db_name, verbosity=2)
        print(f"Migrations for `app2` applied successfully to {db_name}")
    except Exception as e:
        print(f"Error applying migrations to database {db_name}: {e}")
        raise

    return db_name  


def SuperAdmin_Dashboard(request):
    username = request.session.get('username')
    if username: 
        data = SuperAdmin.objects.get(username=username)
        restaurants_count = Restaurants.objects.count()
        admins_count = Admins.objects.all().count()

        all_rest = Restaurants.objects.all()

        staff_count = 0
        if all_rest:
            for i in all_rest:                        
                db_name = ensure_database_connection(i.DB_name)
                staff_count += Staff.objects.using(db_name).count()
                connections[db_name].close()
            
        connections[DEFAULT_DB_ALIAS].ensure_connection()            
    
    else:
        data = None
    context = {'data':data,'restaurants_count':restaurants_count,'admins_count':admins_count,'staff_count':staff_count}
    return render(request,'Super-Admin/SuperAdmin_Dashboard.html',context)


def Admin_Dashboard(request):
    username = request.session.get('username')
    
    if username:
        data = Admins.objects.get(username=username)
        db_name = ensure_database_connection(data.DB_name)          
    else:
        data = None
        db_name = None

    total_staff = Staff.objects.using(db_name).count()
    total_orders = Orders.objects.using(db_name).count()

    total_payments = Payments.objects.using(db_name).aggregate(total=Sum('total_amount'))['total'] or 0
    

    context={
        'data': data,
        'total_staff': total_staff,
        'total_orders': total_orders,
        'total_payments': total_payments,
    }

    return render(request, 'Rest-Admin/Admin_Dashboard.html', context)


def staff_dashboard(request):
    username = request.session.get('username')
    all_rest = Restaurants.objects.all()       
    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None
    
    tables = Table_list.objects.using(db_name).all() 

    occupied_tables = tables.filter(status="Occupied").exclude(occupied_order_no__isnull=True)
    occupied_order_nos = [table.occupied_order_no for table in occupied_tables]
    relevant_orders = Orders.objects.using(db_name).filter(order_no__in=occupied_order_nos)

     

    kot_det = KOT.objects.using(db_name).all()
    kotitem_det = KOTItems.objects.using(db_name).filter(kot_no__in=kot_det)

    total_kot = KOT.objects.using(db_name).count()
    today_kot = KOT.objects.using(db_name).filter(created_at__date=timezone.now().date()).count()
    pending_kot = KOT.objects.using(db_name).filter(status='Pending').count()


    if data.role == 'Receptionist':
        return render(request,'Staff/reception_dashboard.html',{'data':data, 'tables':tables, 'relevant_orders':relevant_orders})

    if data.role == 'Chef':
        return render(request,'Staff/KOT_dashboard.html',{'data':data, 'total_kot':total_kot, 'today_kot':today_kot,'pending_kot':pending_kot})

    if data.role == 'Waiter':
        return render(request,'Waiter/waiter_dashboard.html',{'data':data,'tables':tables, 'relevant_orders':relevant_orders})


def signin(request):    

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        password = request.POST.get('password')

        try:
            s_admin = SuperAdmin.objects.get(phone_number=phone_number)
        except:
            s_admin = None

        try:
            admin = Admins.objects.get(phone_number=phone_number)
        except:
            admin = None

        all_rest = Restaurants.objects.all()

        if s_admin:
            if check_password(password, s_admin.password):
                request.session['username'] = s_admin.username
                messages.success(request, 'Login Sucess')
                return redirect('SuperAdmin_Dashboard')
            else:
                messages.error(request, 'Invalid username or password')
                return render(request,'signin.html',{'phone_number':phone_number})
        elif admin:
            if check_password(password, admin.password):
                request.session['username'] = admin.username
                messages.success(request, 'Login Sucess')
                return redirect('Admin_Dashboard')
            else:
                messages.error(request, 'Invalid username or password')
                return render(request,'signin.html',{'phone_number':phone_number})  

        else:            
            for i in all_rest:                                
                db_name = ensure_database_connection(i.DB_name)                         
                try: 
                    staff = Staff.objects.using(db_name).get(phone_number=phone_number) 
                except:
                    staff = None                
                if staff:
                    if check_password(password, staff.password):
                        request.session['username'] = staff.username
                        messages.success(request, 'Login Sucess')
                        return redirect('staff_dashboard')
            messages.error(request, 'Invalid username or password')
            return render(request,'signin.html',{'phone_number':phone_number})            
    return render(request,'signin.html')


def signout(request):
    request.session.flush()
    return redirect('signin')


def signup(request):
    all_s_admin = SuperAdmin.objects.all()
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        phone_number = request.POST.get('phone_number')
        context = {'username':username,'phone_number':phone_number}
        for i in all_s_admin:
            if i.phone_number == int(phone_number):
                messages.error(request,'number already exists')
                return render(request,'signup.html',context)
        SuperAdmin.objects.create(
            username = username,
            password = password,
            phone_number = phone_number
        )
        messages.success(request,'SuperAdmin saved ')
        return redirect('signin')                
    return render(request,'signup.html')


def add_restaurant(request):
    username = request.session.get('username')
    if username: 
        data = SuperAdmin.objects.get(username=username)
    else:
        data = None

    
    all_rest = Restaurants.objects.all()
        
    if request.method == 'POST':
        name = request.POST.get('name')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        address1 = request.POST.get('address1')
        address2 = request.POST.get('address2')
        city = request.POST.get('city')
        postal_code = request.POST.get('postal_code')

        mobile_number = request.POST.get('postal_code')
        state = request.POST.get('state')
        gst_no = request.POST.get('gst_no') 

        # Generate a unique database name
        last_restaurant = Restaurants.objects.last()
        next_db_number = int(last_restaurant.DB_name.split("_")[1]) + 1 if last_restaurant else 1
        db_name = f"DB_{next_db_number}"

        
        restaurant = Restaurants(
            name=name, 
            phone_number=phone_number, 
            email=email, 
            address1=address1, 
            address2=address2,
            city=city, 
            postal_code=postal_code, 
            DB_name=db_name,
            gst_no=gst_no,
            mobile_number=mobile_number,
            state =state,
        )
        restaurant.save()

        # Create database and tables dynamically
        create_database_and_tables(db_name)

        messages.success(request,'Restaurant added')
        return redirect('add_restaurant')
    
    return render(request, 'Super-Admin/add_restaurant.html', {'data':data, 'all_rest':all_rest})


def edit_restaurant(request, id):
    username = request.session.get('username')
    if not username:
        return redirect('signin')  # Redirect if user is not logged in

    if username: 
        data = SuperAdmin.objects.get(username=username)
    else:
        data = None
    
    restaurant = get_object_or_404(Restaurants, id=id)
    
    if request.method == 'POST':
        edit_name = request.POST.get('edit_name').strip()
        edit_phone_number = request.POST.get('edit_phone_number').strip()
        edit_email = request.POST.get('edit_email').strip()
        edit_address1 = request.POST.get('edit_address1').strip()
        edit_address2 = request.POST.get('edit_address2').strip()
        edit_city = request.POST.get('edit_city').strip()
        edit_postal_code = request.POST.get('edit_postal_code').strip()
        edit_mobile_number = request.POST.get('edit_mobile_number').strip()
        edit_state = request.POST.get('edit_state').strip()
        edit_gst_no = request.POST.get('edit_gst_no').strip()

        if Restaurants.objects.filter(name=edit_name).exclude(id=id).exists():
            messages.error(request, 'This Restaurant Name already exists.')
            return redirect('add_restaurant')

        if Restaurants.objects.filter(phone_number=edit_phone_number).exclude(id=id).exists():
            messages.error(request, 'This Phone Number is already in use. Please use a different one.')
            return redirect('add_restaurant')

        if Restaurants.objects.filter(email=edit_email).exclude(id=id).exists():
            messages.error(request, 'This Email is already in use. Please use a different one.')
            return redirect('add_restaurant')

        # Update the restaurant details
        restaurant.name = edit_name
        restaurant.phone_number = edit_phone_number
        restaurant.email = edit_email
        restaurant.address1 = edit_address1
        restaurant.address2 = edit_address2
        restaurant.city = edit_city
        restaurant.postal_code = edit_postal_code
        restaurant.mobile_number = edit_mobile_number
        restaurant.state = edit_state
        restaurant.gst_no = edit_gst_no
        restaurant.save()

        messages.success(request, 'Restaurant details updated successfully!')
        return redirect('add_restaurant')

    return render(request, 'Super-Admin/add_restaurant.html', {'data': data, 'restaurant': restaurant})


def delete_restaurant(request, id):
    username = request.session.get('username')
    if not username:
        messages.error(request, "You must be logged in to perform this action.")
        return redirect('l')

    restaurant = get_object_or_404(Restaurants, id=id)

    db_name = restaurant.DB_name

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")  
    except Exception as e:
        messages.error(request, f"Error deleting database {db_name}: {e}")

    all_admin = Admins.objects.filter(DB_name = restaurant.DB_name)
    all_admin.delete()    

    restaurant.delete()

    messages.success(request, "Restaurant deleted successfully.")
    return redirect('add_restaurant')


def restaurant_mgmt(request):
    username = request.session.get('username')
    if username: 
        data = SuperAdmin.objects.get(username=username)
    else:
        data = None
    
    return render(request, 'Super-Admin/restaurant_mgmt.html', {'data':data})


def update_all_databases(request): 

    all_rest = Restaurants.objects.all()

    try:        
        for restaurant in all_rest:
            db_name = restaurant.DB_name

            if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
                if not db_name.endswith('.sqlite3'):
                    db_name = f"{db_name}.sqlite3"

            if db_name not in settings.DATABASES:

                settings.DATABASES[db_name] = {
                    'ENGINE': settings.DATABASES['default']['ENGINE'],
                    'NAME': db_name,
                    'USER': settings.DATABASES['default'].get('USER', ''),
                    'PASSWORD': settings.DATABASES['default'].get('PASSWORD', ''),
                    'HOST': settings.DATABASES['default'].get('HOST', 'localhost'),
                    'PORT': settings.DATABASES['default'].get('PORT', ''),
                    'ATOMIC_REQUESTS': settings.DATABASES['default'].get('ATOMIC_REQUESTS', False),
                    'TIME_ZONE': settings.DATABASES['default'].get('TIME_ZONE', settings.TIME_ZONE),
                    'CONN_HEALTH_CHECKS': settings.DATABASES['default'].get('CONN_HEALTH_CHECKS', False),
                    'CONN_MAX_AGE': settings.DATABASES['default'].get('CONN_MAX_AGE', 0),
                    'OPTIONS': settings.DATABASES['default'].get('OPTIONS', {}),
                    'DISABLE_SERVER_SIDE_CURSORS': settings.DATABASES['default'].get('DISABLE_SERVER_SIDE_CURSORS', False),
                    'AUTOCOMMIT': settings.DATABASES['default'].get('AUTOCOMMIT', True),
                }

            try:
                connections[db_name].ensure_connection()

                call_command('migrate', '--database', db_name, app_label='app2', verbosity=2)
                print(f"Updated database: {db_name}")
            except Exception as e:
                print(f"Error updating database {db_name}: {e}")

        messages.success(request, "All databases updated successfully.")
    except Exception as e:
        print(f"Error during update: {e}")
        messages.error(request, f"Error updating databases: {e}")

    return redirect('add_restaurant')  


def add_admins(request):
    username = request.session.get('username')
    if username: 
        data = SuperAdmin.objects.get(username=username)
    else:
        data = None         

    all_rest = Restaurants.objects.all()
    rest_admin = Admins.objects.all()    

    if request.method == 'POST':
        name = request.POST.get('name')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        restaurant_info = request.POST.get('restaurant_info')  

        if password != confirm_password:
            messages.error(request, 'Password mismatch, Please try again.') 
        
        if restaurant_info:
            try:
                restaurant_name, restaurant_address = [x.strip() for x in restaurant_info.split("|")]
                restaurant_det = Restaurants.objects.get(name=restaurant_name, address1=restaurant_address)
            except (ValueError, Restaurants.DoesNotExist):
                messages.error(request, 'Selected restaurant does not exist. Please try again.')
                return redirect('add_admins')

        Admin = Admins(
            username=name, 
            phone_number=phone_number, 
            email=email, 
            password=password, 
            DB_name=restaurant_det.DB_name,             
        )
        Admin.save()

        messages.success(request,'Admin added')
        return redirect('add_admins')
    
    context={'data':data, 'all_rest':all_rest, 'rest_admin':rest_admin}
    
    return render(request, 'Super-Admin/add_admins.html', context)


def edit_admin(request, id):
    username = request.session.get('username')
    
    if not username:
        return redirect('signin')

    if username: 
        data = SuperAdmin.objects.get(username=username)
    else:
        data = None 

    admin = get_object_or_404(Admins, id=id)

    if request.method == 'POST':
        edit_name = request.POST.get('edit_name', '').strip()
        edit_phone_number = request.POST.get('edit_phone_number', '').strip()
        edit_email = request.POST.get('edit_email', '').strip()
        edit_restaurant_id = request.POST.get('edit_restaurant_info')  # Get selected restaurant ID

        if Admins.objects.filter(phone_number=edit_phone_number).exclude(id=id).exists():
            messages.error(request, 'This Phone Number is already in use. Please use a different one.')
            return redirect('add_admins')

        if Admins.objects.filter(email=edit_email).exclude(id=id).exists():
            messages.error(request, 'This Email is already in use. Please use a different one.')
            return redirect('add_admins')

        if edit_restaurant_id:
            restaurant_det = Restaurants.objects.get(id=edit_restaurant_id)
            admin.DB_name = restaurant_det.DB_name  

        admin.username = edit_name
        admin.phone_number = edit_phone_number
        admin.email = edit_email
        admin.save()

        messages.success(request, "Admin details updated successfully.")
        return redirect('add_admins')

    return render(request, 'Super-Admin/add_admins.html', {'data': data, 'admin': admin})


def delete_admin(request, id):
    username = request.session.get('username')
    if not username:
        return redirect('signin')
    
    if username: 
        data = SuperAdmin.objects.get(username=username)
    else:
        data = None

    admin = get_object_or_404(Admins, id=id)
    admin.delete()

    messages.success(request, "Admin deleted successfully.")
    return redirect('add_admins')


def update_restaurant(request):
    username = request.session.get('username')

    if not username:
        messages.error(request, "You must be logged in.")
        return redirect('signin')  

    try:
        data = Admins.objects.get(username=username)
        db_name = ensure_database_connection(data.DB_name)
        restaurant_det = Restaurants.objects.get(DB_name=data.DB_name)  
    except (Admins.DoesNotExist, Restaurants.DoesNotExist):
        messages.error(request, "Restaurant not found.")
        return redirect('dashboard')  

    if request.method == 'POST':
        restaurant_det.name = request.POST.get('name', restaurant_det.name).strip()
        restaurant_det.email = request.POST.get('email', restaurant_det.email).strip()
        restaurant_det.address1 = request.POST.get('address1', restaurant_det.address1).strip()
        restaurant_det.address2 = request.POST.get('address2', restaurant_det.address2).strip()
        restaurant_det.city = request.POST.get('city', restaurant_det.city).strip()
        restaurant_det.state = request.POST.get('state', restaurant_det.state).strip()
        restaurant_det.gst_no = request.POST.get('gst_no', restaurant_det.gst_no).strip()
        restaurant_det.pay_name = request.POST.get('pay_name', restaurant_det.pay_name).strip()
        restaurant_det.upi_id = request.POST.get('upi_id', restaurant_det.upi_id).strip()

        # Convert number fields safely
        phone_number = request.POST.get('phone_number', "").strip()
        mobile_number = request.POST.get('mobile_number', "").strip()
        postal_code = request.POST.get('postal_code', "").strip()

        restaurant_det.phone_number = int(phone_number) if phone_number.isdigit() else restaurant_det.phone_number
        restaurant_det.mobile_number = int(mobile_number) if mobile_number.isdigit() else restaurant_det.mobile_number
        restaurant_det.postal_code = int(postal_code) if postal_code.isdigit() else restaurant_det.postal_code

        restaurant_det.save()
        messages.success(request, "Restaurant details updated successfully!")

    return render(request, 'Rest-Admin/update_restaurant.html', {'data': data, 'restaurant': restaurant_det})


def add_staff(request):
    username = request.session.get('username')
    
    if username:
        data = Admins.objects.get(username=username)
        db_name = ensure_database_connection(data.DB_name)          
    else:
        data = None
        db_name = None  

    all_staff = Staff.objects.using(db_name).all() if db_name else None

    if request.method == 'POST':
        print(db_name,'inside post')
        username = request.POST.get('username')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role')

        if password != confirm_password:
            messages.error(request, 'Password mismatch, Please try again.') 

        new_staff = Staff(
            username=username,
            phone_number=phone_number,
            email=email,
            password=password,
            role=role,
            DB_name = data.DB_name
        )
        new_staff.save(using=db_name)  # Save to the correct database

        messages.success(request, 'Staff added')
        return redirect('add_staff')

    return render(request, 'Rest-Admin/add_staff.html', {'data': data, 'all_staff': all_staff})


def edit_staff(request, id):
    username = request.session.get('username')

    if not username:
        return redirect('signin')

    if username:
        data = Admins.objects.get(username=username)
        db_name = ensure_database_connection(data.DB_name)          
    else:
        data = None
        db_name = None  
    
    staff = get_object_or_404(Staff.objects.using(db_name), id=id) if db_name else None     

    if request.method == 'POST':
        edit_username = request.POST.get('edit_username', '').strip()
        edit_phone_number = request.POST.get('edit_phone_number', '').strip()
        edit_email = request.POST.get('edit_email', '').strip()
        edit_role = request.POST.get('edit_role', '').strip()

        if Staff.objects.using(db_name).filter(phone_number=edit_phone_number).exclude(id=id).exists():
            messages.error(request, 'This Phone Number is already in use. Please use a different one.')
            return redirect('add_staff')

        if Staff.objects.using(db_name).filter(email=edit_email).exclude(id=id).exists():
            messages.error(request, 'This Email is already in use. Please use a different one.')
            return redirect('add_staff')

        staff.username = edit_username
        staff.phone_number = edit_phone_number
        staff.email = edit_email
        staff.role = edit_role

        staff.save(using=db_name)
        
        messages.success(request, "Staff details updated successfully.")
        return redirect('add_staff')

    return render(request, 'Rest-Admin/add_staff.html', {'data': data, 'staff': staff})


def delete_staff(request, id):
    username = request.session.get('username')

    if not username:
        return redirect('signin')
    
    if username:
        data = Admins.objects.get(username=username)
        db_name = ensure_database_connection(data.DB_name)          
    else:
        data = None
        db_name = None  

    staff = get_object_or_404(Staff.objects.using(db_name), id=id) if db_name else None 

    staff.delete(using=db_name)
    messages.success(request, "Staff deleted successfully.")
    
    return redirect('add_staff')


def add_category(request):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')
    
    all_rest = Restaurants.objects.all()

    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None

    cat_det = Categories.objects.using(db_name).all() if db_name else None  

    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        
        try:
            code = int(code) if code else None
        except ValueError:
            messages.error(request, 'Invalid Code. Please enter a valid number.')
            return redirect('add_category')

        if cat_det.exists():
            for i in cat_det:
                if i.name.lower() == name.lower():
                    messages.error(request, 'This Category already exists.')
                    return redirect('add_category') 

                if i.code == code:
                    messages.error(request, 'This Code is already in use. Please try a different code.') 
                    return redirect('add_category')  


        new_category = Categories(
            name=name,
            code=code,
            description=description,
            image=image,
            created_at = timezone.now() + timedelta(hours=5, minutes=30),
        )
        new_category.save(using=db_name)  

        messages.success(request, 'Category added successfully.')
        return redirect('add_category')

    return render(request, 'Staff/add_category.html', {'data': data, 'cat_det': cat_det})


def edit_category(request, id):
    username = request.session.get('username')       
    if not username:
        return redirect('signin')  
    all_rest = Restaurants.objects.all()
    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None

    category = get_object_or_404(Categories.objects.using(db_name), id=id)

    cat_det = Categories.objects.using(db_name).exclude(id=id).all() if db_name else None  

    if request.method == 'POST':
        edit_name = request.POST.get('edit_name')
        edit_code = request.POST.get('edit_code')
        edit_description = request.POST.get('edit_description')

        try:
            edit_code = int(edit_code) if edit_code else None
        except ValueError:
            messages.error(request, 'Invalid Code. Please enter a valid number.')
            return redirect('add_category')

        if cat_det.exists():
            for i in cat_det:
                if i.name.lower() == edit_name.lower():
                    messages.error(request, 'This Category already exists.')
                    return redirect('add_category') 

                if i.code == edit_code:
                    messages.error(request, 'This Code is already in use. Please try a different code.') 
                    return redirect('add_category')  

        
        category.name = edit_name
        category.code = edit_code
        category.description = edit_description
        category.updated_at = timezone.now() + timedelta(hours=5, minutes=30)

        if 'edit_image' in request.FILES:
            category.image = request.FILES['edit_image']

        category.save(using=db_name)
        messages.success(request, 'Category updated successfully.')
        return redirect('add_category')

    return render(request, 'Staff/add_category.html', {'data': data, 'category': category})


def delete_category(request, id):
    username = request.session.get('username')
    if not username:
        return redirect('signin')  
    all_rest = Restaurants.objects.all()
    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None

    category = get_object_or_404(Categories.objects.using(db_name), id=id)

    menu_items = MenuItems.objects.using(db_name).filter(category = category.name)
    menu_items.delete()

    category.delete()

    messages.success(request, 'Category deleted successfully.')
    return redirect('add_category')


def add_menuitem(request):
    username = request.session.get('username')
    if not username:
        return redirect('signin')

    all_rest = Restaurants.objects.all()
    db_name = None

    if username:
        for i in all_rest:
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break
            except Exception as e:
                print(f"Error in database {db_name}: {e}")
    else:
        data = None

    cat_det = Categories.objects.using(db_name).all() if db_name else None
    menu_items = MenuItems.objects.using(db_name).all() if db_name else None
    menuitems_det = Menuitems_details.objects.using(db_name).all() if db_name else None

    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        description = request.POST.get('description')
        type = request.POST.get('type')
        image = request.FILES.get('image')

        gst = request.POST.get('gst')
        gst_type = request.POST.get('gst_type')
        hsn_code = request.POST.get('hsn_code')

        # Check if the item already exists
        if menu_items and menu_items.filter(name=name).exists():
            messages.error(request, 'This Item already exists in the menu.')
            return redirect('add_menuitem')

        # Save Menu Item
        new_menuitem = MenuItems(
            name=name,
            category=category,
            description=description,
            type=type,
            image=image,
            available=True,
            created_at=timezone.now() + timedelta(hours=5, minutes=30),

            gst=gst,
            gst_type=gst_type,
            hsn_code=hsn_code,
        )
        new_menuitem.save(using=db_name)

        # Get multiple size & price inputs
        sizes = request.POST.getlist('size')
        table_prices = request.POST.getlist('table_price')
        takeaway_prices = request.POST.getlist('takeaway_price')
        swiggy_prices = request.POST.getlist('swiggy_price')
        zomoto_prices = request.POST.getlist('zomoto_price')

        for size, table_price, takeaway_price, swiggy_price, zomoto_price in zip(sizes, table_prices, takeaway_prices, swiggy_prices, zomoto_prices ):
            Menuitems_details.objects.using(db_name).create(
                name=name,  # No ForeignKey, just using name
                size=size,
                table_price=table_price,
                takeaway_price=takeaway_price,
                swiggy_price=swiggy_price,
                zomoto_price=zomoto_price
            )

        messages.success(request, 'Item added successfully to the Menu.')
        return redirect('add_menuitem')
    
    context=  {'data': data, 'menu_items': menu_items, 'cat_det': cat_det,'menuitems_det':menuitems_det}

    return render(request, 'Staff/add_menuitem.html',context)


def edit_menuitem(request, id):
    username = request.session.get('username')
    if not username:
        return redirect('signin')

    all_rest = Restaurants.objects.all()
    db_name = None

    if username:
        for i in all_rest:
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break
            except Exception as e:
                print(f"Error in database {db_name}: {e}")
    else:
        data = None

    menu_item = get_object_or_404(MenuItems.objects.using(db_name), id=id)
    cat_det = Categories.objects.using(db_name).all()
    menuitems_det = Menuitems_details.objects.using(db_name).filter(name=menu_item.name)

    all_menuitems = MenuItems.objects.using(db_name).exclude(id=id).all() if db_name else None  

    if request.method == 'POST':
        edit_name = request.POST.get('edit_name')
        edit_category = request.POST.get('edit_category')
        edit_description = request.POST.get('edit_description')
        edit_type = request.POST.get('edit_type')
        edit_gst = request.POST.get('edit_gst')
        edit_hsn_code = request.POST.get('edit_hsn_code')

        # Check if menu item with the same name already exists
        if all_menuitems and all_menuitems.filter(name=edit_name).exists():
            messages.error(request, 'This item already exists in the menu.')
            return redirect('add_menuitem')

        # Update Menu Item details
        menu_item.name = edit_name
        menu_item.category = edit_category
        menu_item.description = edit_description
        menu_item.updated_at = timezone.now() + timedelta(hours=5, minutes=30)
        menu_item.type = edit_type
        menu_item.gst = edit_gst
        menu_item.hsn_code = edit_hsn_code

        if 'edit_image' in request.FILES:
            menu_item.image = request.FILES['edit_image']

        menu_item.save(using=db_name)

        # Update Size & Price Details
        existing_size_ids = request.POST.getlist('existing_size_id')  
        sizes = request.POST.getlist('edit_size')  
        table_prices = request.POST.getlist('edit_table_price')  
        takeaway_prices = request.POST.getlist('edit_takeaway_price')  
        swiggy_prices = request.POST.getlist('edit_swiggy_price')  
        zomoto_prices = request.POST.getlist('edit_zomoto_price')  

        # Delete removed size-price pairs
        existing_details = Menuitems_details.objects.using(db_name).filter(name=menu_item.name)
        existing_detail_ids = [str(detail.id) for detail in existing_details]

        for detail in existing_details:
            if str(detail.id) not in existing_size_ids:
                detail.delete()

        for index, (size, table_price, takeaway_price, swiggy_price, zomoto_price) in enumerate(zip(sizes, table_prices, takeaway_prices, swiggy_prices, zomoto_prices)):
            if index < len(existing_size_ids):  # Update existing size-price pairs
                detail = Menuitems_details.objects.using(db_name).filter(id=existing_size_ids[index]).first()
                if detail:
                    detail.size = size
                    detail.table_price = table_price
                    detail.takeaway_price = takeaway_price
                    detail.swiggy_price = swiggy_price
                    detail.zomoto_price = zomoto_price
                    detail.save(using=db_name)
            else:  # Add new size-price pairs
                Menuitems_details.objects.using(db_name).create(
                    name=menu_item.name,
                    size=size,
                    table_price=table_price,
                    takeaway_price=takeaway_price,
                    swiggy_price=swiggy_price,
                    zomoto_price= zomoto_price
                )

        messages.success(request, 'Menu item updated successfully!')
        return redirect('add_menuitem')

    context = {
        'data': data,
        'menu_item': menu_item,
        'menuitems_det': menuitems_det,
        'cat_det': cat_det
    }

    return render(request, 'Staff/add_menuitem.html', context)


def delete_menuitem(request, id):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')     
    all_rest = Restaurants.objects.all()
    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None

    menuitem = get_object_or_404(MenuItems.objects.using(db_name), id=id)
    menuitem_details = Menuitems_details.objects.using(db_name).filter(name=menuitem.name)
    menuitem_details.delete()
    menuitem.delete()

    messages.success(request, 'Menu Item deleted successfully.')
    return redirect('add_menuitem')


def add_table(request):
    username = request.session.get('username')
    if not username:
        return redirect('signin') 
    
    all_rest = Restaurants.objects.all()
    db_name = None
    if username:
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None

    tables = Table_list.objects.using(db_name).all() if db_name else None 

    if request.method == 'POST':
        table_no = request.POST.get('table_no')
        capacity = request.POST.get('capacity')
        image = request.FILES.get('image')  

        if tables and tables.filter(table_no=table_no).exists():
            messages.error(request, 'This table no already exists.')
            return redirect('add_table')

        new_table = Table_list(
            table_no=table_no,
            capacity=capacity,
            image=image,
            available=True,
            created_at=timezone.now() + timedelta(hours=5, minutes=30),
        )
        new_table.save(using=db_name)

        order_url = f"{settings.APP_BASE_URL}/landing_page/?table_no={table_no}"

        qr = qrcode.make(order_url)
        qr_io = BytesIO()
        qr.save(qr_io, format='PNG')

        new_table.qr_code.save(f"{table_no}_qr.png", ContentFile(qr_io.getvalue()), save=True)
        new_table.save(using=db_name)

        messages.success(request, 'Table added successfully.')
        return redirect('add_table')

    return render(request, 'Staff/add_table.html', {'data': data, 'tables': tables})


def view_qr_code(request, id):
    username = request.session.get('username')
    if not username:
        return redirect('signin') 
    all_rest = Restaurants.objects.all()    

    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None
   
    table = get_object_or_404(Table_list.objects.using(db_name), id=id) if db_name else None

    return render(request, 'Staff/view_qr_code.html', {'data': data,'table': table})


def edit_table(request, id):
    username = request.session.get('username')
    if not username:
        return redirect('signin') 
    all_rest = Restaurants.objects.all()    

    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None
   
    table = get_object_or_404(Table_list.objects.using(db_name), id=id) if db_name else None
   
    if request.method == 'POST':
        edit_capacity = request.POST.get('edit_capacity')
                
        table.table_no = table.table_no
        table.capacity = edit_capacity
        table.updated_at = timezone.now() + timedelta(hours=5, minutes=30),        

        if 'edit_image' in request.FILES:
            table.image = request.FILES['edit_image']

        table.save(using=db_name)

        messages.success(request, 'Table Details item updated successfully!')
        return redirect('add_table') 

    return render(request, 'Staff/add_table.html', {'data': data,'table': table})


def delete_table(request, id):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')     
    all_rest = Restaurants.objects.all()

    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None

    table = get_object_or_404(Table_list.objects.using(db_name), id=id) if db_name else None

    table.delete()

    messages.success(request, 'Table deleted successfully.')
    return redirect('add_table')


def generate_order_no():
    now = timezone.now() + timedelta(hours=5, minutes=30) 
    print('Now', now)
    return f"ORD-{now.strftime('%Y%m%d-%H%M%S')}" 


def generate_kot_no():
    now = timezone.now() + timedelta(hours=5, minutes=30) 
    return f"KOT-{now.strftime('%Y%m%d-%H%M%S')}" 


def place_order(request):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')     
    all_rest = Restaurants.objects.all()

    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None             

    tables = Table_list.objects.using(db_name).all() if db_name else None 
    cat_det = Categories.objects.using(db_name).all() if db_name else None 
    all_menuitems = MenuItems.objects.using(db_name).all() if db_name else None  
    menuitems_det = Menuitems_details.objects.using(db_name).all()

    context = {           
        'data': data, 
        'tables': tables, 
        'cat_det': cat_det, 
        'all_menuitems': all_menuitems, 
        'menuitems_det': menuitems_det
    }
    
    if request.method == "POST":
        order_no = generate_order_no()  
        table_no = request.POST.get("table_no") or None
        total_amount = request.POST.get("totalPrice")

        order_type = request.POST.get("order_type")

        no_of_rows = request.POST.get("no_of_rows")

        try:
            new_order = Orders(
                username=username,
                order_no=order_no,
                order_type=order_type, 
                order_date=timezone.now() + timedelta(hours=5, minutes=30),
                status='Pending',
                table_no=table_no if order_type == 'Dine-In' else None,
                total_amount=Decimal(total_amount),
            )
            new_order.save(using=db_name)

            kot_no = generate_kot_no()

            new_kot = KOT(
                kot_no=kot_no,
                order_no=order_no,
                order_type=order_type, 
                table_no=table_no if order_type == 'Dine-In' else None,
                status='Pending',
                created_at=timezone.now() + timedelta(hours=5, minutes=30),
            )

            new_kot.save(using=db_name)

            # Process Order Items
            for i in range(1, int(no_of_rows)+1):
                item_name = request.POST.get(f'item_name_{i}')
                item_size = request.POST.get(f'item_size_{i}')
                quantity = request.POST.get(f'qty_{i}')
                price = request.POST.get(f'price_{i}')

                OrderItems.objects.using(db_name).create(
                    order_no=order_no,
                    menu_item=item_name,
                    size = item_size,
                    quantity=int(quantity),
                    price=Decimal(price)
                )

                KOTItems.objects.using(db_name).create(
                    kot_no=kot_no,
                    order_no=order_no,
                    order_item=item_name,
                    size = item_size,
                    quantity=int(quantity),
                )                                            

            if table_no:
                try:
                    table = Table_list.objects.using(db_name).get(table_no=table_no)
                    table.occupied_order_no = order_no
                    table.status = "Occupied"
                    table.save(using=db_name)
                except Table_list.DoesNotExist:
                    messages.error(request, "Selected table does not exist.")

            messages.success(request, 'Order placed successfully')

            if order_type == 'Takeaway':
                return redirect('takeaway_orders')
            
            if order_type == 'Dine-In':
                return redirect('staff_dashboard')

        except Exception as e:
            messages.error(request, 'Error in while placing order: {e}')

    return render(request, 'Staff/orders.html', context)


def cancel_order(request, order_no):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')     
    all_rest = Restaurants.objects.all()
    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None

    order = Orders.objects.using(db_name).get(order_no=order_no)
    order_items = OrderItems.objects.using(db_name).filter(order_no=order_no)
    kot_det = KOT.objects.using(db_name).get(order_no=order_no)

    if order.order_type == "Dine-In":
        table = Table_list.objects.using(db_name).get(occupied_order_no=order_no)


    order.status = "Cancelled"
    order.table_no = None
    order.save()

    kot_det.status = "Cancelled"
    kot_det.save()

    if order.order_type == "Dine-In":
        table.status = 'Available'
        table.occupied_order_no = None
        table.save()

    messages.success(request, 'Order cancelled successfully.')
    return redirect('all_orders')


def takeaway_orders(request):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')     
    all_rest = Restaurants.objects.all()

    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None 

    takeaway_orders = Orders.objects.using(db_name).filter(order_type='Takeaway').order_by('-id') 

    takeaway_orders_details = OrderItems.objects.using(db_name).all() 

    for order in takeaway_orders:
        order.amount_in_words = convert_amount_to_words(order.total_amount)

    for item in takeaway_orders_details:
        menu_detail = Menuitems_details.objects.using(db_name).filter(name=item.menu_item, size=item.size).first()
        
        # Find the related order for this item
        order = next((j for j in takeaway_orders if j.order_no == item.order_no), None)

        if menu_detail and order:
            if order.order_type == "Dine-In":
                item.base_price = menu_detail.table_price
            elif order.order_type == "Takeaway":
                item.base_price = menu_detail.takeaway_price
            else:
                item.base_price = 0  
        else:
            item.base_price = 0

    pdf_records = bill_pdf.objects.using(db_name).all()

    return render(request, 'Staff/takeaway_orders.html', {'data':data, 'takeaway_orders': takeaway_orders,'takeaway_orders_details':takeaway_orders_details, 'pdf_records':pdf_records})


def all_orders(request):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')  

    all_rest = Restaurants.objects.all()
    db_name = None
    data = None

    if username:
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             

    all_order = Orders.objects.using(db_name).all().order_by('-id') if db_name else None
    orders_details = OrderItems.objects.using(db_name).all()


    # Convert total_amount to words and attach to each order
    for order in all_order:
        order.amount_in_words = convert_amount_to_words(order.total_amount)

    # Calculate total price for each order item
    for item in orders_details:
        menu_detail = Menuitems_details.objects.using(db_name).filter(name=item.menu_item, size=item.size).first()
        
        # Find the related order for this item
        order = next((j for j in all_order if j.order_no == item.order_no), None)

        if menu_detail and order:
            if order.order_type == "Dine-In":
                item.base_price = menu_detail.table_price
            elif order.order_type == "Takeaway":
                item.base_price = menu_detail.takeaway_price
            else:
                item.base_price = 0  # Default if order type doesn't match
        else:
            item.base_price = 0

    completed_orders = Orders.objects.using(db_name).filter(status="Completed")
    pdf_records = bill_pdf.objects.using(db_name).all()

    return render(request, 'Staff/all_orders.html', {'data': data, 'all_order': all_order, 'orders_details':orders_details,'completed_orders':completed_orders,'pdf_records':pdf_records})


def addmore_items(request, order_no):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')     
    all_rest = Restaurants.objects.all()

    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None  
    

    all_menuitems = MenuItems.objects.using(db_name).all() 
    menuitems_det = Menuitems_details.objects.using(db_name).all()
    cat_det = Categories.objects.using(db_name).all() 
    active_orders = Orders.objects.using(db_name).get(order_no=order_no)
    active_orders_details = OrderItems.objects.using(db_name).filter(order_no=order_no) 
     
    KOT_det = KOTItems.objects.using(db_name).filter(order_no=order_no) 
            
    available_tables = Table_list.objects.using(db_name).filter(status='Available')

    active_orders.amount_in_words = convert_amount_to_words(active_orders.total_amount)

    for item in active_orders_details:
        menu_detail = Menuitems_details.objects.using(db_name).filter(name=item.menu_item, size=item.size).first()
        
        if menu_detail:
            if active_orders.order_type == "Dine-In":
                item.base_price = menu_detail.table_price
            elif active_orders.order_type == "Takeaway":
                item.base_price = menu_detail.takeaway_price
            else:
                item.base_price = 0  # Default if order type doesn't match
        else:
            item.base_price = 0 

    if request.method == "POST":
        totalPrice = request.POST.get("totalPrice")  
        no_of_rows = request.POST.get("no_of_rows")                           

        active_orders.status = 'Pending'
        active_orders.total_amount = totalPrice
        active_orders.save()
        
        for i in active_orders_details:
            i.delete()

        kot_no=generate_kot_no()

        new_kot = KOT(
            kot_no=kot_no,
            order_no=order_no,
            order_type=active_orders.order_type, 
            table_no=active_orders.table_no if active_orders.order_type == 'Dine-In' else None, 
            status='Pending',
            created_at=timezone.now() + timedelta(hours=5, minutes=30),
        )

        new_kot.save(using=db_name)

        for i in range(1, int(no_of_rows)+1):
            item_name = request.POST.get(f'item_name_{i}')
            item_size = request.POST.get(f'item_size_{i}')
            quantity = request.POST.get(f'qty_{i}')
            price = request.POST.get(f'price_{i}')  

            OrderItems.objects.using(db_name).create(
                order_no=order_no,
                menu_item=item_name,
                size = item_size,
                quantity=int(quantity),
                price=Decimal(price)
            )

            try:
                KOT_item_ = KOTItems.objects.using(db_name).filter(order_no=order_no, order_item=item_name, size=item_size) 
            except:
                KOT_item_ = None
            
            if KOT_item_:
                total_qty = 0
                for i in KOT_item_:
                    total_qty = total_qty + int(i.quantity)

                new_qty = int(quantity) - int(total_qty)
                if new_qty >= int(1):
                    KOTItems.objects.using(db_name).create(
                        kot_no=kot_no,
                        order_no=order_no,
                        order_item=item_name,
                        size = item_size,
                        quantity=int(new_qty),
                    )
            else:
                KOTItems.objects.using(db_name).create(
                    kot_no=kot_no,
                    order_no=order_no,
                    order_item=item_name,
                    size = item_size,
                    quantity=int(quantity),
                )
           
        messages.success(request, 'Order Updated successfully')
        if active_orders.order_type == 'Takeaway':
                return redirect('takeaway_orders')
            
        if active_orders.order_type == 'Dine-In':
            return redirect('staff_dashboard') 
    
    context = {
        'data': data, 
        'active_orders': active_orders, 
        'active_orders_details': active_orders_details,
        'all_menuitems': all_menuitems,
        'menuitems_det': menuitems_det,
        'cat_det': cat_det,
        'available_tables':available_tables,
    }

    return render(request, 'Staff/addmore_items.html', context)


def kot_management(request):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')     
    all_rest = Restaurants.objects.all()

    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None  

    all_kot = KOT.objects.using(db_name).all().order_by('-id')if db_name else None    
    kot_det = KOTItems.objects.using(db_name).all()   

    if request.method == "POST":
        kot_id = request.POST.get("kot_id")
        if kot_id:
            try:
                kot_entry = KOT.objects.using(db_name).get(id=kot_id)
                kot_entry.status = "Ready"
                kot_entry.save(using=db_name) 

                order_entry = Orders.objects.using(db_name).get(order_no=kot_entry.order_no)
                if order_entry:

                    if order_entry.order_type == 'Dine-In':
                        order_entry.status = "Served"
                    else:    
                        order_entry.status = "Ready for Pickup"

                    order_entry.save(using=db_name)

                messages.success(request, 'The items Ready To Served')
                return redirect('kot_management')  
            except Exception as e:
                print(f"Error updating status: {e}")

    return render(request, 'Staff/kot_management.html', {'data': data, 'all_kot': all_kot, 'kot_det': kot_det})


from num2words import num2words 
def convert_amount_to_words(amount):
    try:
        amount = float(amount)  
        amount = int(amount) 
        words = num2words(amount, lang='en') 
        words = words.replace(",", "") 
        return words.capitalize() + " only"  
    except Exception as e:
        print(f"Error converting amount to words: {e}")
        return ""

import qrcode
import io
import os
from decimal import Decimal
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from xhtml2pdf import pisa

def generate_order_pdf(request, order_no):
    username = request.session.get('username')
    if not username:
        return redirect('signin')

    all_rest = Restaurants.objects.all()
    
    for i in all_rest:
        try:
            db_name = ensure_database_connection(i.DB_name)
            restaurant_name = i.name
            break
        except Exception as e:
            print(f"Error in database {db_name}: {e}")
            return HttpResponse("Database connection error", status=500)

    try:
        order = Orders.objects.using(db_name).get(order_no=order_no)
        order_items = OrderItems.objects.using(db_name).filter(order_no=order_no)

        restaurant_det = Restaurants.objects.get(DB_name=db_name)

        if order.order_type == "Dine-In":
            table = Table_list.objects.using(db_name).get(occupied_order_no=order_no)

        total_tax = 0  
        taxable_amount = 0  

        for item in order_items:
            menu_detail = Menuitems_details.objects.using(db_name).filter(name=item.menu_item).first()
            menu_item = MenuItems.objects.using(db_name).filter(name=item.menu_item).first()

            if menu_detail and menu_item:
                if order.order_type == "Dine-In":
                    base_price = Decimal(menu_detail.table_price)
                elif order.order_type == "Takeaway":
                    base_price = Decimal(menu_detail.takeaway_price)
                else:
                    base_price = 0  

                gst_str = menu_item.gst.strip().replace('%', '') 
                gst_rate = Decimal(gst_str) / Decimal(100)   
                gst_type = menu_item.gst_type
                item_tax = 0


                if gst_type == "Exclusive":
                    item_tax = round(base_price * gst_rate, 2)
                    actual_price = base_price * item.quantity  
                    item.base_price = base_price  

                elif gst_type == "Inclusive":
                    base_price_without_tax = round((base_price / (1 + gst_rate)), 2)
                    item_tax = round(base_price - base_price_without_tax, 2)
                    actual_price = base_price_without_tax * item.quantity  
                    item.base_price = base_price_without_tax  

                total_tax += item_tax * item.quantity  
                taxable_amount += actual_price  

                item.tax_amount = item_tax
                item.actual_price = actual_price  

        cgst = total_tax / 2
        sgst = total_tax / 2
        order_total_amount = taxable_amount + total_tax  
        order.amount_in_words = convert_amount_to_words(order_total_amount)

        # **Generate UPI QR Code**
        upi_id = restaurant_det.upi_id 
        payee_name = restaurant_name  
        upi_url = f"upi://pay?pa={upi_id}&pn={payee_name}&am={order_total_amount}&cu=INR"

        qr = qrcode.make(upi_url)
        qr_buffer = io.BytesIO()
        qr.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        # **Convert QR to Base64 for PDF Embedding**
        import base64
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()

        template_path = 'Staff/order_pdf.html'
        context = {
            'order': order,
            'order_items': order_items,
            'restaurant_name': restaurant_name,
            'total_tax': total_tax,
            'cgst': cgst,
            'sgst': sgst,
            'taxable_amount': taxable_amount,
            'order_total_amount': order_total_amount,
            'item_tax': item_tax,
            'qr_code': qr_base64  # **Pass QR code as Base64**
        }

        max_height_per_item = 30  
        base_height = 200  
        order_item_count = order_items.count()
        total_height = base_height + (order_item_count * max_height_per_item)

        if total_height < 600:
            total_height = 600

        css_override = f"""
            @page {{
                size: 80mm {total_height}pt;
                margin: 0;
            }}
        """

        template = get_template(template_path)
        html = template.render(context)
        html = f"<style>{css_override}</style>" + html

        pdf_buffer = io.BytesIO()
        
        pisa_status = pisa.CreatePDF(html, dest=pdf_buffer, encoding='UTF-8')

        if pisa_status.err:
            return HttpResponse("Error generating PDF", status=500)

        pdf_buffer.seek(0)

        pdf_filename = f"{order_no}.pdf"
        pdf_path = os.path.join(settings.MEDIA_ROOT, "bills", pdf_filename)

        with open(pdf_path, "wb") as f:
            f.write(pdf_buffer.getvalue())

        transaction_id = generate_transaction_no()

        bill_pdf.objects.using(db_name).create(
            order_no=order_no,
            transaction_id=transaction_id,
            file_name=pdf_filename,
            pdf_file=f"bills/{pdf_filename}",
            datetime=timezone.now() + timedelta(hours=5, minutes=30)
        )

        Payments.objects.using(db_name).create(
            order_no=order_no,
            payment_method="Cash",
            payment_status="Completed",
            transaction_id=transaction_id,
            total_amount=order.total_amount + total_tax
        )

        order.status = "Completed"
        order.save()

        if order.order_type == "Dine-In":
            table.status = 'Available'
            table.occupied_order_no = None
            table.save()

        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{pdf_filename}"'

        return response

    except Orders.DoesNotExist:
        return HttpResponse("Order not found", status=404)


def generate_transaction_no():
    """Generate a unique transaction number based on timestamp."""
    current_time = timezone.now() + timedelta(hours=5, minutes=30) 
    return f"Trans-{current_time.strftime('%d%m%Y-%H%M%S')}"


def bill_generate(request):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')     

    all_rest = Restaurants.objects.all()
    db_name = None

    # Find staff's database connection
    for i in all_rest:            
        try:
            db_name = ensure_database_connection(i.DB_name)
            data = Staff.objects.using(db_name).get(username=username)
            break  
        except Exception as e:
            print(f"Error in database {db_name}: {e}")             

    if not db_name:
        messages.error(request, "Could not connect to the database.")
        return redirect('active_orders')

    order_no = request.GET.get('order_no', None)

    if order_no:
        try:
            order = Orders.objects.using(db_name).get(order_no=order_no)
            order_items = OrderItems.objects.using(db_name).filter(order_no=order_no)
        except Orders.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect('active_orders')
    else:
        order = None
        order_items = None

    completed_orders = Orders.objects.using(db_name).filter(status="Completed")
    pdf_records = bill_pdf.objects.using(db_name).all()

    if order_no:
        pdf_records = pdf_records.filter(order_no=order_no)

    return render(request, 'staff/bill_page.html', {'data': data,'order': order,'order_items': order_items,'completed_orders': completed_orders,'pdf_records': pdf_records})


def pending_kots(request):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')     

    all_rest = Restaurants.objects.all()
    db_name = None
    data = None

    for i in all_rest:            
        try:
            db_name = ensure_database_connection(i.DB_name)
            data = Staff.objects.using(db_name).get(username=username)
            break  
        except Exception as e:
            print(f"Error connecting to database {i.DB_name}: {e}")   

    if not db_name:
        messages.error(request, "Could not connect to any restaurant database.")
        return redirect('signin')

    pending_kots = KOT.objects.using(db_name).filter(status='Pending').order_by('-id')    
    kot_items = KOTItems.objects.using(db_name).all()   

    if request.method == "POST":
        kot_id = request.POST.get("kot_id")
        if kot_id:
            try:
                kot_entry = KOT.objects.using(db_name).get(id=kot_id)
                kot_entry.status = "Ready"
                kot_entry.save(using=db_name) 

                order_entry = Orders.objects.using(db_name).get(order_no=kot_entry.order_no)
                if order_entry:
                    
                    if order_entry.order_type == 'Dine-In':
                        order_entry.status = "Served"  
                    elif order_entry.order_type == 'Qr-Dine-In':
                        order_entry.status = "Completed"  
                    else:
                        order_entry.status = "Ready for Pickup"

                    order_entry.save(using=db_name)

                messages.success(request, 'The items are Ready to be Served')
                return redirect('pending_kots')  
            except Exception as e:
                messages.error(request, f"Error updating status: {e}")

    return render(request, 'Staff/pending_kots.html', {'data': data,'pending_kots': pending_kots,'kot_items': kot_items })

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def shift_table(request, order_no, new_table_no):
    username = request.session.get('username') 
    if not username:
        messages.error(request, "User not authenticated. Please log in.")
        return redirect('signin')

    db_name = None
    all_rest = Restaurants.objects.all()

    for restaurant in all_rest:
        try:
            db_name = ensure_database_connection(restaurant.DB_name)
            data = Staff.objects.using(db_name).get(username=username)
            break  
        except Exception as e:
            print(f"Error in database {restaurant.DB_name}: {e}")             

    if not db_name:
        messages.error(request, "Database connection failed.")
        return redirect('add_more_items_page')

    if request.method == "POST":
        try:
            order = Orders.objects.using(db_name).get(order_no=order_no)

            if order.order_type != 'Dine-In':
                messages.error(request, "Table shifting is only for Dine-In orders.")
                return redirect('add_more_items_page')

            previous_table_no = order.table_no  

            if previous_table_no:
                try:
                    prev_table = Table_list.objects.using(db_name).get(table_no=previous_table_no)
                    prev_table.status = 'Available'
                    prev_table.occupied_order_no = None  
                    prev_table.save(using=db_name)
                except Table_list.DoesNotExist:
                    pass  

            try:
                new_table = Table_list.objects.using(db_name).get(table_no=new_table_no)
                if new_table.status == 'Occupied':
                    messages.error(request, "Selected table is already occupied.")
                    return redirect('addmore_items')
                
                new_table.status = 'Occupied'
                new_table.occupied_order_no = order_no  
                new_table.save(using=db_name)

            except Table_list.DoesNotExist:
                messages.error(request, "New table not found.")
                return redirect('addmore_items')

            # Update order with new table number
            order.table_no = new_table_no
            order.save(using=db_name)

            messages.success(request, f"Order {order_no} moved to table {new_table_no}.")
            return redirect('addmore_items')

        except Orders.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect('addmore_items')
    
    messages.error(request, "Invalid request method.")
    return redirect('addmore_items')


def waiter_place_order(request):
    username = request.session.get('username')
    if not username:
        return redirect('signin')

    all_rest = Restaurants.objects.all()
    data = None
    db_name = None

    for i in all_rest:
        try:
            db_name = ensure_database_connection(i.DB_name)
            data = Staff.objects.using(db_name).get(username=username)
            break
        except Exception as e:
            print(f"Error in database {i.DB_name}: {e}")

    tables = Table_list.objects.using(db_name).all() if db_name else None
    cat_det = Categories.objects.using(db_name).all() if db_name else None
    all_menuitems = MenuItems.objects.using(db_name).all() if db_name else None
    menuitems_det = Menuitems_details.objects.using(db_name).all() if db_name else None

    context = {
        'data': data,
        'tables': tables,
        'cat_det': cat_det,
        'all_menuitems': all_menuitems,
        'menuitems_det': menuitems_det,
    }

    if request.method == "POST":
        order_no = generate_order_no()
        table_no = request.POST.get("table_no")
        total_amount = request.POST.get("totalPrice")
        no_of_rows = request.POST.get("no_of_rows") or request.POST.get("no_of_rows_modal")

        try:
            new_order = Orders(
                username=username,
                order_no=order_no,
                order_type='Dine-In',
                order_date=timezone.now() + timedelta(hours=5, minutes=30),
                status='Pending',
                table_no=table_no,
                total_amount=Decimal(total_amount),
            )
            new_order.save(using=db_name)

            kot_no = generate_kot_no()
            new_kot = KOT(
                kot_no=kot_no,
                order_no=order_no,
                order_type='Dine-In',
                table_no=table_no,
                status='Pending',
                created_at=timezone.now() + timedelta(hours=5, minutes=30),
            )
            new_kot.save(using=db_name)

            for i in range(1, int(no_of_rows) + 1):
                item_name = request.POST.get(f'item_name_{i}')
                item_size = request.POST.get(f'item_size_{i}')
                quantity = request.POST.get(f'qty_{i}')
                price = request.POST.get(f'price_{i}')

                if item_name and quantity and price:
                    OrderItems.objects.using(db_name).create(
                        order_no=order_no,
                        menu_item=item_name,
                        size=item_size,
                        quantity=int(quantity),
                        price=Decimal(price)
                    )
                    KOTItems.objects.using(db_name).create(
                        kot_no=kot_no,
                        order_no=order_no,
                        order_item=item_name,
                        size=item_size,
                        quantity=int(quantity),
                    )

            if table_no:
                try:
                    table = Table_list.objects.using(db_name).get(table_no=table_no)
                    table.occupied_order_no = order_no
                    table.status = "Occupied"
                    table.save(using=db_name)
                except Table_list.DoesNotExist:
                    messages.error(request, "Selected table does not exist.")

            messages.success(request, 'Order placed successfully')
            return redirect('staff_dashboard')

        except Exception as e:
            messages.error(request, f'Error while placing order: {e}')

    return render(request, 'Waiter/waiter_order.html', context)


def w_addmore_items(request, order_no):
    username = request.session.get('username') 
    if not username:
        return redirect('signin')     
    all_rest = Restaurants.objects.all()

    if username:         
        for i in all_rest:            
            try:
                db_name = ensure_database_connection(i.DB_name)
                data = Staff.objects.using(db_name).get(username=username)
                break  
            except Exception as e:
                print(f"Error in database {db_name}: {e}")             
    else:
        data = None  
    

    all_menuitems = MenuItems.objects.using(db_name).all() 
    menuitems_det = Menuitems_details.objects.using(db_name).all()
    cat_det = Categories.objects.using(db_name).all() 
    active_orders = Orders.objects.using(db_name).get(order_no=order_no)
    active_orders_details = OrderItems.objects.using(db_name).filter(order_no=order_no) 
     
    KOT_det = KOTItems.objects.using(db_name).filter(order_no=order_no) 
            
    available_tables = Table_list.objects.using(db_name).filter(status='Available')

    active_orders.amount_in_words = convert_amount_to_words(active_orders.total_amount)

    for item in active_orders_details:
        menu_detail = Menuitems_details.objects.using(db_name).filter(name=item.menu_item, size=item.size).first()
        
        if menu_detail:
            if active_orders.order_type == "Dine-In":
                item.base_price = menu_detail.table_price
            elif active_orders.order_type == "Takeaway":
                item.base_price = menu_detail.takeaway_price
            else:
                item.base_price = 0  # Default if order type doesn't match
        else:
            item.base_price = 0 

    if request.method == "POST":
        totalPrice = request.POST.get("totalPrice")  
        no_of_rows = request.POST.get("no_of_rows")                           

        active_orders.status = 'Pending'
        active_orders.total_amount = totalPrice
        active_orders.save()
        
        for i in active_orders_details:
            i.delete()

        kot_no=generate_kot_no()

        new_kot = KOT(
            kot_no=kot_no,
            order_no=order_no,
            order_type=active_orders.order_type, 
            table_no=active_orders.table_no if active_orders.order_type == 'Dine-In' else None, 
            status='Pending',
            created_at=timezone.now() + timedelta(hours=5, minutes=30),
        )

        new_kot.save(using=db_name)

        for i in range(1, int(no_of_rows)+1):
            item_name = request.POST.get(f'item_name_{i}')
            item_size = request.POST.get(f'item_size_{i}')
            quantity = request.POST.get(f'qty_{i}')
            price = request.POST.get(f'price_{i}')  

            OrderItems.objects.using(db_name).create(
                order_no=order_no,
                menu_item=item_name,
                size = item_size,
                quantity=int(quantity),
                price=Decimal(price)
            )

            try:
                KOT_item_ = KOTItems.objects.using(db_name).filter(order_no=order_no, order_item=item_name, size=item_size) 
            except:
                KOT_item_ = None
            
            if KOT_item_:
                total_qty = 0
                for i in KOT_item_:
                    total_qty = total_qty + int(i.quantity)

                new_qty = int(quantity) - int(total_qty)
                if new_qty >= int(1):
                    KOTItems.objects.using(db_name).create(
                        kot_no=kot_no,
                        order_no=order_no,
                        order_item=item_name,
                        size = item_size,
                        quantity=int(new_qty),
                    )
            else:
                KOTItems.objects.using(db_name).create(
                    kot_no=kot_no,
                    order_no=order_no,
                    order_item=item_name,
                    size = item_size,
                    quantity=int(quantity),
                )
           
        messages.success(request, 'Order Updated successfully')
        return redirect('staff_dashboard') 
    
    context = {
        'data': data, 
        'active_orders': active_orders, 
        'active_orders_details': active_orders_details,
        'all_menuitems': all_menuitems,
        'menuitems_det': menuitems_det,
        'cat_det': cat_det,
        'available_tables':available_tables,
    }

    return render(request, 'Waiter/w_addmore_items.html', context)


import json
from django.utils.safestring import mark_safe

def self_order(request):
    all_rest = Restaurants.objects.all()
    db_name = None

    for i in all_rest:
        try:
            db_name = ensure_database_connection(i.DB_name)
            restaurant_name = i.name
            break
        except Exception as e:
            print(f"Error in database {db_name}: {e}")
            return HttpResponse("Database connection error", status=500)

    table_no = request.GET.get('table_no')
    username = request.GET.get('username')

    cat_det = Categories.objects.using(db_name).all() if db_name else None
    all_menuitems = MenuItems.objects.using(db_name).all() if db_name else None
    menuitems_det = Menuitems_details.objects.using(db_name).all() if db_name else None

    gst_details = {
        item.name: {
            'gst_rate': float(item.gst.replace('%', '')) / 100 if item.gst else 0,
            'gst_type': item.gst_type or 'Exclusive'
        } for item in all_menuitems
    }

    menu_details = {}
    for detail in menuitems_det:
        item_name = detail.name

        if item_name not in menu_details:
            menu_details[item_name] = []

        menu_details[item_name].append({
            'size': detail.size,
            'table_price': float(detail.table_price),
        })

    context = {
        'cat_det': cat_det,
        'all_menuitems': all_menuitems,
        'menu_details_json': mark_safe(json.dumps(menu_details)),
        'gst_details_json': mark_safe(json.dumps(gst_details)),
        'table_no': table_no,
        'username': username,
    }

    return render(request, 'Customer/self_order2.html', context)


def landing_page(request):
    all_rest = Restaurants.objects.all()
    db_name = None

    for i in all_rest:
        try:
            db_name = ensure_database_connection(i.DB_name)
            restaurant_name = i.name
            break
        except Exception as e:
            print(f"Error in database {db_name}: {e}")
            return HttpResponse("Database connection error", status=500)

    table_no = request.GET.get('table_no') 

    return render(request, 'Customer/landing_page.html', {'table_no':table_no, 'restaurant_name':restaurant_name})


import traceback 

def qr_orders(request):
    table_no = request.GET.get('table_no') 
    username = request.GET.get('username') 

    if not table_no or not username:
        messages.error(request, "Missing table number or username.")
        return redirect(f'/self_order/?table_no={table_no}&username={username}')  

    db_name = None
    all_rest = Restaurants.objects.all()

    for i in all_rest:
        try:
            db_name = ensure_database_connection(i.DB_name)
            break
        except Exception as e:
            print(f"Error in database {db_name}: {e}")
            return HttpResponse("Database connection error", status=500)

    if not db_name:
        messages.error(request, "Unable to connect to any restaurant database.")
        return redirect(f'/self_order/?table_no={table_no}&username={username}')

    cat_det = Categories.objects.using(db_name).all()
    all_menuitems = MenuItems.objects.using(db_name).all()
    menuitems_det = Menuitems_details.objects.using(db_name).all()

    context = {
        'cat_det': cat_det,
        'all_menuitems': all_menuitems,
        'menuitems_det': menuitems_det,
        'table_no': table_no,
        'username': username,
    }

    if request.method == "POST":
        try:
            order_no = generate_order_no()
            total_amount = request.POST.get("totalPrice", "0")
            no_of_rows = int(request.POST.get("no_of_rows", "0"))

            new_order = Orders(
                username=username,
                order_no=order_no,
                order_type='Qr-Dine-In',
                order_date=timezone.now() + timedelta(hours=5, minutes=30),
                status='Pending',
                table_no=table_no,
                total_amount=Decimal(total_amount),
            )
            new_order.save(using=db_name)

            kot_no = generate_kot_no()
            new_kot = KOT(
                kot_no=kot_no,
                order_no=order_no,
                order_type='Qr-Dine-In',
                table_no=table_no,
                status='Pending',
                created_at=timezone.now() + timedelta(hours=5, minutes=30),
            )
            new_kot.save(using=db_name)

            for i in range(1, no_of_rows + 1):
                item_name = request.POST.get(f'item_name_{i}')
                item_size = request.POST.get(f'item_size_{i}')
                quantity = request.POST.get(f'qty_{i}', 0)
                price = request.POST.get(f'price_{i}', 0)

                if item_name and item_size and quantity and price:
                    OrderItems.objects.using(db_name).create(
                        order_no=order_no,
                        menu_item=item_name,
                        size=item_size,
                        quantity=int(quantity),
                        price=Decimal(price)
                    )

                    KOTItems.objects.using(db_name).create(
                        kot_no=kot_no,
                        order_no=order_no,
                        order_item=item_name,
                        size=item_size,
                        quantity=int(quantity)
                    )

            transaction_id = generate_transaction_no()
            pdf_filename = f"{order_no}_bill.pdf"

            bill_pdf.objects.using(db_name).create(
                order_no=order_no,
                transaction_id=transaction_id,
                file_name=pdf_filename,
                pdf_file=f"bills/{pdf_filename}",
                datetime=timezone.now() + timedelta(hours=5, minutes=30),
            )

            Payments.objects.using(db_name).create(
                order_no=order_no,
                payment_method="Cash",
                payment_status="Completed",
                transaction_id=transaction_id,
                total_amount=total_amount
            )   

            messages.success(request, 'Order placed successfully.')
            return redirect(f'/confirm_page/?table_no={table_no}&username={username}&order_no={order_no}')

        except Exception as e:
            print("Exception occurred while placing QR order:")
            print(traceback.format_exc())
            messages.error(request, f"Error while placing order: {e}")
            return redirect(f'/self_order/?table_no={table_no}&username={username}')

    return render(request, 'Customer/self_order2.html', context)


def confirm_page(request):
    all_rest = Restaurants.objects.all()
    db_name = None

    for i in all_rest:
        try:
            db_name = ensure_database_connection(i.DB_name)
            restaurant_name = i.name
            break
        except Exception as e:
            print(f"Error in database {db_name}: {e}")
            return HttpResponse("Database connection error", status=500)

    table_no = request.GET.get('table_no') 
    username = request.GET.get('username')
    order_no = request.GET.get('order_no')

    return render(request, 'Customer/confirm_page.html', {
        'table_no': table_no,
        'username': username,
        'restaurant_name': restaurant_name,
        'order_no':order_no,
    })


def generate_order_bill(request, order_no):

    all_rest = Restaurants.objects.all()
    
    for i in all_rest:
        try:
            db_name = ensure_database_connection(i.DB_name)
            restaurant_name = i.name
            break
        except Exception as e:
            print(f"Error in database {db_name}: {e}")
            return HttpResponse("Database connection error", status=500)

    try:
        order = Orders.objects.using(db_name).get(order_no=order_no)
        order_items = OrderItems.objects.using(db_name).filter(order_no=order_no)

        restaurant_det = Restaurants.objects.get(DB_name=db_name)

        total_tax = 0  
        taxable_amount = 0  

        for item in order_items:
            menu_detail = Menuitems_details.objects.using(db_name).filter(name=item.menu_item).first()
            menu_item = MenuItems.objects.using(db_name).filter(name=item.menu_item).first()

            if menu_detail and menu_item:
                if order.order_type == "Qr-Dine-In":
                    base_price = Decimal(menu_detail.table_price) 

                gst_str = menu_item.gst.strip().replace('%', '') 
                gst_rate = Decimal(gst_str) / Decimal(100)   
                gst_type = menu_item.gst_type
                item_tax = 0 

                if gst_type == "Exclusive":
                    item_tax = round(base_price * gst_rate, 2)
                    actual_price = base_price * item.quantity  
                    item.base_price = base_price  

                elif gst_type == "Inclusive":
                    base_price_without_tax = round((base_price / (1 + gst_rate)), 2)
                    item_tax = round(base_price - base_price_without_tax, 2)
                    actual_price = base_price_without_tax * item.quantity  
                    item.base_price = base_price_without_tax  

                total_tax += item_tax * item.quantity  
                taxable_amount += actual_price  

                item.tax_amount = item_tax
                item.actual_price = actual_price  

        cgst = total_tax / 2
        sgst = total_tax / 2
        order_total_amount = taxable_amount + total_tax  
        order.amount_in_words = convert_amount_to_words(order_total_amount)


        template_path = 'Customer/bill_view.html'
        context = {
            'order': order,
            'order_items': order_items,
            'restaurant_name': restaurant_name,
            'total_tax': total_tax,
            'cgst': cgst,
            'sgst': sgst,
            'taxable_amount': taxable_amount,
            'order_total_amount': order_total_amount,
            'item_tax': item_tax,
        }

        max_height_per_item = 30  
        base_height = 200  
        order_item_count = order_items.count()
        total_height = base_height + (order_item_count * max_height_per_item)

        if total_height < 600:
            total_height = 600

        css_override = f"""
            @page {{
                size: 80mm {total_height}pt;
                margin: 0;
            }}
        """

        template = get_template(template_path)
        html = template.render(context)
        html = f"<style>{css_override}</style>" + html

        pdf_buffer = io.BytesIO()
        
        pisa_status = pisa.CreatePDF(html, dest=pdf_buffer, encoding='UTF-8')

        if pisa_status.err:
            return HttpResponse("Error generating PDF", status=500)

        pdf_buffer.seek(0)

        pdf_filename = f"{order_no}.pdf"
        pdf_path = os.path.join(settings.MEDIA_ROOT, "bills", pdf_filename)

        if not os.path.exists(pdf_path):
            with open(pdf_path, "wb") as f:
                f.write(pdf_buffer.getvalue())

    
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'  

        return response


    except Orders.DoesNotExist:
        return HttpResponse("Order not found", status=404)
    



