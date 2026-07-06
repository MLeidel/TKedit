Yes, but with caveats. On Linux Ctrl+Tab can be intercepted by the window manager or the terminal, so it may not reach your Tk app unless the app has focus and is allowed to receive it.

How to do it reliably in Tkinter:
- Bind the key combination at the application level (root) or use bind_all.
- Return "break" from the handler to stop Tk’s default Tab focus traversal.

Example (no notebook required):

import tkinter as tk

def on_ctrl_tab(event):
    print("Ctrl+Tab pressed")
    # Do something here (e.g., switch a page)
    return "break"  # prevent default Tab behavior

root = tk.Tk()
root.bind_all("<Control-Tab>", on_ctrl_tab)

lbl = tk.Label(root, text="Press Ctrl+Tab")
lbl.pack(padx=20, pady=20)

root.mainloop()

Notes:
- If you’re running inside a terminal emulator, the terminal may capture Ctrl+Tab before Tk sees it. Run the app as a standalone GUI (no terminal) to test.
- If you’re using a ttk.Notebook, you can implement logic in the handler to switch to the next tab instead of just printing.
- This behavior is generally consistent on Windows/macOS as well, but always test on the target platform/window manager.