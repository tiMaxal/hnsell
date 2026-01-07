# APPLY THIS PATCH (ONLY THESE CHANGES)

1️⃣ ADD THIS CLASS (ONCE, NEAR THE TOP)

Insert after imports, before class `HNSellApp`:
(no other imports or code touched)

``` py
class ScrollableFrame(ttk.Frame):
    """
    Vertically scrollable container that does NOT interfere with
    PanedWindow or Listbox resizing.

    Used for tall option-heavy tabs (PageMaker) on small screens.
    """
    def __init__(self, parent):
        super().__init__(parent)

        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)

        self.inner = ttk.Frame(canvas)

        self.inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.inner.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.inner.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
```

2️⃣ REMOVE THE NOTEBOOK-LEVEL CANVAS (CRITICAL)

In `__init__`, DELETE this entire block (this is the root cause of your issue):

``` py
# Create canvas with scrollbar for notebook to enable full-tab scrolling
canvas_frame = tk.Frame(root)
canvas_frame.pack(fill='both', expand=True, padx=10, pady=(5, 5))

self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
scrollbar = tk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
scrollable_frame = tk.Frame(self.canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
)

self.canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
self.canvas.configure(yscrollcommand=scrollbar.set)

self.canvas.pack(side='left', fill='both', expand=True)
scrollbar.pack(side='right', fill='y')

def _on_mousewheel(event):
    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
self.canvas.bind("<MouseWheel>", _on_mousewheel)

self.notebook = ttk.Notebook(scrollable_frame)
self.notebook.pack(fill='both', expand=True)
```

3️⃣ REPLACE IT WITH THIS (SIMPLE, SAFE)

``` py
self.notebook = ttk.Notebook(root)
self.notebook.pack(fill='both', expand=True, padx=10, pady=(5, 5))
```

That’s it for the notebook.

4️⃣ MODIFY ONLY `create_pagemaker_tab()`
ORIGINAL

``` py
tab = ttk.Frame(self.notebook)
self.notebook.add(tab, text="PageMaker")
```

REPLACE WITH

``` py
tab = ttk.Frame(self.notebook)
self.notebook.add(tab, text="PageMaker")

scroll = ScrollableFrame(tab)
scroll.pack(fill='both', expand=True)

container = scroll.inner
```

THEN (IMPORTANT)

Inside create_pagemaker_tab, replace every parent of PageMaker widgets:

OLD parent  NEW parent
tab container

⚠️ Nothing else changes
No widget logic, no options, no resizing code, no PanedWindow changes.

5️⃣ UPDATE HELP TEXT (REQUIRED)

In show_help(), append this section:

``` text
INTERFACE & SCROLLING:
- The PageMaker tab supports vertical scrolling for small screens
- Use the mouse wheel while the cursor is inside the PageMaker tab
- Selection lists remain resizable via drag handles
- Other tabs are fixed-height by design
```

✅ WHY THIS IS THE ONLY SAFE FIX

Tkinter cannot safely:

scroll a Notebook

resize PanedWindows

share geometry control

By scoping scrolling inside the PageMaker tab only, you:

eliminate geometry conflicts

preserve resizing

keep behaviour predictable

This is exactly how large Tkinter tools (IDEs, DB browsers, GIS tools) handle tall tabs.
