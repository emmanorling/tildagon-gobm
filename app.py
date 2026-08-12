"""
A Tildagon app to interface to the GoBM bread tracker, which is hosted at
https://enorling.eu.pythonanywhere.com/

Written by Emma Norling, with the help of Gemini
"""

import app
from events.input import Buttons, BUTTON_TYPES

try:
    import urequests as requests
except ImportError:
    import requests

welcome = (
    "Welcome to the Guild of Bread Makers bread tracker. "
    "If we remember to update the log, you'll see what loaves "
    "are in progress and when they'll be ready.\nPress \"C\" to continue."
)


class BreadTrackerApp(app.App):

    def __init__(self):
        super().__init__()
        self.button_states = Buttons(self)

        # API Endpoints
        self.status_url = "https://enorling.eu.pythonanywhere.com/api/status/"
        self.history_url = "https://enorling.eu.pythonanywhere.com/api/history/"

        # App State - Starts on Welcome screen
        self.current_view = "welcome"  # "welcome", "status", "history", "notes"
        self.status_msg = "Starting..."
        self.timer = 0

        # Machine Status Data & Navigation
        self.machines = []
        self.status_selected_index = 0
        self.status_scroll_offset = 0
        self.has_fetched_status = False

        # Baking History Data & Navigation
        self.history_items = []
        self.history_selected_index = 0
        self.history_scroll_offset = 0
        self.has_fetched_history = False

        # Active Loaf Notes Selection
        self.selected_loaf = None

    def fetch_data(self):
        self.status_msg = "Fetching..."
        try:
            res = requests.get(self.status_url)
            if res.status_code == 200:
                data = res.json()
                self.machines = data.get("machines", [])
                self.status_msg = "Updated"

                if self.status_selected_index >= len(self.machines):
                    self.status_selected_index = max(0, len(self.machines) - 1)
            else:
                self.status_msg = f"HTTP {res.status_code}"
            res.close()
        except Exception:
            self.status_msg = "Conn Error"

    def fetch_history(self):
        self.status_msg = "Fetching History..."
        try:
            res = requests.get(self.history_url)
            if res.status_code == 200:
                data = res.json()
                self.history_items = data.get("history", [])
                self.status_msg = "History Loaded"
            else:
                self.status_msg = f"HTTP {res.status_code}"
            res.close()
        except Exception:
            self.history_items = []
            self.status_msg = "Loaded"
        self.has_fetched_history = True

    def _get_item_height(self, machine, is_selected):
        status = machine.get("status", "Idle")
        if is_selected:
            return 40 if status == "Baking" else 24
        return 16

    def update_history_scroll_offset(self):
        if not self.history_items:
            self.history_scroll_offset = 0
            return

        if self.history_selected_index < self.history_scroll_offset:
            self.history_scroll_offset = self.history_selected_index
            return

        while True:
            y_pos = -42
            fits = False

            for idx in range(self.history_scroll_offset, len(self.history_items)):
                is_selected = (idx == self.history_selected_index)
                h = 32 if is_selected else 18

                if idx == self.history_selected_index and (y_pos + h) <= 68:
                    fits = True
                    break

                y_pos += h
                if y_pos > 68:
                    break

            if fits or self.history_scroll_offset >= self.history_selected_index:
                break

            self.history_scroll_offset += 1

    def update(self, delta):
        # Initial status fetch in background
        if not self.has_fetched_status:
            self.has_fetched_status = True
            self.fetch_data()

        # Handle Action / Confirm button across views
        btn_action = self.button_states.get(BUTTON_TYPES["CONFIRM"]) or (
            BUTTON_TYPES.get("C") and self.button_states.get(BUTTON_TYPES["C"])
        )

        if btn_action:
            self.button_states.clear()
            if self.current_view == "welcome":
                self.current_view = "status"
            elif self.current_view == "status":
                self.current_view = "history"
                if not self.has_fetched_history:
                    self.fetch_history()
            elif self.current_view == "history":
                if self.history_items:
                    self.selected_loaf = self.history_items[self.history_selected_index]
                    self.current_view = "notes"
            return

        # Handle Button F (CANCEL) as Back Button across all views
        if self.button_states.get(BUTTON_TYPES["CANCEL"]):
            self.button_states.clear()
            if self.current_view == "notes":
                self.current_view = "history"
            elif self.current_view == "history":
                self.current_view = "status"
            elif self.current_view == "status":
                self.current_view = "welcome"
            else:
                self.minimise()
            return

        # View-Specific Navigation Controls
        if self.current_view == "status":
            if BUTTON_TYPES.get("DOWN") and self.button_states.get(BUTTON_TYPES["DOWN"]):
                self.button_states.clear()
                if self.machines and self.status_selected_index < len(self.machines) - 1:
                    self.status_selected_index += 1

            if BUTTON_TYPES.get("UP") and self.button_states.get(BUTTON_TYPES["UP"]):
                self.button_states.clear()
                if self.status_selected_index > 0:
                    self.status_selected_index -= 1

        elif self.current_view == "history":
            if BUTTON_TYPES.get("DOWN") and self.button_states.get(BUTTON_TYPES["DOWN"]):
                self.button_states.clear()
                if self.history_items and self.history_selected_index < len(self.history_items) - 1:
                    self.history_selected_index += 1

            if BUTTON_TYPES.get("UP") and self.button_states.get(BUTTON_TYPES["UP"]):
                self.button_states.clear()
                if self.history_selected_index > 0:
                    self.history_selected_index -= 1

        # Auto-refresh status data every 30 seconds
        self.timer += delta
        if self.timer > 30000:
            self.timer = 0
            if self.current_view == "status":
                self.fetch_data()

    def draw(self, ctx):
        ctx.save()

        # Background (Dark slate)
        ctx.rgb(0.1, 0.1, 0.15).rectangle(-120, -120, 240, 240).fill()
        ctx.text_align = ctx.CENTER

        if self.current_view == "welcome":
            self.draw_welcome_view(ctx)
        elif self.current_view == "status":
            self.draw_status_view(ctx)
        elif self.current_view == "history":
            self.draw_history_view(ctx)
        elif self.current_view == "notes":
            self.draw_notes_view(ctx)

        ctx.restore()

    def draw_welcome_view(self, ctx):
        ctx.font_size = 16
        ctx.rgb(1.0, 0.75, 0.3).move_to(0, -75).text("Bread Tracker")

        ctx.font_size = 12
        ctx.rgb(0.9, 0.9, 0.9)

        # Split and format welcome message for display
        paragraphs = welcome.split("\n")
        y_pos = -45

        for para in paragraphs:
            words = para.split(" ")
            current_line = ""

            for word in words:
                if len(current_line + " " + word) <= 28:
                    current_line += (" " if current_line else "") + word
                else:
                    ctx.move_to(0, y_pos).text(current_line)
                    y_pos += 14
                    current_line = word
            if current_line:
                if "Press" in current_line:
                    ctx.rgb(0.3, 1.0, 0.4)  # Highlight the prompt in green
                ctx.move_to(0, y_pos).text(current_line)
                y_pos += 14

        #ctx.font_size = 10
        #ctx.rgb(0.5, 0.5, 0.5).move_to(0, 95).text("C: Continue | F: Exit")

    def _wrap_text(self, text, max_chars):
        if not text:
            return []
        
        paragraphs = text.split("\n")
        lines = []

        for para in paragraphs:
            words = para.split(" ")
            current_line = ""

            for word in words:
                if len(current_line + " " + word) <= max_chars:
                    current_line += (" " if current_line else "") + word
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

        return lines

    def draw_status_view(self, ctx):
        ctx.font_size = 18
        ctx.rgb(1.0, 0.75, 0.3).move_to(0, -75).text("Bread Tracker")

        if not self.machines:
            ctx.font_size = 13
            ctx.rgb(0.8, 0.8, 0.8).move_to(0, 0).text(self.status_msg)
            ctx.font_size = 10
            ctx.rgb(0.5, 0.5, 0.5).move_to(0, 95).text("C: Completed loaves")
            return

        sel_idx = self.status_selected_index
        sel_machine = self.machines[sel_idx]
        name = sel_machine.get("name", "Machine")
        status = sel_machine.get("status", "Idle")

        # 1. DRAW SELECTED MACHINE (CENTERED AT y = 0 WITH WRAPPING)
        if status == "Baking":
            ctx.rgb(0.3, 1.0, 0.4)
            loaf = sel_machine.get("loaf", "Bread")
            ready = sel_machine.get("ready_at", "")

            # Wrap machine name and active loaf details
            name_lines = self._wrap_text(f"► {name} ◄", 18)
            loaf_str = f"{loaf} - {ready}" if ready else loaf  # e.g., "Sourdough - Ready in 45m"
            loaf_lines = self._wrap_text(loaf_str, 24)

            # Calculate height of wrapped block to keep it centered around y = 0
            total_height = (len(name_lines) * 16) + (len(loaf_lines) * 14) + 4
            start_y = -(total_height // 2) + 12

            ctx.font_size = 15
            for line in name_lines:
                ctx.move_to(0, start_y).text(line)
                start_y += 16

            start_y += 2
            ctx.font_size = 12
            for line in loaf_lines:
                ctx.move_to(0, start_y).text(line)
                start_y += 14

            top_boundary = -(total_height // 2) - 6
            bottom_boundary = (total_height // 2) + 10

        else:
            ctx.rgb(1.0, 1.0, 1.0)
            idle_lines = self._wrap_text(f"► {name}: Idle ◄", 18)

            total_height = len(idle_lines) * 16
            start_y = -(total_height // 2) + 10

            ctx.font_size = 15
            for line in idle_lines:
                ctx.move_to(0, start_y).text(line)
                start_y += 16

            top_boundary = -(total_height // 2) - 6
            bottom_boundary = (total_height // 2) + 10

        # 2. DRAW ITEMS ABOVE SELECTED ITEM (going upwards)
        y_above = top_boundary
        for idx in range(sel_idx - 1, -1, -1):
            if y_above < -55:
                break
            m = self.machines[idx]
            m_name = m.get("name", "Machine")
            m_status = m.get("status", "Idle")
            label = f"{m_name} (Baking)" if m_status == "Baking" else f"{m_name}: Idle"

            m_lines = self._wrap_text(label, 26)
            ctx.rgb(0.5, 0.5, 0.5)
            ctx.font_size = 11

            for line in reversed(m_lines):
                if y_above < -55:
                    break
                ctx.move_to(0, y_above).text(line)
                y_above -= 14
            y_above -= 4

        # 3. DRAW ITEMS BELOW SELECTED ITEM (going downwards)
        y_below = bottom_boundary
        for idx in range(sel_idx + 1, len(self.machines)):
            if y_below > 65:
                break
            m = self.machines[idx]
            m_name = m.get("name", "Machine")
            m_status = m.get("status", "Idle")
            label = f"{m_name} (Baking)" if m_status == "Baking" else f"{m_name}: Idle"

            m_lines = self._wrap_text(label, 26)
            ctx.rgb(0.5, 0.5, 0.5)
            ctx.font_size = 11

            for line in m_lines:
                if y_below > 65:
                    break
                ctx.move_to(0, y_below).text(line)
                y_below += 14
            y_below += 4

        # Footer
        ctx.font_size = 10
        ctx.rgb(0.5, 0.5, 0.5)
        if len(self.machines) > 1:
            counter = f"{self.status_selected_index + 1}/{len(self.machines)}"
            ctx.move_to(0, 80).text(f"▲ {counter} ▼")

        ctx.move_to(0, 95).text("C: History | F: Back")

    def draw_history_view(self, ctx):
        ctx.font_size = 18
        ctx.rgb(0.3, 0.75, 1.0).move_to(0, -75).text("Baking History")

        self.update_history_scroll_offset()
        y_pos = -42

        if not self.history_items:
            ctx.font_size = 13
            ctx.rgb(0.8, 0.8, 0.8).move_to(0, 0).text(self.status_msg)
        else:
            visible_items = self.history_items[self.history_scroll_offset:]

            for i, item in enumerate(visible_items):
                if y_pos > 68:
                    break

                actual_index = self.history_scroll_offset + i
                is_selected = (actual_index == self.history_selected_index)

                name = item.get("name", "Loaf")
                date = item.get("date", "")

                if is_selected:
                    ctx.rgb(1.0, 0.9, 0.4)
                    ctx.font_size = 15
                    ctx.move_to(0, y_pos).text(f"► {name} ◄")
                    y_pos += 16

                    ctx.font_size = 11
                    ctx.move_to(0, y_pos).text(f"Completed: {date}")
                    y_pos += 18
                else:
                    ctx.rgb(0.5, 0.5, 0.5)
                    ctx.font_size = 11
                    ctx.move_to(0, y_pos).text(f"{name} - {date}")
                    y_pos += 18

        ctx.font_size = 10
        ctx.rgb(0.5, 0.5, 0.5)

        if len(self.history_items) > 1:
            counter = f"{self.history_selected_index + 1}/{len(self.history_items)}"
            ctx.move_to(0, 80).text(f"▲ {counter} ▼")

        ctx.move_to(0, 95).text("C: Select | F: Back")

    def draw_notes_view(self, ctx):
        if not self.selected_loaf:
            ctx.font_size = 13
            ctx.rgb(0.8, 0.8, 0.8).move_to(0, 0).text("No Loaf Selected")
            return

        name = self.selected_loaf.get("name", "Loaf Notes")
        date = self.selected_loaf.get("date", "")
        machine = self.selected_loaf.get("machine", "Unknown Machine")
        notes = self.selected_loaf.get("notes", "No addtional notes recorded.")

        # 1. Header Title (Wrapped safely to max 2 lines)
        ctx.font_size = 15
        ctx.rgb(1.0, 0.75, 0.3)
        title_lines = self._wrap_text(name, 18)
        
        y_pos = -80
        for line in title_lines[:2]:
            ctx.move_to(0, y_pos).text(line)
            y_pos += 16

        # 2. Metadata Subheader (Wrapped to fit circular display)
        ctx.font_size = 12
        ctx.rgb(0.6, 0.6, 0.6)
        meta_text = f"Was ready at {date} in {machine}"
        meta_lines = self._wrap_text(meta_text, 26)
        
        for line in meta_lines[:2]:
            ctx.move_to(0, y_pos).text(line)
            y_pos += 13

        y_pos += 6  # Gap before note body

        # 3. Notes Content (Tighter 22-char limit to prevent edge clipping)
        ctx.font_size = 12
        ctx.rgb(0.9, 0.9, 0.9)
        note_lines = self._wrap_text(notes, 22)

        for line in note_lines:
            if y_pos > 75:  # Prevent rendering over footer
                break
            ctx.move_to(0, y_pos).text(line)
            y_pos += 15

        # Footer Back Prompt
        ctx.font_size = 10
        ctx.rgb(0.5, 0.5, 0.5).move_to(0, 95).text("F: Back to History")


__app_export__ = BreadTrackerApp
main = BreadTrackerApp
