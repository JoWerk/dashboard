import os
import calendar
import pytz
from datetime import datetime, date
from django.shortcuts import render, redirect
from django.conf import settings
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_google_client_config():
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "project_id": settings.GOOGLE_PROJECT_ID,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": ["http://localhost:8000/google/callback/"]
        }
    }


def home(request):
    # 1. Pull settings and handle Timezone
    SELECTED_CALENDARS = getattr(settings, 'DASHBOARD_CALENDARS', [])
    user_tz = pytz.timezone('America/Phoenix')
    now_local = datetime.now(user_tz)
    today = now_local.date()

    # 2. Setup Calendar Grid (Sunday Start)
    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdatescalendar(today.year, today.month)

    events_by_day = {}

    # 3. Fetch from Google
    token_path = os.path.join(settings.BASE_DIR, 'token.json')
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            # Handle token refresh if expired
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            service = build('calendar', 'v3', credentials=creds)

            # Range for visible grid
            time_min = datetime.combine(month_days[0][0], datetime.min.time()).isoformat() + 'Z'
            time_max = datetime.combine(month_days[-1][-1], datetime.max.time()).isoformat() + 'Z'

            calendar_list = service.calendarList().list().execute()

            for entry in calendar_list.get('items', []):
                if entry.get('summary') in SELECTED_CALENDARS:
                    events_res = service.events().list(
                        calendarId=entry['id'], timeMin=time_min, timeMax=time_max,
                        singleEvents=True, orderBy='startTime'
                    ).execute()

                    for event in events_res.get('items', []):
                        raw_start = event['start'].get('dateTime') or event['start'].get('date')
                        clean_date = raw_start[:10]
                        
                        cal_name = entry.get('summary', '')
                        img = None
                        # Default color if not found
                        color = entry.get('backgroundColor', '#3d92ff') 
                        
                        if 'Cayden' in cal_name:
                            img = 'cayden.png'
                            color = '#f59e0b'
                        elif 'Jenna' in cal_name:
                            img = 'jenna.png'
                            color = '#ec4899'
                        elif 'Steph' in cal_name:
                            img = 'steph.png'
                            color = '#a855f7'
                        elif 'Josh' in cal_name:
                            img = 'josh.png'
                            color = '#3d92ff'
                        elif 'Werkau' in cal_name:
                            img = None # No image for Werkau
                            color = '#10b981'
                        
                        event['color'] = color
                        if img:
                            event['image'] = f'images/{img}'
                        else:
                            event['image'] = None

                        # 12-Hour Time & Duration Logic
                        if 'dateTime' in event['start']:
                            start_dt = datetime.fromisoformat(raw_start.replace('Z', '+00:00')).astimezone(user_tz)
                            event['display_time'] = start_dt.strftime('%I:%M %p').lstrip('0')

                            # Calculate Duration for sidebar
                            if 'end' in event:
                                end_raw = event['end'].get('dateTime')
                                if end_raw:
                                    end_dt = datetime.fromisoformat(end_raw.replace('Z', '+00:00')).astimezone(user_tz)
                                    diff = end_dt - start_dt
                                    hrs, rem = divmod(diff.seconds, 3600)
                                    mins = rem // 60
                                    event['duration'] = f"{hrs}h {mins}m" if hrs > 0 else f"{mins} min"

                        if clean_date not in events_by_day:
                            events_by_day[clean_date] = []
                        events_by_day[clean_date].append(event)
        except Exception as e:
            print(f"Sync Error: {e}")

    # 4. Build Grid Data
    calendar_grid = []
    for week in month_days:
        week_data = []
        for day in week:
            day_str = day.strftime('%Y-%m-%d')
            week_data.append({
                'day_num': day.day,
                'is_today': day == today,
                'is_current_month': day.month == today.month,
                'events': events_by_day.get(day_str, [])
            })
        calendar_grid.append(week_data)

    context = {
        'status': 'System Online',
        'month_name': today.strftime('%B %Y'),
        'weeks': calendar_grid,
        'week_count': len(calendar_grid),
        'day_names': ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'],
        'today_events': events_by_day.get(today.strftime('%Y-%m-%d'), []),
        'today_date': today,
    }
    return render(request, 'dashboard/index.html', context)


def google_login(request):
    client_config = get_google_client_config()
    flow = google_auth_oauthlib.flow.Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = 'http://localhost:8000/google/callback/'
    auth_url, state = flow.authorization_url(access_type='offline', prompt='consent')
    request.session['state'] = state
    return redirect(auth_url)


def google_callback(request):
    state = request.session.get('state')
    client_config = get_google_client_config()
    flow = google_auth_oauthlib.flow.Flow.from_client_config(client_config, scopes=SCOPES, state=state)
    flow.redirect_uri = 'http://localhost:8000/google/callback/'
    flow.fetch_token(authorization_response=request.get_full_path())
    with open('token.json', 'w') as token:
        token.write(flow.credentials.to_json())
    return redirect('home')