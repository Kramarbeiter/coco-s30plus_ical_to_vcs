# nokia_3210_ical_to_vcs
Converts `.ics` files into a minimalist vCalendar 1.0 format (`.vcs`) that is tailored to the hardware restrictions of the Nokia 3210 4G (S30+). Based on https://github.com/antoniobarba/vcalconverter.

## Usage
Console: python coco.py calendar.ics [--all]

After starting, the script analyzes the file and interactively asks how many events should be exported. One separate `.vcs` file is created for each selected event, since the device can only import one event at a time. The output files are saved in the vcs_files folder.

## Parameters

1. input: Path to the .ics file (.../calendar.ics)
2. --all (optional): Exports all events. Without this parameter, only events from today onwards are exported (including ongoing past series).

## Core Features & Output

1. Dynamic 40-Character Subject
- Since the Nokia does not support locations or notes for recurring events, the script combines all information in the subject: Title, Location (Logic).
- Protection Limit: The subject is strictly capped at 40 characters to prevent unwanted behavior.
- Priority: If space is lacking, the location is removed first (with a warning in the console), then the title is truncated.

2. The "Round-up Logic" (Series Workaround)
- The Nokia only understands standard intervals (daily, weekly, etc.). Complex series (e.g., "Every 2 weeks") are therefore "rounded up" (here: to weekly).
- To clarify the change, the script automatically adds a compact note to the end of the subject, e.g., (2W-W9).
- This means: Interval 2 weeks, start was in week 9. Serves as a quick check on the phone (even/odd week) whether the event is relevant today.
- The console lists all events where this logic was applied.

3. File Naming
  The generated .vcs files are formatted for better overview in the Nokia file manager:
- Format: [Original-Title]_[StartDate].vcs 
- Example: Team_Meeting_20260302.vcs

4. Hardware-Specific Fixes
- End Dates: Series end dates (UNTIL) are patched into the Nokia's DTEND field.
- Formatting: Timezone suffixes (e.g., Z) are removed, as the Nokia often interprets them as an error.
- Umlauts: Are automatically converted (e.g., ö -> oe) to prevent display errors on the screen and save characters.

## Future of this Project

Further developement is not planned.
