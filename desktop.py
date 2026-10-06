import wx

CONFIG = wx.Config("ModernWxApp")

def get_icon(label, size=(32, 32)):
    art_ids = {
        "Home": wx.ART_GO_HOME,
        "Settings": wx.ART_EXECUTABLE_FILE,
        "About": wx.ART_INFORMATION,
        "Profile": wx.ART_TIP,
        "Preferences": wx.ART_HELP_BOOK,
        "License": wx.ART_QUESTION,
        "ToggleTheme": wx.ART_TIP
    }
    return wx.ArtProvider.GetBitmap(art_ids.get(label, wx.ART_MISSING_IMAGE), wx.ART_OTHER, size)

DARK_THEME = {"bg": "#2C3E50", "hover": "#34495E", "text": wx.WHITE}
LIGHT_THEME = {"bg": "#ECF0F1", "hover": "#BDC3C7", "text": wx.BLACK}

class Sidebar(wx.Panel):
    def __init__(self, parent, on_select, theme):
        super().__init__(parent, size=(240, -1gi))
        self.parent = parent
        self.on_select = on_select
        self.expanded = True
        self.theme = theme
        self.selected_label = "Home"
        self.buttons = []
        self.submenus_visible = {}
        self.submenu_panels = {}

        self.SetBackgroundColour(theme["bg"])
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.button_panel = wx.Panel(self)
        self.button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.button_panel.SetSizer(self.button_sizer)
        self.button_panel.SetBackgroundColour(theme["bg"])

        self.button_defs = [
            ("Home", []),
            ("Settings", ["Profile", "Preferences"]),
            ("About", ["License"])
        ]

        for label, subitems in self.button_defs:
            self.add_main_button(label, subitems)

        self.sizer.Add(self.button_panel, 1, wx.EXPAND)

        toggle_icon = get_icon("ToggleTheme", (20, 20))
        toggle_btn = wx.BitmapButton(self, bitmap=toggle_icon, size=(32, 32), style=wx.BORDER_NONE)
        toggle_btn.SetBackgroundColour(theme["bg"])
        toggle_btn.Bind(wx.EVT_BUTTON, self.toggle_sidebar)

        self.sizer.AddStretchSpacer()
        self.sizer.Add(toggle_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        self.SetSizer(self.sizer)

    def add_main_button(self, label, subitems):
        icon_size = (24, 24) if not self.expanded else (32, 32)
        bmp = get_icon(label, size=icon_size)
        panel = wx.Panel(self.button_panel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        icon = wx.StaticBitmap(panel, bitmap=bmp)
        text = wx.StaticText(panel, label=label)
        text.SetForegroundColour(self.theme["text"])
        text.SetFont(wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.BOLD))

        hbox.AddSpacer(5)
        hbox.Add(icon, 0, wx.ALIGN_CENTER | wx.RIGHT, 8)
        hbox.Add(text, 0, wx.ALIGN_CENTER)
        panel.SetSizer(hbox)
        panel.SetBackgroundColour(self.theme["bg"])

        def on_click(evt, l=label):
            self.parent.GetParent().on_sidebar_select(l)
            self.highlight_button(l)
            if not subitems:
                for lbl in self.submenus_visible:
                    self.submenu_panels[lbl].Hide()
                    self.submenus_visible[lbl] = False
            self.Layout()

        panel.Bind(wx.EVT_LEFT_DOWN, on_click)
        icon.Bind(wx.EVT_LEFT_DOWN, on_click)
        text.Bind(wx.EVT_LEFT_DOWN, on_click)

        def on_enter(evt, p=panel):
            p.SetBackgroundColour(self.theme["hover"])

        def on_leave(evt, p=panel):
            if text.GetLabel() != self.selected_label:
                p.SetBackgroundColour(self.theme["bg"])

        panel.Bind(wx.EVT_ENTER_WINDOW, on_enter)
        panel.Bind(wx.EVT_LEAVE_WINDOW, on_leave)

        self.button_sizer.Add(panel, 0, wx.EXPAND | wx.ALL, 2)
        self.buttons.append((panel, text))

        submenu_panel = wx.Panel(self.button_panel)
        submenu_sizer = wx.BoxSizer(wx.VERTICAL)
        submenu_panel.SetSizer(submenu_sizer)
        submenu_panel.Hide()

        for sub in subitems:
            bmp = get_icon(sub)
            subpanel = wx.Panel(submenu_panel)
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            icon = wx.StaticBitmap(subpanel, bitmap=bmp)
            text = wx.StaticText(subpanel, label=sub)
            text.SetForegroundColour(self.theme["text"])
            text.SetFont(wx.Font(9, wx.DEFAULT, wx.NORMAL, wx.NORMAL))

            hbox.AddSpacer(20)
            hbox.Add(icon, 0, wx.ALIGN_CENTER | wx.RIGHT, 8)
            hbox.Add(text, 0, wx.ALIGN_CENTER)
            subpanel.SetSizer(hbox)
            subpanel.SetBackgroundColour(self.theme["bg"])

            handler = lambda evt, l=sub: (self.on_select(l), self.highlight_button(l))
            subpanel.Bind(wx.EVT_LEFT_DOWN, handler)
            icon.Bind(wx.EVT_LEFT_DOWN, handler)
            text.Bind(wx.EVT_LEFT_DOWN, handler)

            def on_enter(evt, p=subpanel):
                p.SetBackgroundColour(self.theme["hover"])

            def on_leave(evt, p=subpanel):
                p.SetBackgroundColour(self.theme["bg"])

            subpanel.Bind(wx.EVT_ENTER_WINDOW, on_enter)
            subpanel.Bind(wx.EVT_LEAVE_WINDOW, on_leave)

            submenu_sizer.Add(subpanel, 0, wx.EXPAND | wx.ALL, 1)

        self.button_sizer.Add(submenu_panel, 0, wx.EXPAND)
        self.submenus_visible[label] = False
        self.submenu_panels[label] = submenu_panel

    def highlight_button(self, label):
        self.selected_label = label
        for panel, text in self.buttons:
            panel.SetBackgroundColour("#1ABC9C" if text.GetLabel() == label else self.theme["bg"])
        self.Layout()

    def toggle_submenu(self, label):
        visible = self.submenus_visible[label]
        panel = self.submenu_panels[label]
        panel.Show(not visible)
        self.submenus_visible[label] = not visible
        self.Layout()

    def toggle_sidebar(self, event=None):
        width = self.GetSize().width
        new_width = 100 if self.expanded else 240
        self.animate_sidebar(width, new_width)
        self.expanded = not self.expanded
        self.update_button_labels()
        if not self.expanded:
            for label in self.submenus_visible:
                if self.submenus_visible[label]:
                    self.submenu_panels[label].Hide()
                    self.submenus_visible[label] = False
        self.Layout()

    def animate_sidebar(self, start, end):
        self._animate_step(start, end, 10 if end > start else -10)

    def _animate_step(self, current, end, step):
        if (step > 0 and current >= end) or (step < 0 and current <= end):
            self.SetMinSize((end, -1))
            self.GetParent().Layout()
            return
        self.SetMinSize((current, -1))
        self.GetParent().Layout()
        wx.CallLater(10, self._animate_step, current + step, end, step)

    def update_button_labels(self):
        for panel, text in self.buttons:
            text.Show(self.expanded)
        self.Layout()


class Page(wx.Panel):
    def __init__(self, parent, label, theme):
        super().__init__(parent)
        self.label = label
        self.theme = theme
        self.update_theme()

    def update_theme(self):
        self.SetBackgroundColour(self.theme["bg"])
        self.DestroyChildren()
        sizer = wx.BoxSizer(wx.VERTICAL)

        if self.label == "Preferences":
            toggle = wx.Button(self, label="Toggle Theme")
            toggle.Bind(wx.EVT_BUTTON, lambda evt: self.GetTopLevelParent().toggle_theme())
            sizer.Add(toggle, 0, wx.ALL | wx.ALIGN_CENTER, 20)
        elif self.label == "Home":
            text = wx.StaticText(self, label="Welcome to the Home Page!")
            text.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
            text.SetForegroundColour(self.theme["text"])
            sizer.Add(text, 0, wx.ALL | wx.ALIGN_CENTER, 20)
            sizer.Add(wx.Button(self, label="Explore Dashboard"), 0, wx.ALL | wx.ALIGN_CENTER, 10)
            sizer.Add(wx.Button(self, label="Notifications"), 0, wx.ALL | wx.ALIGN_CENTER, 10)
        elif self.label == "Profile":
            sizer.Add(wx.StaticText(self, label="User Profile Settings"), 0, wx.ALL | wx.ALIGN_CENTER, 10)
            sizer.Add(wx.TextCtrl(self, value="Username"), 0, wx.ALL | wx.EXPAND, 10)
            sizer.Add(wx.TextCtrl(self, value="Email"), 0, wx.ALL | wx.EXPAND, 10)
            sizer.Add(wx.Button(self, label="Save Changes"), 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        elif self.label == "License":
            sizer.Add(wx.StaticText(self, label="License Agreement"), 0, wx.ALL | wx.ALIGN_CENTER, 10)
            sizer.Add(wx.TextCtrl(self, value="This software is licensed under ...", style=wx.TE_MULTILINE | wx.TE_READONLY), 1, wx.ALL | wx.EXPAND, 10)
        elif self.label == "About":
            sizer.Add(wx.StaticText(self, label="Modern wxPython UI App\nVersion 1.0"), 0, wx.ALL | wx.ALIGN_CENTER, 20)
        else:
            sizer.Add(wx.StaticText(self, label=f"{self.label} Page"), 0, wx.ALL | wx.ALIGN_CENTER, 20)

        self.SetSizer(sizer)


class MainPanel(wx.Panel):
    def __init__(self, parent, theme):
        super().__init__(parent)
        self.theme = theme
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        labels = ["Home", "Settings", "About", "Profile", "Preferences", "License"]
        self.pages = {label: Page(self, label, theme) for label in labels}
        for panel in self.pages.values():
            panel.Hide()
            self.sizer.Add(panel, 1, wx.EXPAND)
        self.current_page = None
        self.show_page("Home")

    def show_page(self, label):
        if self.current_page:
            self.current_page.Hide()
        new_page = self.pages[label]
        new_page.update_theme()
        new_page.Show()
        self.current_page = new_page
        self.Layout()


class MainFrame(wx.Frame):
    def __init__(self):
        saved_theme = CONFIG.Read("theme", "dark")
        self.theme = DARK_THEME if saved_theme == "dark" else LIGHT_THEME

        super().__init__(None, title="Modern wxPython App", size=(900, 650))

        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(self.theme["bg"])
        self.main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.sidebar = Sidebar(self.panel, self.on_sidebar_select, self.theme)
        self.main_panel = MainPanel(self.panel, self.theme)

        self.main_sizer.Add(self.sidebar, 0, wx.EXPAND)
        self.main_sizer.Add(self.main_panel, 1, wx.EXPAND | wx.ALL, 10)

        self.panel.SetSizer(self.main_sizer)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        self.Centre()
        self.Show()

    def on_key(self, event):
        if event.GetKeyCode() == ord('`'):
            self.sidebar.toggle_sidebar()
        else:
            event.Skip()

    def on_sidebar_select(self, label):
        self.main_panel.show_page(label)

    def toggle_theme(self):
        self.theme = LIGHT_THEME if self.theme == DARK_THEME else DARK_THEME
        CONFIG.Write("theme", "light" if self.theme == LIGHT_THEME else "dark")
        CONFIG.Flush()
        self.panel.SetBackgroundColour(self.theme["bg"])
        self.sidebar.Destroy()
        self.main_panel.Destroy()
        self.sidebar = Sidebar(self.panel, self.on_sidebar_select, self.theme)
        self.main_panel = MainPanel(self.panel, self.theme)
        self.main_sizer.Clear()
        self.main_sizer.Add(self.sidebar, 0, wx.EXPAND)
        self.main_sizer.Add(self.main_panel, 1, wx.EXPAND | wx.ALL, 10)
        self.sidebar.update_button_labels()
        self.sidebar.Layout()
        self.panel.Layout()


class MyApp(wx.App):
    def OnInit(self):
        frame = MainFrame()
        self.SetTopWindow(frame)
        return True

if __name__ == "__main__":
    app = MyApp(False)
    app.MainLoop()
