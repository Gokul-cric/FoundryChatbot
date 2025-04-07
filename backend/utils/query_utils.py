import re
import difflib
import calendar
from datetime import datetime
import pandas as pd



def expand_month_range_across_years(start_month, start_year, end_month, end_year):
    """Expands range across months and possibly years (e.g., March 2022 to May 2023)."""
    start_year = int(start_year)
    end_year = int(end_year)
    start_index = list(calendar.month_abbr).index(start_month[:3])
    end_index = list(calendar.month_abbr).index(end_month[:3])

    result = []
    for year in range(start_year, end_year + 1):
        month_start = start_index if year == start_year else 1
        month_end = end_index if year == end_year else 12
        for i in range(month_start, month_end + 1):
            result.append((calendar.month_abbr[i], str(year)))
    return result

def extract_query_params(user_query, prev_foundry=None, prev_defect_type=None):
    foundries = [ "Munjal"]#"MCIE", "Munjal Line 1", "MMK", "AIW",
    defect_types = ["Blow Hole", "Sand Inclusion defect", "Erosion Scab", "Broken Mould", "Sand Fusion", "Mould Swell", "Total Rejection"]

    sorted_foundries = sorted(foundries, key=lambda x: -len(x))
    foundry = next((f for f in sorted_foundries if f.lower() in user_query.lower()), None)
    defect_type = next((d for d in defect_types if d.lower() in user_query.lower()), None)

    

    foundry = foundry or prev_foundry or "Munjal"
    defect_type = defect_type or prev_defect_type

    month_map = {m.lower(): calendar.month_abbr[i] for i, m in enumerate(calendar.month_name) if m}
    month_map.update({calendar.month_abbr[i].lower(): calendar.month_abbr[i] for i in range(1, 13)})
    month_map.update({str(i): calendar.month_abbr[i] for i in range(1, 13)})
    month_map.update({f"{i:02}": calendar.month_abbr[i] for i in range(1, 13)})

    months, year = [], None

    user_query = re.sub(r"(\b\d{4})[\s\-]*(\b[a-z]{3,9}\b)", r"\2 \1", user_query, flags=re.IGNORECASE)

    
    range_with_year = re.search(r"(\b[a-z]{3,9})\s*(?:to|and|-)\s*(\b[a-z]{3,9})\s+(\d{2,4})", user_query, re.IGNORECASE)
    if range_with_year:
        m1, m2, y = range_with_year.groups()
        year = f"20{y}" if len(y) == 2 else y
        months = expand_month_range_across_years(month_map[m1.lower()], year, month_map[m2.lower()], year)
        return foundry, defect_type, [m for m, y in months], year

    range_across_years = re.search(r"(\b[a-z]{3,9})\s+(\d{2,4})\s*(?:to|-)\s*(\b[a-z]{3,9})\s+(\d{2,4})", user_query, re.IGNORECASE)
    if range_across_years:
        m1, y1, m2, y2 = range_across_years.groups()
        y1 = f"20{y1}" if len(y1) == 2 else y1
        y2 = f"20{y2}" if len(y2) == 2 else y2
        months = expand_month_range_across_years(month_map[m1.lower()], y1, month_map[m2.lower()], y2)
        return foundry, defect_type, [m for m, y in months], None

    all_year = re.search(r"all\s+periods\s+in\s+(\d{4})", user_query, re.IGNORECASE)
    if all_year:
        year = all_year.group(1)
        return foundry, defect_type, list(calendar.month_abbr[1:]), year

    matches = re.findall(r"\b([a-zA-Z]{3,9})\b(?:\s*['\-]?\s*(\d{2,4}))?", user_query, re.IGNORECASE)
    for m, y in matches:
        if m.lower() in month_map:
            months.append(month_map[m.lower()])
        elif difflib.get_close_matches(m.lower(), month_map.keys(), n=1, cutoff=0.75):
            match = difflib.get_close_matches(m.lower(), month_map.keys(), n=1)[0]
            months.append(month_map[match])
        if y:
            year = f"20{y}" if len(y) == 2 else y

    if months:
        return foundry, defect_type, list(set(months)), year

    if not months and not year:
        words = re.findall(r'\b[a-z]{3,9}\b', user_query.lower())
        for word in words:
            if word in month_map:
                return foundry, defect_type, [month_map[word]], None
            close_match = difflib.get_close_matches(word, month_map.keys(), n=1, cutoff=0.75)
            if close_match:
                return foundry, defect_type, [month_map[close_match[0]]], None

    if not months:
        year_only = re.search(r"\b(?:in\s+)?(\d{2,4})\b", user_query)
        if year_only:
            y = year_only.group(1)
            year = f"20{y}" if len(y) == 2 else y
            return foundry, defect_type, list(calendar.month_abbr[1:]), year

    foundry = foundry or prev_foundry or "Munjal"
    defect_type = defect_type or prev_defect_type
    return foundry, defect_type, None, None
