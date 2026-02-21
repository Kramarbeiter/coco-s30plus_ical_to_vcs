import argparse
import sys
import os
import re
from datetime import datetime

def clean_text(text):
    """Replaces umlauts and removes special characters for the Nokia."""
    replacements = {'ä':'ae', 'ö':'oe', 'ü':'ue', 'Ä':'Ae', 'Ö':'Oe', 'Ü':'Ue', 'ß':'ss'}
    for k, v in replacements.items():
        text = text.replace(k, v)
    return re.sub(r'[^a-zA-Z0-9\s\.\!\?\-\:\(\)\,\/]', '', text).strip()

class Event:
    def __init__(self, start='', end='', summary='', location='', description='', rrule=''):
        self.start = start.split('Z')[0].split('+')[0]
        self.end_orig = end.split('Z')[0].split('+')[0] if end else self.start
        
        self.summary_clean = clean_text(summary)
        self.location_clean = clean_text(location)
        self.rrule_orig = rrule
        self.final_summary = ""

    def get_interval(self):
        if not self.rrule_orig: return 1
        match = re.search(r'INTERVAL=(\d+)', self.rrule_orig.upper())
        return int(match.group(1)) if match else 1

    def translate_and_build_summary(self):
        r = self.rrule_orig.upper()
        interval = self.get_interval()
        logic_str = ""
        
        # 1. Round-up logic (Appends the note for clarification)
        if r and interval > 1:
            start_dt = datetime.strptime(self.start[:8], "%Y%m%d")
            kw = start_dt.isocalendar()[1]
            unit = "W" if "WEEKLY" in r else "D"
            logic_str = f"({interval}{unit}-W{kw})"

        title = self.summary_clean
        location = self.location_clean

        def assemble(t, l, log):
            res = t
            if l: res += f", {l}"
            if log: res += f" {log}"
            return res

        test_summary = assemble(title, location, logic_str)

        # 2. Length check: Limit is 40 characters!
        if len(test_summary) > 40 and location:
            print(f"  -> WARNING: Location '{location}' in '{title[:15]}...' skipped (Subject otherwise > 40 chars).")
            location = "" 
            test_summary = assemble(title, location, logic_str)

        # 3. If still too long (title extremely long), truncate the title
        if len(test_summary) > 40:
            suffix_len = len(f" {logic_str}") if logic_str else 0
            max_title_len = 40 - suffix_len
            title = title[:max_title_len].strip()
            test_summary = assemble(title, "", logic_str)

        self.final_summary = test_summary

        if r and interval > 1:
            print(f"  -> Round-up: '{self.final_summary}'")

        # 4. Nokia series prefix (vCalendar 1.0 Standards)
        prefix = ""
        if r:
            if "DAILY" in r: prefix = "D1"
            elif "WEEKLY" in r: prefix = "W1"
            elif "MONTHLY" in r: prefix = "MD1" 
            elif "YEARLY" in r: prefix = "YD1"  
            
        return f"{prefix} {self.start}" if prefix else ""

    def toVCS(self):
        rrule_nokia = self.translate_and_build_summary()
        
        nokia_end = self.end_orig
        if rrule_nokia:
            until_date = "20991231" # Infinite, if no end is defined
            match = re.search(r'UNTIL=([0-9]{8})', self.rrule_orig.upper())
            if match:
                until_date = match.group(1)
            
            end_time = self.end_orig[8:] if len(self.end_orig) > 8 else "T000000"
            nokia_end = f"{until_date}{end_time}"

        # Absolute minimum of fields
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:1.0",
            "BEGIN:VEVENT",
            f"SUMMARY;CHARSET=UTF-8:{self.final_summary}",
            f"DTSTART:{self.start}",
            f"DTEND:{nokia_end}"
        ]
        
        if rrule_nokia:
            lines.append(f"RRULE:{rrule_nokia}")
            
        lines.append(f"AALARM:{self.start};;;")
        lines.append("END:VEVENT")
        lines.append("END:VCALENDAR")
        
        return "\r\n".join(lines)

    def get_filename(self):
        clean_title = re.sub(r'[^a-zA-Z0-9]', '', self.summary_clean.replace(' ', '_'))
        return f"{clean_title[:15]}_{self.start[:15]}.vcs"

