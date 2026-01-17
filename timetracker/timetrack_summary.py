#!/usr/bin/env python3
"""
timetrack_summary.py - summarize time tracking data
"""

import sys
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# try to use zoneinfo (Python 3.9+), fallback to pytz
try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        from dateutil.tz import gettz
        ZoneInfo = lambda name: gettz(name)
    except ImportError:
        import pytz
        ZoneInfo = lambda name: pytz.timezone(name)

EASTERN = ZoneInfo('America/New_York')
UTC = ZoneInfo('UTC')

DATA_DIR = Path.home() / "notes" / "_data" / "timetracker"
LOG_FILE = DATA_DIR / "log"
CURRENT_FILE = DATA_DIR / "current"


def parse_log_line(line):
    """parse a log line into timestamp, action, category, project, and tags"""
    parts = line.strip().split()
    if len(parts) < 4:
        return None
    
    timestamp_str = parts[0]
    action = parts[1]
    category = parts[2]
    project = parts[3]
    tags = parts[4:] if len(parts) > 4 else []
    
    try:
        # parse as UTC, then convert to Eastern Time
        timestamp_utc = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        timestamp_eastern = timestamp_utc.astimezone(EASTERN)
    except ValueError:
        return None
    
    return {
        'timestamp': timestamp_eastern,
        'action': action,
        'category': category,
        'project': project,
        'tags': tags
    }


def get_time_range(period):
    """get start and end datetime for the given period in Eastern Time"""
    now_eastern = datetime.now(EASTERN)
    today_start = now_eastern.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if period == 'day':
        start = today_start
        end = today_start + timedelta(days=1)
    elif period == 'week':
        # monday is 0, sunday is 6
        days_since_monday = (now_eastern.weekday()) % 7
        start = today_start - timedelta(days=days_since_monday)
        end = start + timedelta(days=7)
    elif period == 'month':
        start = today_start.replace(day=1)
        # get first day of next month
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    elif period == 'year':
        start = today_start.replace(month=1, day=1)
        end = start.replace(year=start.year + 1)
    else:
        return None, None
    
    return start, end


def format_duration(seconds):
    """format duration in seconds as h:mm"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}:{minutes:02d}"


def summarize(period='day', show_tags=False):
    """summarize time tracking for the given period"""
    if not LOG_FILE.exists():
        print("No log file found.")
        return
    
    start_time, end_time = get_time_range(period)
    if start_time is None:
        print(f"Invalid period: {period}")
        print("Valid periods: day, week, month, year")
        return
    
    # time the parsing
    parse_start = time.time()
    
    # read and parse log entries
    entries = []
    with open(LOG_FILE, 'r') as f:
        for line in f:
            entry = parse_log_line(line)
            if entry:
                entries.append(entry)
    
    parse_duration = time.time() - parse_start
    
    # match start/stop pairs and calculate durations
    sessions = []
    pending_starts = {}  # key: (category, project) -> list of (start_time, tags)
    
    for entry in entries:
        # entry timestamp is already in Eastern Time
        entry_time = entry['timestamp']
        
        # check if entry is in the time range (both in Eastern Time)
        if entry_time < start_time or entry_time >= end_time:
            continue
        
        key = (entry['category'], entry['project'])
        
        if entry['action'] == 'start':
            if key not in pending_starts:
                pending_starts[key] = []
            pending_starts[key].append((entry_time, entry['tags']))
        elif entry['action'] == 'stop':
            if key in pending_starts and pending_starts[key]:
                start, tags = pending_starts[key].pop(0)
                duration = (entry_time - start).total_seconds()
                sessions.append({
                    'category': entry['category'],
                    'project': entry['project'],
                    'start': start,
                    'end': entry_time,
                    'duration': duration,
                    'tags': tags
                })
    
    if not sessions:
        period_name = period.capitalize()
        print(f"No tracked time found for this {period}.")
        return
    
    # group by category and project
    by_category_project = defaultdict(float)
    total_seconds = 0
    
    for session in sessions:
        key = (session['category'], session['project'])
        by_category_project[key] += session['duration']
        total_seconds += session['duration']
    
    # print summary
    period_name = period.capitalize()
    print(f"Time Summary - This {period_name}")
    print("=" * 50)
    print(f"Total: {format_duration(int(total_seconds))}")
    print()
    
    # sort by duration (descending)
    sorted_items = sorted(by_category_project.items(), key=lambda x: x[1], reverse=True)
    
    # print tree structure
    print("Breakdown:")
    current_category = None
    for (category, project), duration in sorted_items:
        if category != current_category:
            if current_category is not None:
                print()
            print(f"  {category}/")
            current_category = category
        print(f"    {project}: {format_duration(int(duration))}")
        
        # if show_tags is True, show tag breakdown for this project
        if show_tags:
            # collect all sessions for this category/project
            project_sessions = [s for s in sessions if s['category'] == category and s['project'] == project]
            # group by tags
            tag_durations = defaultdict(float)
            for s in project_sessions:
                if s['tags']:
                    # create a key from sorted tags for consistency
                    tag_key = tuple(sorted(s['tags']))
                    tag_durations[tag_key] += s['duration']
                else:
                    tag_durations[tuple()] += s['duration']
            
            if tag_durations:
                # sort by duration
                sorted_tags = sorted(tag_durations.items(), key=lambda x: x[1], reverse=True)
                for tag_tuple, tag_duration in sorted_tags:
                    if tag_tuple:
                        tag_str = ', '.join(tag_tuple)
                        print(f"      [{tag_str}]: {format_duration(int(tag_duration))}")
                    else:
                        print(f"      [no tags]: {format_duration(int(tag_duration))}")
    
    # print parsing time at the bottom
    if parse_duration < 1:
        parse_time_str = f"{parse_duration * 1000:.3f}ms"
    else:
        parse_time_str = f"{parse_duration:.2f}s"
    print()
    print(f"({parse_time_str} to parse log file)")


def list_tags():
    """list all tags broken apart by project"""
    if not LOG_FILE.exists():
        print("No log file found.")
        return
    
    # read and parse log entries
    entries = []
    with open(LOG_FILE, 'r') as f:
        for line in f:
            entry = parse_log_line(line)
            if entry:
                entries.append(entry)
    
    # collect all tags by project
    # structure: {category: {project: set(tags)}}
    tags_by_project = defaultdict(lambda: defaultdict(set))
    
    for entry in entries:
        if entry['action'] == 'start' and entry['tags']:
            category = entry['category']
            project = entry['project']
            for tag in entry['tags']:
                tags_by_project[category][project].add(tag)
    
    if not tags_by_project:
        print("No tags found in any projects.")
        return
    
    print("Tags by Project")
    print("=" * 50)
    
    # sort categories and projects for consistent output
    sorted_categories = sorted(tags_by_project.keys())
    
    for category in sorted_categories:
        print(f"\n  {category}/")
        sorted_projects = sorted(tags_by_project[category].keys())
        for project in sorted_projects:
            tags = sorted(tags_by_project[category][project])
            print(f"    {project}:")
            for tag in tags:
                print(f"      - {tag}")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'tag' and len(sys.argv) > 2 and sys.argv[2] == 'list':
        list_tags()
    elif len(sys.argv) > 1 and sys.argv[1] == 'tag':
        # timetrack tag (without period, default to day)
        period = 'day'
        summarize(period, show_tags=True)
    elif len(sys.argv) > 2 and sys.argv[2] == 'tag':
        # timetrack <period> tag
        period = sys.argv[1]
        summarize(period, show_tags=True)
    else:
        period = sys.argv[1] if len(sys.argv) > 1 else 'day'
        summarize(period)

