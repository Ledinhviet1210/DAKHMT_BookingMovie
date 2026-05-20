from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .forms import RegisterForm, LoginForm
from .models import Booking, Ticket, Showtime

from .app_views.manage_views import *
from .app_views.staff_views import *
from .app_views.ticket_views import *
from .app_views.booking_views import *
from .app_views.payment_views import *
from .app_views.public_views import *
from .app_views.auth_views import *
from .app_views.dashboard_views import *






