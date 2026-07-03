# Tksyntex
# Syntax highlighting for Tkinter Text widget
#
# compile to Tksyntex.pyc

import tkinter as tk
from tkinter import font as tkfont
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.token import Token


class SyntaxHighlighter:
    def __init__(self, text_widget, language="text", style_name="plaintext",
                 font_name="Consolas", font_size=11, debounce_ms=300):
        self.text_widget = text_widget
        self.language = language
        self.style = get_style_by_name(style_name)
        self.lexer = get_lexer_by_name(language, stripnl=False, ensurenl=True)
        self.font_name = font_name
        self.font_size = font_size
        self._debounce_timer = None
        self._debounce_delay = debounce_ms

        self.text_widget.configure(bg=self.style.background_color)

        self._configure_tags()
        self._bind_events()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _configure_tags(self):
        """Configure tkinter text tags from Pygments style."""

        # Collect comment color first so we can reuse it
        comment_color = None
        for token, style_str in self.style:
            if token == Token.Comment.Single:
                if style_str['color']:
                    comment_color = '#' + style_str['color']
                    break

        # Configure a tag for every token in the style
        for token, style_str in self.style:
            tag_name = str(token)
            settings = {}

            # Foreground color only - skip bgcolor to prevent dark char backgrounds
            if style_str['color']:
                settings['foreground'] = '#' + style_str['color']

            # Font weight and slant
            bold = style_str['bold']
            italic = style_str['italic']
            if bold and italic:
                weight = 'bold italic'
            elif bold:
                weight = 'bold'
            elif italic:
                weight = 'italic'
            else:
                weight = 'normal'
            settings['font'] = (self.font_name, self.font_size, weight)

            if settings:
                self.text_widget.tag_configure(tag_name, **settings)

        # Remap triple-quoted strings (Token.Literal.String.Doc) to comment color
        # so ''' blah ''' looks the same as # comments
        if comment_color:
            for token_str in (
                str(Token.Literal.String.Doc),   # ''' and """ strings
                str(Token.Comment),
                str(Token.Comment.Single),
                str(Token.Comment.Hashbang),
            ):
                self.text_widget.tag_configure(token_str, foreground=comment_color)

    def _bind_events(self):
        """Bind text change events for real-time highlighting."""
        self.text_widget.bind("<KeyRelease>", self._on_change)
        self.text_widget.bind("<<Paste>>",    self._on_change)
        self.text_widget.bind("<<Cut>>",      self._on_change)

    # ------------------------------------------------------------------
    # Real-time debounced updating
    # ------------------------------------------------------------------

    def _on_change(self, event=None):
        """Debounce handler - waits for a pause in typing before highlighting."""
        if self._debounce_timer is not None:
            self.text_widget.after_cancel(self._debounce_timer)

        self._debounce_timer = self.text_widget.after(
            self._debounce_delay,
            self._run_highlight
        )

    def _run_highlight(self):
        """Execute highlight and clear the timer."""
        self._debounce_timer = None
        self.highlight()

    def set_language(self, language):
        """Swap language at runtime and re-highlight."""
        self.language = language
        self.lexer = get_lexer_by_name(language, stripnl=False, ensurenl=True)
        self.highlight()

    # ------------------------------------------------------------------
    # Core highlighting
    # ------------------------------------------------------------------

    def highlight(self):
        """Tokenize content and apply syntax highlighting tags."""
        code = self.text_widget.get("1.0", tk.END)

        # Remove all existing highlight tags
        for tag in self.text_widget.tag_names():
            if tag != "sel":
                self.text_widget.tag_remove(tag, "1.0", tk.END)

        row, col = 1, 0

        for token, content in lex(code, self.lexer):
            start = f"{row}.{col}"

            # Track position across newlines (critical for multiline strings)
            newlines = content.count('\n')
            if newlines:
                row += newlines
                col = len(content.split('\n')[-1])
            else:
                col += len(content)

            end = f"{row}.{col}"

            # Walk up token hierarchy to find the nearest configured tag
            tag_token = token
            while tag_token is not Token:
                tag_name = str(tag_token)
                if tag_name in self.text_widget.tag_names():
                    self.text_widget.tag_add(tag_name, start, end)
                    break
                tag_token = tag_token.parent
