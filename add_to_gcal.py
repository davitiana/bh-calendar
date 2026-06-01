#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime, date
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
CALENDAR_FILE = "november_calendar.json"

CALENDAR_ID = "primary"  # use "primary" for your main calendar


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


def make_event(entry, event_title):
    event_date = entry["date"]  # "2025-11-03"
    return {
        "summary": event_title,
        "start": {"date": event_date},
        "end": {"date": event_date},
    }


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"ERROR: {CREDENTIALS_FILE} not found.")
        print("Download it from Google Cloud Console → APIs & Services → Credentials.")
        return

    with open(CALENDAR_FILE) as f:
        calendar = json.load(f)

    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    created = 0
    skipped = 0
    for entry in calendar:
        if not entry["events"]:
            skipped += 1
            continue
        for event_title in entry["events"]:
            event_body = make_event(entry, event_title)
            result = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
            print(f"Created: {entry['date']} — {event_title}")
            created += 1

    print(f"\nDone. {created} event(s) added, {skipped} day(s) had no events.")


if __name__ == "__main__":
    main()
