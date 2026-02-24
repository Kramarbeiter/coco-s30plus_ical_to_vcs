Based on https://github.com/antoniobarba/vcalconverter.

<img width="256" height="1024" alt="icon" src="https://github.com/user-attachments/assets/3db2fa17-66ab-46c2-9ebb-d259e1e080ad" />

# [Download Executable](https://github.com/Kramarbeiter/coca-s30plus_ical_to_vcs/releases/)
Download and run `.exe` file. Hover to recieve explanations.

<img width="512" height="480" alt="Coca" src="https://github.com/user-attachments/assets/18c516c6-5ed3-4ff9-ab3c-b4379e1c7517" />

# Script

## Usage
Console:
- python coca_gui.py

## Core Features & Output

### Dynamic 40-Character Subject
- Since the Nokia does not synchronise the location and note data with the `.vcs` file of the respective event, the script combines all information in the subject: "Title, Location (Logic)". Notes are not supported due to the character limit.
- Protection: The subject is strictly capped at 40 characters to prevent unwanted behavior. This is the maximum number of characters that can be entered in the subject field on the device.
- Priority: If space is lacking, the location is removed first (with a warning in the console), then the title is truncated. The logic has priority.

### The "Round-up Logic" (Series Workaround)
- The Nokia only understands standard intervals (daily, weekly, etc.). Complex series (e.g., "Every 2 weeks") are therefore "rounded up" (here: to weekly).
- To clarify the change, the script automatically adds a compact note to the end of the subject, e.g., (2W-W9). This means: Interval 2 weeks, start was in week 9. Serves as a quick check on the phone (even/odd week) whether the event is relevant today.
- The console lists all events where this logic was applied.
- The device does not support specifying the end of a series, but time-limited series converted by this script can be imported and will function correctly.

### File Naming
  The generated `.vcs` files are formatted for better overview in the Nokia file manager:
- Format: `[Original-Title]_[StartDate].vcs`
- Example: `Team_Meeting_20260302.vcs`

### Hardware-Specific Fixes
- End Dates: Series end dates (UNTIL) are patched into the Nokia's DTEND field.
- Formatting: Timezone suffixes (e.g., Z) are removed, as the Nokia often interprets them as an error.
- Umlauts: Are automatically converted (e.g., ö -> oe) to prevent display errors on the screen and save characters.

## Prerequisites
- **Python 3.x** is required to run this script.
- No external packages or dependencies are needed (the script relies entirely on Python's standard libraries).

# Future of this Project

Since the script solves the problem I had in the most practicable way I can think of, no further developement is planned. However, feel free to make improvements yourself.