class Calendar:
    def __init__(self, file_path):
        self.events = []
        if not os.path.exists(file_path): return
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            tmp = {'start':'','end':'','summary':'','location':'','description':'','rrule':''}
            in_ev = False
            for line in f:
                line = line.strip()
                if line.startswith('BEGIN:VEVENT'): in_ev = True
                elif line.startswith('END:VEVENT'):
                    self.events.append(Event(**tmp))
                    tmp = {'start':'','end':'','summary':'','location':'','description':'','rrule':''}
                    in_ev = False
                elif in_ev and ':' in line:
                    try:
                        k_f, v = line.split(':', 1)
                        k = k_f.split(';')[0]
                        if k == 'DTSTART': tmp['start'] = v
                        elif k == 'DTEND': tmp['end'] = v
                        elif k == 'SUMMARY': tmp['summary'] = v
                        elif k == 'LOCATION': tmp['location'] = v
                        elif k == 'RRULE': tmp['rrule'] = v
                    except: continue

    def scan(self, all_past=False):
        self.events.sort(key=lambda x: x.start)
        today = datetime.now().strftime('%Y%m%d')
        return [e for e in self.events if all_past or (e.start[:8] >= today or e.rrule_orig)]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true', help="Export all events, including past ones")
    args = parser.parse_args()

    # 1. Find all .ics files in the current directory
    ics_files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and f.lower().endswith('.ics')])
    
    if not ics_files:
        print("No .ics files found in the current directory.")
        sys.exit()

    print("\nFound .ics files:")
    for idx, f in enumerate(ics_files, 1):
        print(f"  [{idx}] {f}")

    # 2. Ask user for selection
    file_selection = input("\nWhich files should be processed? (Enter single number / multiple comma-seperated numbers or just press Enter to process all files): ").strip()

    selected_files = []
    if not file_selection:
        selected_files = ics_files
    else:
        indices = [i.strip() for i in file_selection.split(',')]
        for i in indices:
            if i.isdigit():
                idx = int(i)
                if 1 <= idx <= len(ics_files):
                    selected_files.append(ics_files[idx-1])
                else:
                    print(f"  -> Ignoring invalid selection: {idx}")

    if not selected_files:
        print("No valid files selected. Exiting.")
        sys.exit()

    out_dir = "vcs_files"
    if not os.path.exists(out_dir): os.makedirs(out_dir)

    total_files_created = 0

    # 3. Process selected files
    for current_file in selected_files:
        cal = Calendar(current_file)
        found_events = cal.scan(all_past=args.all)
        
        total = len(found_events)
        if total == 0:
            print(f"\nNo matching events found in '{current_file}'.")
            continue

        print("\n" + "="*40)
        print(f"FILE ANALYSIS: {current_file}")
        print(f"Found events: {total}")
        print("="*40)

        user_input = input(f"How many events shall be processed? (1-{total}, or Enter for all): ").strip()
        limit = int(user_input) if user_input.isdigit() else total

        export_count = min(limit, total)
        for i in range(export_count):
            ev = found_events[i]
            vcs_text = ev.toVCS()
            path = os.path.join(out_dir, ev.get_filename())
            with open(path, 'w', encoding='latin-1', errors='replace') as f:
                f.write(vcs_text)
        
        print(f"  -> {export_count} events from '{current_file}' created in '{out_dir}'.")
        total_files_created += export_count
    
    print("\n" + "="*40)
    print(f"DONE! Processed and created a total of {total_files_created} files.")
    print("="*40 + "\n")
