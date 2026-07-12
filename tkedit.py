#!/opt/homebrew/bin/python3

# tkedit.py
# M Leidel 7/2026
#     use "which python3" to find path to python3
#     MacOS - #!/opt/homebrew/bin/python3


import os
import sys
import configparser
import subprocess
import webbrowser
import json
import platform
import re
from datetime import datetime
from pathlib import Path
from tkinter import Listbox
from tkinter import filedialog
from tkinter import TclError
from ttkbootstrap import *
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Querybox
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.widgets import ToolTip
from ttkbootstrap import Style
import tkinterdnd2 as tkdnd
from tkinterdnd2 import DND_FILES, TkinterDnD
from tklinenums import TkLineNumbers
import markdown
from Tksyntex import SyntaxHighlighter

# selection parameters
word_re = re.compile(r"[^()\[\],\.\-\s=\"\';:\/]+")

# language identification
lx = [".txt",".py",".js",".c",".java",".html",".css",".go",".rs",".sh",".json",".sql",".md",".ini", ".h", ".cpp"]
#       0           2                    5                  8             10                               15

# language maps to lx
lex = ['text', 'python', 'javascript', 'cpp', 'java', 'html', 'css', 'go',
       'rust', 'bash', 'json', 'sql', 'markdown', 'ini', 'cpp', 'cpp']

if platform.system() == "Windows":
    # Windows will store the config files in the app directory
    inipath  = Path("C:\\", "TKedit", "tkedit.ini")
    lastpath = Path("C:\\", "TKedit", "lastfile")
    winpath  = Path("C:\\", "TKedit", "winfo")
    appicon  = Path("C:\\", "TKedit", "tkedit256.png")
    recents  = Path("C:\\", "TKedit", "recent_files.json")
    snipdir  = Path("C:\\", "TKedit", "snippets")
elif platform.system() == "Darwin":
    user = os.environ.get("USER")
    inipath = Path("/Users",user,".config","tkedit","tkedit.ini")
    lastpath = Path("/Users",user,".config","tkedit","lastfile")
    winpath = Path("/Users",user,".config","tkedit","winfo")
    appicon = Path("/Users",user,".config","tkedit","tkedit256.png")
    recents = Path("/Users",user,".config","tkedit","recent_files.json")
    snipdir = Path("/Users",user,".config","tkedit","snippets")
else:
    # Linux will store the config files in ~/.config/TKedit directory
    user = os.environ.get("USER")
    inipath = Path("/home",user,".config","tkedit","tkedit.ini")
    lastpath = Path("/home",user,".config","tkedit","lastfile")
    winpath = Path("/home",user,".config","tkedit","winfo")
    appicon = Path("/home",user,".config","tkedit","tkedit256.png")
    recents = Path("/home",user,".config","tkedit","recent_files.json")
    snipdir = Path("/home",user,".config","tkedit","snippets")
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class TKedit:
    ''' master class for TKedit '''
    def __init__(self, master):
        self.master = master
        self.master.title("TKedit Text Editor")
        self.rf_manager = RecentFilesManager()

        # get settings from ini file
        try:
            config = configparser.ConfigParser()
            config.read(inipath)
            # set settings variables
            self.fontname = config['Main']['font']
            self.fontsize = int(config['Main']['fontsize'])
            self.theme = config['Main']['theme']
            self.color = config['Main']['style']
            self.open_last = config['Main']['lastfile']
            self.tabsize = int(config['Main']['tabsz'])
            self.terminal = config['Main']['terminal']
            self.appath = config['Main']['appath']
            self.autoindent = config['Main']['autoindent']
            self.debounce = config['Main']['debounce']
            self.md2html = config['Main']['md2html']
            self.backups = config['Main']['backup']
            self.filemanager = config['Main']['filemgr']
            self.nospaces = config['Main']['nospaces']
        except Exception as e:
            print(e)
            Messagebox.show_error("Config Error", "tkedit.ini")
            sys.exit()

        # some "globals"
        self.filename = None
        self.filepriv = None
        self.is_dirty = False
        self.last_found_index = 0
        self.search_term = ""
        self.has_highlight = False
        self.indent = " " * self.tabsize
        self.bookmarks = set()
        self.dropfile = None

        # now the layout and initializing

        frame_t = Frame(root)
        frame_t.pack(side="right", fill="both", expand=True)

        # Scrollbars packed FIRST so they reserve space before the text area expands
        hbar = Scrollbar(frame_t, orient="horizontal")
        hbar.pack(fill="x", side="bottom")

        vbar = Scrollbar(frame_t, orient="vertical")
        vbar.pack(fill="y", side="right")

        # Text area pack AFTER scrollbars
        self.text_area = Text(frame_t,
                              wrap="none", # or wrap
                              undo=True,
                              xscrollcommand=hbar.set,
                              yscrollcommand=vbar.set)

        self.text_area.pack(expand=True, fill="both", side="top")

        # Link scrollbars to text area
        hbar.config(command=self.text_area.xview)
        vbar.config(command=self.text_area.yview)

        # determine colors for TkLineNumbers, based on ttkbootstrap themes
        bg="#ffffff"  # default is for Light Themes
        if self.theme == "darkly": bg="#222222"
        if self.theme == "cyborg": bg="#060606"
        if self.theme == "superhero": bg="#2b3e50"
        if self.theme == "solar": bg="#002b36"
        if self.theme in ["darkly","cyborg","superhero","solar"]:
            fg="#eee"  # light for dark themes
        else:
            fg="#111"  # dark for light themes
        # Create the TkLineNumbers widget and pack it to the left
        self.linenums = TkLineNumbers(root,
                                      self.text_area,
                                      justify="center",
                                      borderwidth=0,
                                      highlightthickness=0,
                                      colors=(fg, bg))
        self.linenums.pack(fill="y", side="left")

        # Create a tag to highlight the search result.
        self.text_area.tag_config("highlight", background="dim gray")

        # "File" Menu

        self.menu_bar = Menu(master)
        self.file_menu = Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        self.file_menu.add_command(label="New Window", accelerator="Ctrl-Shift+W", command=self.open_file_window)

        self.file_menu.add_separator()
        self.file_menu.add_command(label="Open", accelerator="Ctrl+O", command=self.open_file)
        self.file_menu.add_command(label="Open Recents", accelerator="Ctrl-Shift+O", command=self.open_file_recent)
        self.file_menu.add_command(label="Open Prior", accelerator="Ctrl-P", command=self.load_previous)

        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        self.file_menu.add_command(label="Save As", accelerator="Shift-Ctrl+S", command=self.save_file_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Close", accelerator="Ctrl+Q", command=self.close_file)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        # "Other" Menu

        self.file_menu = Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Config", command=self.open_options)

        self.file_menu.add_separator()
        self.file_menu.add_command(label="Find", accelerator="Ctrl+F", command=self.find_text)
        self.file_menu.add_command(label="Next", accelerator="F3", command=self.find_next)
        self.file_menu.add_command(label="Replace", accelerator="Ctrl+H", command=self.find_replace)
        self.file_menu.add_command(label="Toggle Word Wrap", accelerator="Ctrl+W", command=self.toggle_wordwrap)

        self.file_menu.add_separator()
        self.file_menu.add_command(label="Terminal", accelerator="Ctrl+Shift+T", command=self.open_terminal)
        self.file_menu.add_command(label="File Manager", accelerator="Ctrl+Shift+F", command=self.open_file_manager)
        self.file_menu.add_command(label="Snippets", accelerator="Alt+Z", command=self.open_snippet_window)

        self.file_menu.add_separator()
        self.file_menu.add_command(label="About", accelerator="Ctrl+1", command=self.about)
        self.file_menu.add_command(label="Special Keys", accelerator="Ctrl+2", command=self.hotkeys)
        self.file_menu.add_command(label="Documentation", accelerator="Ctrl+3", command=self.display_help)
        self.menu_bar.add_cascade(label="Other", menu=self.file_menu)

        self.master.config(menu=self.menu_bar)



        # Bind keyboard shortcuts everything except MacOS
        if platform.system() != "Darwin":
            self.text_area.bind('<Control-KeyPress-1>', self.about)
            self.text_area.bind('<Control-KeyPress-2>', self.hotkeys)
            self.text_area.bind('<Control-KeyPress-3>', self.display_help)
            self.text_area.bind('<Control-a>', self.select_all)
            self.text_area.bind('<Control-n>', self.new_file)
            self.text_area.bind("<Control-o>", self.open_file)
            self.text_area.bind("<Shift-Control-O>", self.open_file_recent)
            self.text_area.bind("<Shift-Control-W>", self.open_file_window)
            self.text_area.bind("<Shift-Control-S>", self.save_file_as)
            self.text_area.bind("<Control-s>", self.save_file)
            self.text_area.bind("<Control-v>", self.paste)
            root.bind("<Control-q>", self.close_file)
            self.text_area.bind("<Control-f>", self.find_text)
            self.text_area.bind("<F3>", self.find_next)
            self.text_area.bind("<Control-h>", self.find_replace)
            self.text_area.bind("<Control-w>", self.toggle_wordwrap)
            self.text_area.bind("<Control-u>", self.convert_to_uppercase)
            self.text_area.bind("<Control-l>", self.convert_to_lowercase)
            self.text_area.bind("<Shift-Control-T>", self.open_terminal)
            self.text_area.bind("<Shift-Control-F>", self.open_file_manager)
            self.text_area.bind("<Tab>", self.on_tab)
            self.text_area.bind("<Shift-Tab>", self.on_shift_tab)
            self.text_area.bind("<Shift-ISO_Left_Tab>", self.on_shift_tab)
            self.text_area.bind("<Button-3>", self.show_popup)  # right-click to show popup
            self.text_area.bind("<Double-Button-1>", self.select_token)
            self.text_area.bind("<Control-slash>", self.toggle_line_comments)
            self.text_area.bind("<Control-Button-1>", self.toggle_bookmark)
            self.text_area.bind("<Control-b>", self.next_bookmark)
            self.text_area.bind("<Control-Shift-B>", self.clear_bookmarks)
            self.text_area.bind("<Control-p>", self.load_previous)
            self.text_area.bind("<Alt-z>", self.open_snippet_window)
            self.text_area.bind("<Shift-Control-Z>", self.open_snippet_window)  # for Mac
        else:
        # Bind keyboard shortcuts for MacOS
            self.text_area.bind('<Command-KeyPress-1>', self.about)
            self.text_area.bind('<Command-KeyPress-2>', self.hotkeys)
            self.text_area.bind('<Command-KeyPress-3>', self.display_help)
            self.text_area.bind('<Command-a>', self.select_all)
            self.text_area.bind('<Command-n>', self.new_file)
            self.text_area.bind("<Command-o>", self.open_file)
            self.text_area.bind("<Shift-Command-O>", self.open_file_recent)
            self.text_area.bind("<Shift-Command-W>", self.open_file_window)
            self.text_area.bind("<Shift-Command-S>", self.save_file_as)
            self.text_area.bind("<Command-s>", self.save_file)
            self.text_area.bind("<Command-v>", self.paste)
            root.bind("<Command-q>", self.close_file)
            self.text_area.bind("<Command-f>", self.find_text)
            self.text_area.bind("<F3>", self.find_next)
            self.text_area.bind("<Command-h>", self.find_replace)
            self.text_area.bind("<Command-w>", self.toggle_wordwrap)
            self.text_area.bind("<Command-u>", self.convert_to_uppercase)
            self.text_area.bind("<Command-l>", self.convert_to_lowercase)
            self.text_area.bind("<Shift-Command-T>", self.open_terminal)
            self.text_area.bind("<Shift-Command-F>", self.open_file_manager)
            self.text_area.bind("<Tab>", self.on_tab)
            self.text_area.bind("<Shift-Tab>", self.on_shift_tab)
            self.text_area.bind("<Shift-ISO_Left_Tab>", self.on_shift_tab)
            self.text_area.bind("<Button-3>", self.show_popup)  # right-click to show popup
            self.text_area.bind("<Double-Button-1>", self.select_token)
            self.text_area.bind("<Command-slash>", self.toggle_line_comments)
            self.text_area.bind("<Command-Button-1>", self.toggle_bookmark)
            self.text_area.bind("<Command-b>", self.next_bookmark)
            self.text_area.bind("<Command-Shift-B>", self.clear_bookmarks)
            self.text_area.bind("<Command-p>", self.load_previous)
            self.text_area.bind("<Alt-z>", self.open_snippet_window)
            self.text_area.bind("<Shift-Command-Z>", self.open_snippet_window)  # for Mac


        if self.autoindent.lower() == 'yes':
            self.text_area.bind("<Return>", self.on_return)
        for quote in ('"', "'", "`", "*", "_"):
            self.text_area.bind(quote, self.surround_with_quote)

        self.text_area.bind("<<Modified>>", self.on_modified)  # Mark dirty on edits
        self.enable_autopairs(self.text_area)  # setup []]{  [] ddd   }}()
        self.text_area.tag_configure("bookmark", background="black") # Light green highlight

        # --- DRAG AND DROP SETUP ---
        # Register both the master window and your text editor widget as drop targets
        self.master.drop_target_register(tkdnd.DND_FILES)
        self.text_area.drop_target_register(tkdnd.DND_FILES)
        # Bind the drop event to the handler
        self.master.dnd_bind("<<Drop>>", self.handle_drop)
        self.text_area.dnd_bind("<<Drop>>", self.handle_drop)

        # Create highlighter - font information ...
        # using the Tksyntex module
        self.highlighter = SyntaxHighlighter(
            text_widget=self.text_area,
            language="text",
            style_name=self.color,
            font_name=self.fontname,
            font_size=self.fontsize,
            debounce_ms=self.debounce
        )

        self.style = Style(theme=self.theme)  # set the ttkbootstrap theme


        if self.theme in ["darkly","cyborg","superhero","solar"]:
            self.style.configure('TButton', background=self.style.colors.dark,
                                            foreground=self.style.colors.light,
                                            bootstyle="success-outline")
        else:
            self.style.configure('TButton', background=self.style.colors.light, foreground=self.style.colors.dark)


        # open file from command line
        if len(sys.argv) > 1:
            self.filename = sys.argv[1]
            self.filepriv = self.filename
            self.load_file()
        elif self.open_last.lower() == "yes":
            if os.path.exists(lastpath):
                self.filename = open(lastpath, "r", encoding="utf-8").read().strip()
                if self.filename:
                    self.load_file()

    #-----------End of Init----------#

    def handle_drop(self, event):
        ''' This function runs when a file is dropped onto the app '''
        # Parse the dropped files list (handles spaces in file paths correctly)
        file_paths = self.master.splitlist(event.data)

        if file_paths:
            # The first file dropped
            file_path = os.path.abspath(file_paths[0])

            if os.path.isfile(file_path):
                # Call your existing file-opening method here
                self.dropfile = file_path
                self.open_file_window()


    def _get_selected_line_range(self, text: Text):
        ''' helper for tab routines '''
        try:
            first = text.index("sel.first")
            last = text.index("sel.last")
        except TclError:
            return None
        start_line = int(first.split(".")[0])
        last_included = text.index(f"{last} - 1c")
        end_line = int(last_included.split(".")[0])
        return start_line, end_line


    def _get_cursor_line_range(self, text: Text):
        # outdent just the line where INSERT is
        ins = text.index(INSERT)
        line = int(ins.split(".")[0])
        return line, line


    def on_tab(self, event=None):
        ''' handles block and 1 line tab '''
        text = event.widget
        bounds = self._get_selected_line_range(text)

        if not bounds:
            text.insert(INSERT, self.indent)
            return "break"

        start_line, end_line = bounds
        for ln in range(start_line, end_line + 1):
            text.insert(f"{ln}.0", self.indent)
        return "break"


    def on_shift_tab(self, event=None):
        ''' handles block and 1 line reverse tab '''
        text = event.widget
        bounds = self._get_selected_line_range(text)
        if not bounds:
            bounds = self._get_cursor_line_range(text)

        start_line, end_line = bounds
        indent_len = len(self.indent)

        for ln in range(start_line, end_line + 1):
            line_start = f"{ln}.0"

            # Remove only if line starts with exact INDENT
            current = text.get(line_start, f"{ln}.{indent_len}")
            if current == self.indent:
                text.delete(line_start, f"{ln}.{indent_len}")
            else:
                # Optional: remove up to indent_len spaces if present
                i = 0
                while i < indent_len:
                    ch = text.get(f"{ln}.{i}", f"{ln}.{i+1}")
                    if ch == " ":
                        i += 1
                    else:
                        break
                if i > 0:
                    text.delete(f"{ln}.0", f"{ln}.{i}")

        return "break"


    def on_return(self, event):
        ''' When Enter is pressed this causes autoindent '''
        widget = event.widget
        # Get the current line number and the text on that line
        current_line = widget.index("insert").split(".")[0]
        line_start = f"{current_line}.0"
        line_end = f"{current_line}.end"
        line_text = widget.get(line_start, line_end)
        # Count the leading spaces of the current line
        leading_spaces_count = len(line_text) - len(line_text.lstrip(' '))
        whitespace = " " * leading_spaces_count
        # Smart Indent: Check if the line ends with a colon (ignoring trailing whitespace)
        if line_text.rstrip().endswith(":"):
            whitespace += "    " # Add 4 extra spaces for the new block
        # Insert the newline character AND the calculated whitespace
        widget.insert(INSERT, "\n" + whitespace)
        # Automatically scroll the text widget to keep the cursor in view
        widget.see(INSERT)
        return "break" # Prevent Tkinter from inserting a second, default newline


    def toggle_line_comments(self, event=None):
        '''
        Toggle line comments in a Tkinter Text widget.

        Behavior:
        - If there is a selection, operate on all touched lines.
        - Otherwise operate on the current line.
        - For multi-line comment:
            insert comment marker at the minimum indentation shared by non-blank lines.
        - For uncomment:
            remove the marker if present at that same indentation position.
        - Uses '# ' for Python/shell-like files, otherwise '// '.
        '''
        text = self.text_area
        filename = self.filename

        HASH_EXTS = {".py", ".pyw", ".sh", ".bash", ".zsh", ".ksh"}

        ext = os.path.splitext(filename or "")[1].lower()
        comment = "# " if ext in HASH_EXTS else "// "
        raw_mark = comment.rstrip()   # "#" or "//"

        # Get selected/current line range
        try:
            start_idx = text.index("sel.first")
            end_idx = text.index("sel.last")
            has_selection = True
        except TclError:
            start_idx = text.index("insert")
            end_idx = text.index("insert")
            has_selection = False

        start_line = int(text.index(f"{start_idx} linestart").split(".")[0])

        # If selection ends at column 0 of the next line, don't include that next line
        if has_selection:
            end_line_idx = text.index(end_idx)
            end_line, end_col = map(int, end_line_idx.split("."))
            if end_col == 0 and end_line > start_line:
                end_line -= 1
            else:
                end_line = int(text.index(f"{end_idx} lineend").split(".")[0])
        else:
            end_line = int(text.index(f"{end_idx} lineend").split(".")[0])

        lines = [text.get(f"{ln}.0", f"{ln}.end") for ln in range(start_line, end_line + 1)]

        def leading_ws_count(s: str) -> int:
            i = 0
            while i < len(s) and s[i] in (" ", "\t"):
                i += 1
            return i

        nonblank_lines = [ln for ln in lines if ln.strip()]
        if not nonblank_lines:
            return

        # Minimum indentation among non-blank lines
        min_indent = min(leading_ws_count(ln) for ln in nonblank_lines)

        def line_has_comment_at_column(line: str, col: int) -> bool:
            if not line.strip():
                return True  # ignore blank lines in all()/toggle decision
            if len(line) < col:
                return False
            rest = line[col:]
            return rest.startswith(comment) or rest.startswith(raw_mark)

        should_uncomment = all(line_has_comment_at_column(ln, min_indent) for ln in nonblank_lines)

        new_lines = []

        if should_uncomment:
            for line in lines:
                if not line.strip():
                    new_lines.append(line)
                    continue

                if len(line) < min_indent:
                    new_lines.append(line)
                    continue

                before = line[:min_indent]
                rest = line[min_indent:]

                if rest.startswith(comment):          # "# " or "// "
                    rest = rest[len(comment):]
                elif rest.startswith(raw_mark):       # "#code" or "//code"
                    rest = rest[len(raw_mark):]
                    if rest.startswith(" "):
                        rest = rest[1:]

                new_lines.append(before + rest)
        else:
            for line in lines:
                if not line.strip():
                    new_lines.append(line)
                    continue

                col = min_indent
                before = line[:col]
                rest = line[col:]
                new_lines.append(before + comment + rest)

        block_start = f"{start_line}.0"
        block_end = f"{end_line}.end"
        text.delete(block_start, block_end)
        text.insert(block_start, "\n".join(new_lines))
        return "break"


    def surround_with_quote(self, event=None):
        ''' If text is selected and a quote character is typed,
        wrap the selection with that character instead of replacing it.
        Handles:  "  '  `
        '''
        quote_char = event.char   # the actual character typed

        # Only act when there IS a selection
        try:
            sel_start = self.text_area.index("sel.first")
            sel_end   = self.text_area.index("sel.last")
        except TclError:
            # No selection — let the keystroke behave normally
            return  # NOT "break" — allow normal insertion

        # Replace selection with  quote + text + quote
        selected_text = self.text_area.get(sel_start, sel_end)
        self.text_area.delete(sel_start, sel_end)
        self.text_area.insert(sel_start, f"{quote_char}{selected_text}{quote_char}")

        # Re-select the content BETWEEN the new quotes (optional but nice)
        new_sel_start = self.text_area.index(f"{sel_start} + 1 char")
        new_sel_end   = self.text_area.index(f"{sel_start} + {len(selected_text) + 1} char")
        self.text_area.tag_add("sel", new_sel_start, new_sel_end)

        return "break"


    def convert_to_uppercase(self, event=None):
        ''' Control-u '''
        try:
            # Check if there is a selection
            selected_text = self.text_area.get(SEL_FIRST, SEL_LAST)
            # Convert to uppercase
            upper_text = selected_text.upper()
            # Delete the selected text and insert the uppercase version
            self.text_area.delete(SEL_FIRST, SEL_LAST)
            self.text_area.insert(INSERT, upper_text)
        except TclError:
            # TclError is raised when there is no selection
            Messagebox.show_warning("Please select some text first.", "No Selection")


    def convert_to_lowercase(self, event=None):
        ''' Control-l '''
        try:
            # Check if there is a selection
            selected_text = self.text_area.get(SEL_FIRST, SEL_LAST)
            upper_text = selected_text.lower()
            self.text_area.delete(SEL_FIRST, SEL_LAST)
            self.text_area.insert(INSERT, upper_text)
        except TclError:
            # TclError is raised when there is no selection
            Messagebox.show_warning("Please select some text first.", "No Selection")


    def select_all(self, event=None):
        ''' Control-a Select All '''
        self.text_area.tag_add('sel', '1.0', 'end')
        self.text_area.mark_set('insert', '1.0')
        self.text_area.see('insert')
        return 'break'


    def strip_trailing_whitespace(self):
        ''' Remove trailing whitespace from every line in the text area.
        Only modifies lines that need changing, preserving all tags/highlights.
        Returns the number of lines modified. '''
        # Save cursor position
        cursor_pos = self.text_area.index("insert")

        # Get total number of lines
        last_line = int(self.text_area.index("end-1c").split(".")[0])

        lines_changed = 0

        for lineno in range(1, last_line + 1):
            line_start = f"{lineno}.0"
            line_end   = f"{lineno}.end"

            line_text  = self.text_area.get(line_start, line_end)
            stripped   = line_text.rstrip()

            if stripped != line_text:
                # Only delete the trailing whitespace characters — leave the rest intact
                # This preserves tags on the rest of the line
                trail_start = f"{lineno}.{len(stripped)}"
                self.text_area.delete(trail_start, line_end)
                lines_changed += 1
        # Restore cursor position
        try:
            self.text_area.mark_set("insert", cursor_pos)
        except TclError:
            self.text_area.mark_set("insert", "end")

        return lines_changed


    def toggle_wordwrap(self, event=None):
        ''' Control-W turns word wrap on and off. Always starts off. '''
        w = self.text_area['wrap']
        if w == 'none':
            self.text_area.config(wrap="word")
            toast(" Word Wrap On ", 1900)
        else:
            self.text_area.config(wrap="none")
            toast(" Word Wrap OFF ", 1900)
        return "break"


    def open_options(self, event=None):
        ''' loads the tkedit.ini file for editing '''
        self.filename = str(inipath)
        self.load_file()
        Messagebox.show_info("TKedit must restart for saved changes to take effect.", "Settings")


    def load_file(self):
        ''' helper method to find file type and display content for editing
            With no extention assume text/.txt - no highlighting
            Also when ext not found assume text/.txt '''
        lang = self.extension_get_language() # set the file type via its extension
        if self.has_highlight:
            self.highlighter.set_language(lang)
        else:
            self.highlighter.set_language("text")
        try:
            with open(self.filename, "r", encoding="utf-8") as file:
                content = file.read()
                self.text_area.delete("1.0", END)
                self.text_area.insert(END, content)
                self.is_dirty = False
                self.text_area.edit_modified(False)
                self.master.title((self.filename or "Untitled"))
                self.highlighter.highlight()

        except Exception as e:
            # assume new file unless open_last
            if self.open_last.lower() == 'yes':
                Messagebox.show_warning("last file not found", "No File Warning")
                self.filename = None
                self.open_last = None
                return "break"
        self.text_area.focus_set()
        return "break"


    def on_modified(self, event=None):
        ''' tkinter sets a modified flag
            Primarily for tklinenums
        '''
        root.after_idle(self.linenums.redraw)  # for line number changes
        if self.text_area.edit_modified():
            self.master.title("*" + (self.filename or "Untitledd"))
            self.is_dirty = True
            self.text_area.edit_modified(False)


    def open_terminal(self, event=None):
        ''' Open the system terminal in the current file directory '''
        current_dir = os.path.dirname(self.filename) if self.filename else "."
        if platform.system() == "Windows":
            subprocess.Popen([self.terminal, "-d", current_dir])
        elif platform.system() == "Darwin":
            # for MacOS - ignores config setting
            subprocess.Popen(["open", "-n", "-a", "Terminal"])
        else:
            # for: GNOME Terminal, MATE Terminal, XFCE4 Terminal, Tilix, Terminator, LXTerminal, Alacritty
            subprocess.Popen([self.terminal, "--working-directory="+current_dir])
        return "break"


    def open_file_manager(self, event=None):
        ''' Open the system File Manager in the current directory '''
        current_dir = os.path.dirname(self.filename) if self.filename else "."
        subprocess.Popen([self.filemanager, current_dir])
        return "break"


    def write_html(self, md_text: str, outpath_html: str) -> bool:
        ''' convert MD to HTML and write file '''
        H = markdown.markdown(md_text,
                              extensions=['tables','fenced_code'])
        # write to file
        try:
            open(outpath_html, 'w', encoding='utf-8').write(H)
        except:
            return False
        return True


    def md_to_html_path(self, md_path):
        '''Return the path for the .html file that matches md_path's directory and base name.'''
        p = Path(md_path)
        if p.is_dir():
            raise ValueError("md_path is a directory, expected a file path")
        return str(p.with_suffix('.html'))


    def prompt_save_changes(self) -> bool:
        res = Messagebox.yesno(
            f"Do you want to save changes to {self.filename} first?",
            "Save File First?"
        )
        if res == "No":
            return False
        else:
            return True


    def new_file(self, event=None):
        ''' Creating a new file. Prompt to save an opened file. '''
        if self.filename and self.is_dirty:
            if self.prompt_save_changes():
                self.save_file()
        self.filename = None
        self.text_area.delete("1.0", END)
        self.master.title((self.filename or "Untitled"))
        self.is_dirty = False
        self.highlighter.set_language("text")
        self.highlighter.highlight()
        self.text_area.focus_set()
        return "break"


    def open_file(self, event=None):
        ''' Open an existing file. Prompt to save opened file. '''
        if self.filename and self.is_dirty:
            if self.prompt_save_changes():
                self.save_file()

        current_dir = os.path.dirname(self.filename) if self.filename else "."

        if self.filename:
            self.filepriv = self.filename

        self.filename = filedialog.askopenfilename(initialdir=current_dir,
                                                   title="Select File",
                                                   filetypes=(("All files", "*"),
                                                             ("Text files", "*.txt"),
                                                             ("Python files", "*.py")))
        if self.filename:
            self.load_file()
        return "break"


    def load_previous(self, event=None):
        ''' opens this session's previously opened file '''
        if self.filepriv:
            filename = self.filepriv
            self.filepriv = self.filename
            self.filename = filename
            self.load_file()
        return "break"


    def open_file_window(self, event=None):
        ''' Open an existing file in a new tkedit instance. '''
        if not self.dropfile:
            if self.filename and self.is_dirty:
                if self.prompt_save_changes():
                    self.save_file()

            current_dir = os.path.dirname(self.filename) if self.filename else "."

            file = filedialog.askopenfilename(initialdir=current_dir,
                                                       title="Select File",
                                                       filetypes=(("All files", "*"),
                                                                 ("Text files", "*.txt"),
                                                                 ("Python files", "*.py")))
        else:
            file = self.dropfile
            self.dropfile = None

        if file:
            # Assumes tkedit.pyc is the compiled target (may not work on Windows)
            if platform.system() == "Windows":
                subprocess.Popen(["pythonw.exe", self.appath, file])
            else:
                subprocess.Popen([self.appath, file])
        return "break"


    def save_file(self, event=None):
        ''' Save opened file, or Save-As if no changes. '''
        if self.filename:
            try:
                with open(lastpath, "w", encoding="utf-8") as fout:
                    fout.write(self.filename)
                if self.nospaces == 'yes' and self.filename.endswith(".md") is False:
                    self.strip_trailing_whitespace()
                with open(self.filename, "w", encoding="utf-8") as file:
                    content = self.text_area.get("1.0", "end-1c")
                    file.write(content)
                    self.text_area.edit_modified(False)
                    self.is_dirty = False
                    self.master.title((self.filename or "Untitled"))
                    self.rf_manager.add_file(self.filename)
                    if self.md2html == 'yes' and self.filename.endswith(".md"):
                        htmlpath = self.md_to_html_path(self.filename)
                        rc = self.write_html(content, htmlpath)
                        if rc is False:
                            Messagebox.show_error("Could not write HTML from MD file", "Error Save")
                    if self.backups == 'yes':
                        self.backup_write_for(self.filename)
                    self.text_area.focus_set()
            except Exception as e:
                Messagebox.show_error("Could not save file: " + str(e), "Error")
                return
        else:
            # filename was None
            self.save_file_as()
        return "break"


    def save_file_as(self, event=None):
        ''' Save opened file as a different/new file
        as with Save going to consider markdown and handle spaces as directed '''
        current_dir = os.path.dirname(self.filename) if self.filename else "."
        self.filename = filedialog.asksaveasfilename(initialdir = current_dir,
                                                     title = "Save File As",
                                                     filetypes = (("All files", "*"),
                                                                 ("Text files", "*.txt"),
                                                                 ("Python files", "*.py")))
        if self.filename:
            if self.filename is not None:
                with open(lastpath, "w", encoding="utf-8") as fout:
                    fout.write(self.filename)
            lang = self.extension_get_language() # set the file type via its extension
            if self.has_highlight:
                self.highlighter.set_language(lang)
            try:
                if self.nospaces == 'yes' and self.filename.endswith(".md") is False:
                    self.strip_trailing_whitespace()
                with open(self.filename, "w", encoding="utf-8") as file:
                    content = self.text_area.get("1.0", END)
                    file.write(content)
                    self.text_area.edit_modified(False)
                    self.is_dirty = False
                    if self.has_highlight:
                        self.highlighter.highlight()
                    self.master.title((self.filename or "Untitled"))
                    self.rf_manager.add_file(self.filename)
                    if self.md2html == 'yes' and self.filename.endswith(".md"):
                        htmlpath = self.md_to_html_path(self.filename)
                        rc = self.write_html(content, htmlpath)
                        if rc is False:
                            Messagebox.show_error("Could not write HTML from MD file", "Error Save_As")
                    if self.backups == 'yes':
                        self.backup_write_for(self.filename)
            except Exception as e:
                Messagebox.show_error("Could not save file: " + str(e), "Error")
            return "break"


    def open_file_recent(self, event=None):
        '''Creates the Toplevel UI window to select a recent file.'''
        if self.filename and self.is_dirty:
            if self.prompt_save_changes():
                self.save_file()

        recent_list = self.rf_manager.files

        if not recent_list:
            Messagebox.show_info("No recent files found.", "Recent Files")
            return

        # Create Toplevel popup
        popup = Toplevel(self)
        popup.title("Open Recent File")
        popup.geometry("450x400")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)

        # Ensure focus goes to the popup
        popup.grab_set()

        # Label instruction
        lbl = Label(popup, text="Select a file to open:", font=("Helvetica", 10, "bold"))
        lbl = Label(popup, text="Select a file to open:")
        lbl.pack(anchor=W, padx=15, pady=(15, 5))

        # Listbox Wrapper Frame (for scrollbar attachment)
        list_frame = Frame(popup)
        list_frame.pack(fill=BOTH, expand=YES, padx=15, pady=5)

        scrollbar = Scrollbar(list_frame, orient=VERTICAL)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Listbox with ttkbootstrap styling attributes
        listbox = Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Sans", 10),
            # bg="#2b2b2b", # Matching the 'darkly' theme background style
            # fg="#ffffff",
            # selectbackground="#00bc8c", # Accent color
            # activestyle="none",
            borderwidth=0
        )
        listbox.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar.config(command=listbox.yview)

        # Populate Listbox
        for file_path in recent_list:
            if os.path.isfile(file_path):  # need to weed out deleted files
                listbox.insert(END, file_path)

        # Helper function to capture selection and load file
        def open_selected():
            selection = listbox.curselection()
            if selection:
                chosen_file = listbox.get(selection[0])
                if self.filename:
                    self.filepriv = self.filename
                self.filename = chosen_file
                self.load_file()
                popup.destroy()

        # Handle Double Click selection shortcut
        listbox.bind("<Double-1>", lambda event: open_selected())

        # Action Buttons Layout
        btn_frame = Frame(popup)
        btn_frame.pack(fill=X, side=BOTTOM, padx=15, pady=15)

        cancel_btn = Button(btn_frame, text="Cancel", command=popup.destroy)
        cancel_btn.pack(side=RIGHT, padx=5)

        open_btn = Button(btn_frame, text="Open File", command=open_selected)
        open_btn.pack(side=RIGHT, padx=5)


    def backup_name_for(self, path, date=None, prefix="bkup_"):
        '''
        Given a path (string or Path), return a Path for the backup file
        named: bkup_<original-base>_<yymmdd>.<ext>
        - <ext> is the same final extension as the original (without leading dot).
        - If the original has no extension, the backup will have no trailing extension.
        '''
        p = Path(path)
        if date is None:
            date = datetime.now()
        yymmdd = date.strftime("%y%m%d")
        if p.suffix:                     # p.suffix includes the leading dot, e.g. ".txt"
            ext = p.suffix.lstrip(".")
            base = p.name[:-len(p.suffix)]   # remove the final suffix from the name
        else:
            ext = ""
            base = p.name
        bname = f"{prefix}{base}_{yymmdd}"
        if ext:
            bname = f"{bname}.{ext}"

        return str(p.parent / bname)


    def backup_write_for(self, filename):
        ''' name the backup file,
            get the content,
            Write the backup file '''
        content = self.text_area.get("1.0", "end-1c")
        bfile = self.backup_name_for(filename)
        with open(bfile, "w", encoding="utf-8") as fout:
            fout.write(content)


    def extension_get_language(self) -> str:
        '''Given a filename with extension, return the corresponding language.'''
        # Get the file extension from Path
        ext = '.' + self.filename.split('.')[-1]
        self.has_highlight = True
        # Find the index in lx and return language
        if ext in lx:
            index = lx.index(ext)
            return lex[index]
        else:
            self.has_highlight = False
            return None


    def return_selection(self):
        ''' Used with Find, Replace functions '''
        try:
            # "sel.first" and "sel.last" are the start and end of the selection
            selected_text = self.text_area.get("sel.first", "sel.last")
            return selected_text
        except TclError:
            # This error triggers if the "sel" tag doesn't exist anywhere
            # print("Nothing is selected.")
            return ""


    def find_text(self, event=None):
        ''' Ask the user for the text to search
            then find and highlight the text if found.'''
        look = self.return_selection()
        # term = simpledialog.askstring("Find", "Enter text to search:", initialvalue=look)
        term = Querybox.get_string(
            prompt="Search for:",
            title="Find Text",
            initialvalue=look  # Optional: sets default text in the field
        )

        if term:
            self.search_term = term
            # Remove any previous highlights.
            self.text_area.tag_remove("highlight", "1.0", END)
            self.last_found_index = self.text_area.index("insert")  # start searching at current position
            pos = self.text_area.search(self.search_term, self.last_found_index, stopindex=END)
            if pos:
                # highlight the found text.
                end_pos = f"{pos}+{len(self.search_term)}c"
                # Adjust the view to make the found text visible.
                self.text_area.see(pos)
                # Store the ending position for finding the next match.
                self.last_found_index = end_pos
                self.text_area.tag_add("highlight", pos, end_pos)
            else:
                Messagebox.show_info("No matches found.", "Result")
        return "break"  # Prevent the default behavior.


    def find_next(self, event=None):
        ''' Search for next occurrence of text in response text area (self.txt) '''
        if not self.search_term:
            return self.find_text()

        pos = self.text_area.search(self.search_term, self.last_found_index, stopindex=END)
        if pos:
            # Remove previous highlights so only the current match is highlighted.
            self.text_area.tag_remove("highlight", "1.0", END)
            end_pos = f"{pos}+{len(self.search_term)}c"
            # --- CURSOR FIXES START HERE ---
            self.text_area.mark_set("insert", pos)
            # Force focus back to the text area so the cursor actively blinks
            self.text_area.focus_set()
            # --- CURSOR FIXES END HERE ---
            self.text_area.see(pos)
            # Update the last found index.
            self.last_found_index = end_pos
            self.text_area.tag_add("highlight", pos, end_pos)
        else:
            # Messagebox.show_info("No more matches found.", "Result")
            self.last_found_index = "1.0"  # back to "top" and start over
            self.text_area.tag_remove("highlight", "1.0", END)
        return "break"  # Prevent the default behavior.


    def display_help(self, event=None):
        ''' launch README.html '''
        html_path = Path(__file__).resolve().parent / "README.html"
        webbrowser.open_new_tab(html_path.as_uri())  # opens in default browser
        return "break"


    def close_file(self, event=None):
        ''' Closing the file also closes the program
        Geometry is saved into winfo file '''
        if self.filename is not None:
            with open(lastpath, "w", encoding="utf-8") as fout:
                fout.write(self.filename)
        if self.is_dirty:
            if self.prompt_save_changes():
                self.save_file()
        self.rf_manager.save_to_disk()
        with open(winpath, "w", encoding="utf-8") as fout:
            fout.write(root.geometry())
        self.master.destroy()  # Properly close the window.


    def find_replace(self, event=None):
        '''Open a dialog to find and replace text.'''
        # Create a custom dialog window
        look = self.return_selection()
        dialog = Toplevel(self.master)
        dialog.title("Find and Replace")
        dialog.geometry("500x250")
        # dialog.resizable(False, False)

        # Find label and entry
        Label(dialog, text="Find:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        find_entry = Entry(dialog, width=40)
        find_entry.grid(row=0, column=1, padx=10, pady=5)
        find_entry.insert(0, look)
        find_entry.focus()

        # Replace label and entry
        Label(dialog, text="Replace with:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        replace_entry = Entry(dialog, width=40)
        replace_entry.grid(row=1, column=1, padx=10, pady=5)

        # Case sensitive checkbox
        case_var = BooleanVar()
        case_check = Checkbutton(dialog, text="Case sensitive", variable=case_var)
        case_check.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        # Result label
        result_label = Label(dialog, text="")
        result_label.grid(row=3, column=0, columnspan=2, pady=5)

        def replace_one():
            '''Replace the next occurrence.'''
            find_text = find_entry.get()
            replace_text = replace_entry.get()

            if not find_text:
                Messagebox.show_warning("Please enter text to find.", "Warning")
                return

            # Remove previous highlights
            self.text_area.tag_remove("highlight", "1.0", END)

            # Initialize search position if not set or invalid
            # start at current insertion point
            search_pos = getattr(self, 'last_found_index', "1.0")
            if not search_pos or search_pos == "0":
                search_pos = "1.0"

            # Search options
            nocase = not case_var.get()
            pos = self.text_area.search(find_text, search_pos,
                                         stopindex=END, nocase=nocase)

            if pos:
                end_pos = f"{pos}+{len(find_text)}c"
                # Replace the text
                self.text_area.delete(pos, end_pos)
                self.text_area.insert(pos, replace_text)
                # Highlight the replacement
                new_end_pos = f"{pos}+{len(replace_text)}c"
                self.text_area.tag_add("highlight", pos, new_end_pos)
                self.text_area.see(pos)
                self.last_found_index = new_end_pos
                result_label.config(text="Replaced 1 occurrence.", foreground="green")
            else:
                result_label.config(text="No matches found.", foreground="red")
                self.last_found_index = "1.0"  # Reset for next search

        def replace_all():
            '''Replace all occurrences.'''
            find_text = find_entry.get()
            replace_text = replace_entry.get()

            if not find_text:
                Messagebox.show_warning("Please enter text to find.", "Warning")
                return

            # Remove previous highlights
            self.text_area.tag_remove("highlight", "1.0", END)

            # Search and replace all
            nocase = not case_var.get()
            count = 0
            search_pos = "1.0"

            while True:
                pos = self.text_area.search(find_text, search_pos,
                                            stopindex=END, nocase=nocase)
                if not pos:
                    break

                end_pos = f"{pos}+{len(find_text)}c"
                self.text_area.delete(pos, end_pos)
                self.text_area.insert(pos, replace_text)
                count += 1
                search_pos = f"{pos}+{len(replace_text)}c"

            # Reset for next search
            self.last_found_index = "1.0"

            if count > 0:
                result_label.config(
                    text=f"Replaced {count} occurrence{'s' if count != 1 else ''}.",
                    foreground="green"
                )
            else:
                result_label.config(text="No matches found.", foreground="red")

        def on_close():
            '''Remove highlights before closing dialog.'''
            self.text_area.tag_remove("highlight", "1.0", END)
            if self.has_highlight:
                self.highlighter.highlight()
            dialog.destroy()

        # Buttons frame
        button_frame = Frame(dialog)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)

        Button(button_frame, text="Replace", command=replace_one, width=12).pack(side="left", padx=5)
        Button(button_frame, text="Replace All", command=replace_all, width=12).pack(side="left", padx=5)
        # Button(button_frame, text="Close", command=dialog.destroy, width=12).pack(side="left", padx=5)
        Button(button_frame, text="Close", command=on_close, width=12).pack(side="left", padx=5)
        return "break"


    def copy_all(self, panel):
        ''' copys entire loaded file to clipblard '''
        panel.focus()
        panel.tag_add(SEL, '1.0', END)
        panel.mark_set(INSERT, '1.0')
        panel.see(INSERT)
        root.clipboard_clear()  # clear clipboard contents
        if panel.tag_ranges("sel"):  # append new value to clipbaord
            root.clipboard_append(panel.selection_get())
            panel.tag_remove(SEL, "1.0", END)


    def paste(self, event=None):
        ''' replaces system "paste" function '''
        try:
            clip = root.clipboard_get()
        except TclError:
            return "break"

        ta = self.text_area

        if ta.tag_ranges("sel"):  # there is a selection
            start = ta.index("sel.first")
            end   = ta.index("sel.last")
            ta.delete(start, end)
            ta.insert(start, clip)
        else:
            inx = ta.index(INSERT)
            ta.insert(inx, clip)
        return "break"


    def has_selection(self, text_widget) -> bool:
        # "sel" is the selection tag in Tk Text widgets
        ranges = text_widget.tag_ranges("sel")
        return bool(ranges) and (text_widget.compare(ranges[0], "!=", ranges[1]))


    def poptxt(self, n):
        ''' Routes txt context menu actions '''
        if n == 1:  # Copy
            if self.has_selection(self.text_area):
                content = self.text_area.selection_get()
                root.clipboard_clear()  # clear clipboard contents
                root.clipboard_append(self.text_area.selection_get())  # append new value to clipbaord
            else:
                Messagebox.show_warning("Nothing Selected", "Copy")
        elif n == 2:  # Paste
            self.paste()  # revised paste function
        elif n == 3:  # Select All
            self.copy_all(self.text_area)
        elif n == 4:  # find text in the response window
            self.find_text()
        elif n == 5:  # find text in the response window
            self.find_replace()
        elif n == 6:   # search for selected text using browser
            if self.has_selection(self.text_area):
                search = self.text_area.selection_get()
                webbrowser.open("https://www.google.com/search?q=" + search)
            else:
                Messagebox.show_warning("Nothing Selected", "Internet Search")
        elif n == 7:  # Recent Files Picker
            self.open_file_recent()


    def show_popup(self, event=None):
        ''' display the context menu in the editor '''
        popup = Toplevel(self.master)
        popup.wm_overrideredirect(True)  # no window decorations
        popup.attributes("-topmost", True)
        popup.geometry("+%d+%d" % (event.x_root, event.y_root))

        frame = Frame(popup)
        frame.pack()

        items = [
            ("Copy", lambda: (popup.destroy(), self.poptxt(1))),
            ("Paste", lambda: (popup.destroy(), self.poptxt(2))),
            ("Copy All", lambda: (popup.destroy(), self.poptxt(3))),
            ("Find Text", lambda: (popup.destroy(), self.poptxt(4))),
            ("Replace Text", lambda: (popup.destroy(), self.poptxt(5))),
            ("Internet Search", lambda: (popup.destroy(), self.poptxt(6))),
            ("Open Recents", lambda: (popup.destroy(), self.poptxt(7))),
            ("Close", lambda: (popup.destroy())),
        ]

        for text, cmd in items:
            b = Button(frame, text=text, command=lambda c=cmd: (popup.destroy(), c()))
            b.pack(fill="x", padx=8, pady=4)  # padding around each item


    def select_token(self, event):
        ''' handles the double-click selection criteria '''
        # get index of click
        idx = self.text_area.index("@%d,%d" % (event.x, event.y))
        line_no, col = map(int, idx.split('.'))
        # get the full line
        line = self.text_area.get(f"{line_no}.0", f"{line_no}.end")
        # find the token that contains the clicked column
        for m in word_re.finditer(line):
            if m.start() <= col < m.end():
                start = f"{line_no}.{m.start()}"
                end   = f"{line_no}.{m.end()}"
                self.text_area.tag_remove("sel", "1.0", "end")
                self.text_area.tag_add("sel", start, end)
                self.text_area.mark_set("insert", end)
                self.text_area.see("insert")
                break
        else:
            # optional: if click on a separator, select that single char
            if 0 <= col < len(line):
                start = f"{line_no}.{col}"
                end   = f"{line_no}.{col+1}"
                self.text_area.tag_remove("sel", "1.0", "end")
                self.text_area.tag_add("sel", start, end)
        return "break"   # stop default handler


    def about(self, event=None):
        ''' Display Messagebox with settings info and author info '''
        msg = f''' CURRENT CONFIG
font: {self.fontname}
font size: {self.fontsize}
theme: {self.theme}
highlight: {self.color}
open last: {self.open_last}
tab size: {self.tabsize}
terminal: {self.terminal}
file manager: {self.filemanager}
backup: {self.backups}
app path: {self.appath}
auto indent: {self.autoindent}
no trail spaces: {self.nospaces}
md to HTML: {self.md2html}
debounce: {self.debounce}

Author: Michael Leidel
        https://github.com/Mleidel

favorite themes:
    solar / paraiso-dark
    cyborg / material
    darkly / gruvbox-dark
    superhero / monokai
    darkly / zenburn
'''
        Messagebox.show_info(msg, "About")


    def hotkeys(self, event=None):
        ''' Messagebox with hotkey assignments '''
        if platform.system() != "Darwin":
            msg = '''
SPECIAL KEYS    DESCRIPTION

Control-o ... Open File
Control-n ... New File
Control-p ... Open Previous File
Control-Shift-O ... Open Recent File List
Control-Shift-W ... Open File New Window
Control-Shift-S ... Save-As File
Control-s ... Save File
Control-q ... Close App
Control-u ... uppercase
Control-l ... lowercase
Control-f ... Find Text
F3 ... Find Next
Control-h ... Find - Replace Text
Control-w ... Toggle Word wrap
Control-a ... Select All
Control-Shift-T ... Open Terminal
Control-Shift-F ... Open File Manager
Control-Slash ... Toggle Line Comment
Alt-z ... snippets
Shift-Control-Z ... snippets (for Mac)
'''
        else:
            msg = '''
SPECIAL KEYS    DESCRIPTION

Command-o ... Open File
Command-n ... New File
Command-p ... Open Previous File
Command-Shift-O ... Open Recent File List
Command-Shift-W ... Open File New Window
Command-Shift-S ... Save-As File
Command-s ... Save File
Command-q ... Close App
Command-u ... uppercase
Command-l ... lowercase
Command-f ... Find Text
F3 ... Find Next
Command-h ... Find - Replace Text
Command-w ... Toggle Word wrap
Command-a ... Select All
Command-Shift-T ... Open Terminal
Command-Shift-F ... Open File Manager
Command-Slash ... Toggle Line Comment
Alt-z ... snippets
Shift-Command-Z ... snippets (for Mac)
'''
        Messagebox.show_info(msg, "Key Commands")

    # Autopairs

    def enable_autopairs(self, text_widget: Text):
        ''' bracketing selections '''
        PAIRS = {"(": ")", "[": "]", "{": "}"}
        CLOSERS = {")", "]", "}"}

        def on_keypress(event):
            ch = event.char

            # Typing opener: insert opener+closer and put caret between
            if ch in PAIRS and event.keysym not in ("BackSpace", "Return"):
                cur = text_widget.index(INSERT)
                opener = ch
                closer = PAIRS[opener]

                text_widget.insert(cur, opener + closer)
                text_widget.mark_set(INSERT, f"{cur} + 1c")  # between
                return "break"

            # Typing closer: if caret is right before it, just move past it
            if ch in CLOSERS:
                cur = text_widget.index(INSERT)

                if text_widget.compare(cur, ">", "1.0"):
                    before = text_widget.get(f"{cur} - 1c", cur)
                    if before == ch:
                        text_widget.mark_set(INSERT, f"{cur} + 1c")
                        return "break"

            return None

        # Only intercept key presses; no caret “fix” on mouse/selection changes.
        text_widget.bind("<KeyPress>", on_keypress, add="+")
        return text_widget


    # snippets

    def open_snippet_window(self, event=None):
        SnippetWindow(self, self.text_area, self.highlighter, snipdir)


    # Bookmarks

    def toggle_bookmark(self, event):
        ''' Control-Slash toggles a bookmark '''
        # Determine which line was clicked based on the mouse coordinate
        self.text = self.text_area
        click_index = self.text.index(f"@{event.x},{event.y}")
        line_num = int(click_index.split(".")[0])

        if line_num in self.bookmarks:
            # Remove bookmark
            self.bookmarks.remove(line_num)
            self.text.tag_remove("bookmark", f"{line_num}.0", f"{line_num + 1}.0")
            toast(f" Removed Bookmark line {line_num} ", 1900)
        else:
            # Add bookmark
            self.bookmarks.add(line_num)
            self.text.tag_add("bookmark", f"{line_num}.0", f"{line_num + 1}.0")
            toast(f" Added Bookmark line {line_num} ", 1900)

        # Force tklinenums to redraw if needed
        self.linenums.redraw()
        return "break" # Prevents default Tkinter behavior for Ctrl+Click


    def next_bookmark(self, event=None):
        ''' Jump to next bookmark '''
        self.text = self.text_area
        if not self.bookmarks:
            toast(" No bookmarks set. ", 1900)
            return "break"

        # Get current cursor line
        current_line = int(self.text.index("insert").split(".")[0])

        # Sort bookmarks to look through them sequentially
        sorted_bookmarks = sorted(list(self.bookmarks))

        # Find the next bookmark that is greater than the current line
        next_line = None
        for b in sorted_bookmarks:
            if b > current_line:
                next_line = b
                break

        # Wrap around to the first bookmark if no "next" bookmark is found
        if next_line is None:
            next_line = sorted_bookmarks[0]

        # Move the cursor and scroll to that line
        self.text.mark_set("insert", f"{next_line}.0")
        self.text.see(f"{next_line}.0")
        # toast(f" Jumped to bookmark line {next_line} ", 1900)
        return "break"

    def clear_bookmarks(self, event=None):
        ''' Remove all bookmarks '''
        # Clear the tracking set
        self.text = self.text_area
        self.bookmarks.clear()
        # Remove visual highlights from the entire text widget
        self.text.tag_remove("bookmark", "1.0", "end")
        self.linenums.redraw()
        toast(" Cleared All bookmarks. ", 1900)
        return "break"

# Startup Splash: needed to initialize theme for dialogs

def auto_close_entry_dialog(master, close_ms=3000, width_chars=12):
    '''
    Opens a small borderless dialog with a single Entry.
    Auto-closes after close_ms milliseconds.
    Returns the entry value when closed. '''
    dlg = Toplevel(master)
    dlg.transient(master)
    dlg.resizable(False, False)
    dlg.grab_set()

    # Borderless (no caption bar)
    dlg.overrideredirect(True)

    # Size + center over parent
    w, h = 140, 100
    master.update_idletasks()
    x = master.winfo_rootx() + (master.winfo_width() // 2) - (w // 2)
    y = master.winfo_rooty() + (master.winfo_height() // 2) - (h // 2)
    dlg.geometry(f"{w}x{h}+{x}+{y}")

    entry = Entry(dlg, width=width_chars)
    entry.place(x=15, y=28, width=w - 30)
    entry.insert(0, "  T K e d i t")
    entry.config(font="Sans, 15")
    entry.focus_set()

    def close():
        try:
            dlg.grab_release()
        except TclError:
            pass
        dlg.destroy()
        master.lift() # bring focus to main window
        master.focus_force()
        master.focus_set()

    dlg.after(close_ms, close)
    # Block until closed
    master.wait_window(dlg)

# LittleToster

def toast(t_text, t_time=2000):
    '''
    Display a small message for a short time in the upper-left corner of the
    parent window.

    - parent: a tkinter widget (usually the root window)
    - t_text: string to display
    - t_time: duration in milliseconds
    '''
    top = root.winfo_toplevel()
    top.update_idletasks()
    x = top.winfo_rootx()
    y = top.winfo_rooty()
    t = Toplevel(top)
    t.overrideredirect(True)          # no window decorations (toast-style)
    t.attributes('-topmost', True)    # keep on top
    t.geometry(f'+{x}+{y}')
    l = Label(
        t,
        text=t_text,
        font=("Sans", 14, "bold"),
        background="black",
        foreground="white",
    )
    l.pack()  # or use grid() if you prefer

    t.overrideredirect(True)
    t.update_idletasks()
    top.after(t_time, t.destroy)


# Recent Files Manager class

class RecentFilesManager:
    ''' Class to display and manage the recent file window '''
    def __init__(self, filename="recent_files.json", limit=15):
        self.filename = str(recents)
        self.limit = limit
        self.files = self.load_from_disk()

    def load_from_disk(self):
        '''Loads the recent files list from a JSON file.'''
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as fi:
                    data = json.load(fi)
                    return data if isinstance(data, list) else []
            except Exception:
                Messagebox.show_error("Recent Files Load Disk", "Exception")
                return [] # Fallback if file is corrupted
        Messagebox.show_error("Recent Files Path not found", "Exception")
        return []

    def add_file(self, file_path):
        '''Adds a file to the top of the list, enforcing uniqueness and the limit.'''
        if not file_path:
            return

        file_path = os.path.abspath(file_path)

        # If it already exists, remove it so it can be bumped to the top
        if file_path in self.files:
            self.files.remove(file_path)

        # Insert at the beginning of the list
        self.files.insert(0, file_path)

        # Enforce the 10-file limit
        if len(self.files) > self.limit:
            self.files = self.files[:self.limit]

    def save_to_disk(self):
        '''Writes the current list to disk.'''
        try:
            with open(self.filename, "w", encoding="utf-8") as fi:
                json.dump(self.files, fi, indent=4)
        except Exception as e:
            print(f"Error saving recent files: {e}")
            Messagebox.show_error(e, "Saving Recent Files")




class SnippetWindow(Toplevel):
    '''  '''
    def __init__(self, master, editor_text, highlighter, snippet_dir="snippets"):
        super().__init__(master)
        self.title("Snippets")
        self.geometry("450x500")
        self.minsize(350, 300)
        self.attributes("-topmost", True)

        self.editor_text = editor_text
        self.snippet_dir = Path(snippet_dir)
        self.highlighter = highlighter
        self.snippet_dir.mkdir(parents=True, exist_ok=True)

        self.protocol("WM_DELETE_WINDOW", self.close_window)

        self._build_ui()
        self.reload_snippets()

    def _build_ui(self):
        ''' Build Snippets Window containing a listbox '''
        frame = Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        list_frame = Frame(frame)
        list_frame.pack(fill="both", expand=True)

        self.listbox = Listbox(
            list_frame,
            selectmode=EXTENDED,
            activestyle="dotbox"
        )
        self.listbox.pack(side="left", fill="both", expand=True)

        scrollbar = Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        # Buttons
        btn_frame = Frame(frame, padding=(0, 10, 0, 0))
        btn_frame.pack(fill="x")

        self.insert_btn = Button(btn_frame, text="Insert", command=self.insert_snippets)
        ToolTip(self.insert_btn,
                text="insert into current open file",
                bootstyle=(INVERSE),
                wraplength=80)

        self.add_btn = Button(btn_frame, text="Add", command=self.add_snippet)
        ToolTip(self.add_btn,
                text="Make snippet from clipboard content",
                bootstyle=(INVERSE),
                wraplength=80)

        self.delete_btn = Button(btn_frame, text="Delete", command=self.delete_snippets)
        self.close_btn = Button(btn_frame, text="Close", command=self.close_window)

        self.insert_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.add_btn.pack(side="left", expand=True, fill="x", padx=5)
        self.delete_btn.pack(side="left", expand=True, fill="x", padx=5)
        self.close_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))

    def reload_snippets(self):
        '''Read snippet filenames from the directory and display them sorted.'''
        self.listbox.delete(0, END)

        files = sorted(
            [p.name for p in self.snippet_dir.iterdir() if p.is_file()]
        )

        for fname in files:
            self.listbox.insert(END, fname)

    def get_selected_files(self):
        '''Return list of selected filenames in listbox order.'''
        selected_indices = self.listbox.curselection()
        return [self.listbox.get(i) for i in selected_indices]

    def insert_snippets(self):
        '''Insert selected snippet files into the editor Text widget.'''
        selected_files = self.get_selected_files()

        if not selected_files:
            Messagebox.show_info("Please select one or more snippets.", "Insert Snippet")
            return

        snippets = []
        for fname in selected_files:
            path = self.snippet_dir / fname
            try:
                with open(path, "r", encoding="utf-8") as f:
                    snippets.append(f.read())
            except Exception as e:
                Messagebox.show_error(f"Could not read {fname}:\n{e}", "Insert Snippet")
                return

        insert_text = "\n\n".join(snippets)
        self.editor_text.insert(INSERT, insert_text)
        self.highlighter.highlight()

    def add_snippet(self):
        '''Prompt for filename and write clipboard contents to a new snippet file.'''
        # fname = simpledialog.askstring("Add Snippet", "Enter snippet file name:")
        fname = Querybox.get_string(
            prompt="Enter snippet file name:",
            title="Add Snippet"
        )

        if not fname:
            return

        fname = fname.strip()

        # Optional: if user did not include extension, add one
        # if not os.path.splitext(fname)[1]:
        #     fname += ".txt"

        path = self.snippet_dir / fname

        try:
            clipboard_text = self.clipboard_get()
        except TclError:
            Messagebox.show_error("Clipboard is empty or unavailable.", "Add Snippet")
            return

        if path.exists():
            overwrite = Messagebox.yesno(
                f"Snippet '{fname}' already exists.\nOverwrite it?",
                "Overwrite Snippet"
            )
            if overwrite == "No":
                return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(clipboard_text)
        except Exception as e:
            Messagebox.show_error(f"Could not write snippet:\n{e}", "Add Snippet")
            return

        self.reload_snippets()
        Messagebox.show_info(f"Snippet '{fname}' saved.", "Add Snippet")

    def delete_snippets(self):
        '''Delete selected snippet files.'''
        selected_files = self.get_selected_files()

        if not selected_files:
            Messagebox.show_info("Please select one or more snippets.", "Delete Snippet")
            return

        confirm = Messagebox.yesno(
            f"Delete {len(selected_files)} selected snippet(s)?",
            "Delete Snippet"
        )
        if confirm == "No":
            return

        errors = []
        for fname in selected_files:
            path = self.snippet_dir / fname
            try:
                path.unlink()
            except Exception as e:
                errors.append(f"{fname}: {e}")

        self.reload_snippets()

        if errors:
            Messagebox.show_error("Some files could not be deleted:\n\n" + "\n".join(errors), "Delete Snippet")

    def close_window(self):
        '''  Destroys the Snippets Toplevel window '''
        self.destroy()

# ------------------#

def save_location():
    ''' executes at WM_DELETE_WINDOW event - see below '''
    with open(winpath, "w", encoding="utf-8") as fout:
        fout.write(root.geometry())
    root.destroy()

# connects DnD2 the main app window
root = TkinterDnD.Tk()
root.title("TKedit")
root.geometry("500x400")

# opening new windows successively will offset top metric
if os.path.isfile(winpath):
    with open(winpath, "r", encoding="utf-8") as f:
        lcoor = f.read().strip()
    text = lcoor  # now increment the "top" value by 28 pixels to slightly push down a new window
    x = text.rfind('+') + 1
    top = int(text[x:]) + 28  # pushes down "top" so previous window is still exposed
    text = text[:x] + str(top)  # next write the modified geo for next new window
    with open(winpath, "w", encoding="utf-8") as fout:
        fout.write(text)
    root.geometry(lcoor.strip())  # 1171x1296+3268+15  WxH+left+top
else:
    root.geometry("800x500") # WxH+left+top

root.protocol("WM_DELETE_WINDOW", save_location)  # Absolute Exit - does not check is_dirty

try:
    icon_img = PhotoImage(file=appicon)
    root.iconphoto(True, icon_img)
except Exception:
    pass

TKedit(root)
auto_close_entry_dialog(root, close_ms=1000)
root.mainloop()
