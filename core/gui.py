import flet as ft
import pyperclip # Need this for clipboard action

try:
    from config import DEFAULT_PASSWORD, PORT
except ImportError:
    DEFAULT_PASSWORD = "admin"
    PORT = 2004

# --- COLOR PALETTE ---
class Palette:
    BG = "#0B0E14"
    CARD_BG = "#151A23"
    INPUT_BG = "#0B0E14"
    BORDER = "#2B3240"
    ACCENT = "#3B82F6"
    TEXT_HEAD = "#FFFFFF"
    TEXT_SUB = "#94A3B8"
    SUCCESS = "#10B981"
    DANGER = "#EF4444"
    WARNING = "#F59E0B"

# FIXED: Inherit from ft.Column (NOT UserControl)
class AppGUI(ft.Column):
    def __init__(self, on_start, on_stop, on_browse, on_minimize):
        super().__init__()
        self.expand = True
        self.alignment = ft.MainAxisAlignment.CENTER 
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.scroll = ft.ScrollMode.AUTO
        
        self.on_start_server = on_start
        self.on_stop_server = on_stop
        self.on_browse_folder = on_browse
        self.on_minimize_to_tray = on_minimize

        # --- 1. HEADER COMPONENT ---
        self.status_badge = ft.Container(
            content=ft.Text("Status: Offline", color=Palette.DANGER, size=12, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.with_opacity(0.1, Palette.DANGER),
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            border_radius=20,
            border=ft.border.all(1, Palette.DANGER)
        )

        header = ft.Row(
            [
                ft.Row([
                    ft.Icon(ft.Icons.DIAMOND_OUTLINED, color=Palette.ACCENT, size=24),
                    ft.Text("Local Hub v2", size=20, weight=ft.FontWeight.BOLD, color=Palette.TEXT_HEAD),
                ]),
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, 
                        icon_color=Palette.TEXT_SUB, 
                        on_click=self.on_minimize_to_tray,
                        tooltip="Minimize"
                    ),
                    self.status_badge
                ])
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        # --- 2. PATH SELECTION ---
        self.browse_icon_btn = ft.Container(
            content=ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED, color=Palette.ACCENT, size=20),
            bgcolor=ft.Colors.with_opacity(0.15, Palette.ACCENT),
            border_radius=8,
            padding=8,
            margin=ft.margin.only(right=10),
            on_click=self.on_browse_folder,
            tooltip="Browse Folder",
            ink=True,
        )

        self.path_field = ft.TextField(
            value="",
            read_only=False,
            text_size=14,
            border_color=Palette.BORDER,
            bgcolor=Palette.CARD_BG,
            border_radius=8,
            filled=True,
            hint_text="/path/to/your/shared/folder",
            hint_style=ft.TextStyle(color=Palette.TEXT_SUB),
            prefix=self.browse_icon_btn,
            content_padding=15
        )

        path_section = ft.Column([
            ft.Text("Shared Folder Path", color=Palette.TEXT_HEAD, size=14, weight=ft.FontWeight.W_500),
            self.path_field
        ], spacing=10)

        # --- 3. ACCESS ROLES ---
        self.admin_switch = ft.Switch(value=True, on_change=self.toggle_field, active_color=Palette.SUCCESS)
        self.viewer_switch = ft.Switch(value=False, on_change=self.toggle_field, active_color=Palette.ACCENT)
        self.uploader_switch = ft.Switch(value=False, on_change=self.toggle_field, active_color=Palette.ACCENT)

        self.admin_pass_field = self._make_pass_field(DEFAULT_PASSWORD, enabled=True)
        self.viewer_pass_field = self._make_pass_field("Set Viewer Password", enabled=False)
        self.uploader_pass_field = self._make_pass_field("Set Uploader Password", enabled=False)

        # Customization Dialog
        self.custom_title = ft.TextField(label="Page Title", value="File Upload Portal", border_color=Palette.BORDER, bgcolor=Palette.INPUT_BG, text_size=13, border_radius=8)
        self.custom_subtitle = ft.TextField(label="Subtitle", value="Please upload files.", border_color=Palette.BORDER, bgcolor=Palette.INPUT_BG, text_size=13, border_radius=8)
        self.custom_image_path = ft.TextField(label="Logo Path", read_only=True, expand=True, text_size=12, border_color=Palette.BORDER, bgcolor=Palette.INPUT_BG, border_radius=8)
        
        self.logo_picker = ft.FilePicker(on_result=self._on_logo_picked)
        
        self.customize_dialog = ft.AlertDialog(
            modal=True,
            bgcolor=Palette.CARD_BG,
            title=ft.Text("Customize Upload Page", color=Palette.TEXT_HEAD, size=18),
            content=ft.Column([
                self.custom_title,
                self.custom_subtitle,
                ft.Row([
                    self.custom_image_path,
                    ft.IconButton(icon=ft.Icons.IMAGE_SEARCH, icon_color=Palette.ACCENT, on_click=lambda _: self.logo_picker.pick_files(allow_multiple=False))
                ])
            ], height=220, width=450, spacing=15),
            actions=[ft.TextButton("Save & Close", on_click=self._close_dialog, style=ft.ButtonStyle(color=Palette.ACCENT))],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12)
        )

        self.edit_uploader_btn = ft.IconButton(
            icon=ft.Icons.EDIT_NOTE_ROUNDED, icon_color=Palette.WARNING, tooltip="Customize Branding",
            on_click=self._open_dialog, visible=False,
            style=ft.ButtonStyle(bgcolor=ft.Colors.with_opacity(0.1, Palette.WARNING), shape=ft.RoundedRectangleBorder(radius=8))
        )

        roles_card = ft.Container(
            bgcolor=Palette.CARD_BG,
            border=ft.border.all(1, Palette.BORDER),
            border_radius=12,
            padding=20,
            content=ft.Column([
                ft.Text("Access Roles", size=16, weight=ft.FontWeight.BOLD, color=Palette.TEXT_HEAD),
                ft.Divider(color=Palette.BORDER, height=20),
                self._build_role_row("Admin", ft.Icons.SECURITY, ft.Colors.GREEN_400, self.admin_switch, self.admin_pass_field),
                self._build_role_row("Viewer", ft.Icons.VISIBILITY_OUTLINED, ft.Colors.ORANGE_400, self.viewer_switch, self.viewer_pass_field),
                
                ft.Row([
                    ft.Container(content=ft.Icon(ft.Icons.DRIVE_FOLDER_UPLOAD_OUTLINED, color=ft.Colors.BLUE_400, size=20), 
                               bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLUE_400), padding=8, border_radius=8),
                    ft.Text("Uploader", color=Palette.TEXT_HEAD, weight=ft.FontWeight.W_500, width=80),
                    ft.Container(expand=True), 
                    self.edit_uploader_btn,
                    self.uploader_switch, 
                    ft.Container(width=20),
                    ft.Container(content=self.uploader_pass_field, width=300)
                ], alignment=ft.MainAxisAlignment.START)
            ], spacing=15)
        )

        # --- 4. NETWORK ---
        self.ngrok_switch = ft.Switch(value=False, on_change=self.toggle_field, active_color=Palette.ACCENT)
        self.ngrok_token_field = ft.TextField(hint_text="Ngrok Auth Token", disabled=True, expand=True, border_color=Palette.BORDER, bgcolor=Palette.INPUT_BG, border_radius=8, filled=True, password=True, can_reveal_password=True, text_size=13, height=45, content_padding=10)
        self.port_field = ft.TextField(value=str(PORT), label="Port", width=100, text_align=ft.TextAlign.CENTER, border_color=Palette.BORDER, bgcolor=Palette.INPUT_BG, border_radius=8, filled=True, text_size=13, height=45, content_padding=10, keyboard_type=ft.KeyboardType.NUMBER)

        network_card = ft.Container(
            bgcolor=Palette.CARD_BG,
            border=ft.border.all(1, Palette.BORDER),
            border_radius=12, padding=20,
            content=ft.Column([
                ft.Text("Network", size=16, weight=ft.FontWeight.BOLD, color=Palette.TEXT_HEAD),
                ft.Divider(color=Palette.BORDER, height=20),
                ft.Row([ft.Icon(ft.Icons.SETTINGS_ETHERNET, color=Palette.ACCENT), ft.Text("Server Port:", color=Palette.TEXT_HEAD), self.port_field]),
                ft.Container(height=5),
                ft.Row([
                    ft.Icon(ft.Icons.PUBLIC, color="purple"), ft.Text("Public Link (Ngrok)", color=Palette.TEXT_HEAD),
                    ft.Container(expand=True), self.ngrok_switch, ft.Container(width=20), ft.Container(content=self.ngrok_token_field, width=300)
                ])
            ], spacing=5)
        )

        # --- 5. URLS & LOGS ---
        self.local_url_field = self._make_copy_field("Offline")
        self.public_url_field = self._make_copy_field("Unavailable")

        url_section = ft.Row([
            ft.Column([ft.Text("Local URL", weight=ft.FontWeight.BOLD), self.local_url_field], expand=True),
            ft.Column([ft.Text("Public URL", weight=ft.FontWeight.BOLD), self.public_url_field], expand=True),
        ], spacing=20)

        self.log_view = ft.ListView(expand=True, spacing=2, auto_scroll=True)
        self.log_container = ft.Container(content=self.log_view, bgcolor=Palette.INPUT_BG, border_radius=8, padding=15, height=250, border=ft.border.all(1, Palette.BORDER))
        self.log_view.controls.append(ft.Text("Logs will appear here...", color=Palette.TEXT_SUB, font_family="Consolas", size=12, selectable=True))

        # --- 6. LAYOUT ---
        self.stop_btn = ft.ElevatedButton("Stop Server", icon=ft.Icons.STOP_CIRCLE_OUTLINED, on_click=self.on_stop_server, disabled=True, style=ft.ButtonStyle(bgcolor={"": Palette.DANGER, "disabled": Palette.BORDER}, color={"": "white", "disabled": Palette.TEXT_SUB}, padding=20, shape=ft.RoundedRectangleBorder(radius=8)), expand=True)
        self.start_btn = ft.ElevatedButton("Start Server", icon=ft.Icons.PLAY_CIRCLE_OUTLINE_ROUNDED, on_click=self.on_start_server, style=ft.ButtonStyle(bgcolor={"": Palette.ACCENT, "disabled": Palette.BORDER}, color={"": "white", "disabled": Palette.TEXT_SUB}, padding=20, shape=ft.RoundedRectangleBorder(radius=8)), expand=True)
        
        bottom_bar = ft.Container(bgcolor=Palette.CARD_BG, padding=ft.padding.symmetric(horizontal=0, vertical=20), border=ft.border.only(top=ft.BorderSide(1, Palette.BORDER)), content=ft.Row([self.stop_btn, ft.Container(width=20), self.start_btn]))

        self.controls = [
            self.customize_dialog, self.logo_picker,
            ft.Container(content=ft.Column([header, ft.Divider(color="transparent", height=10), path_section, roles_card, network_card, url_section, ft.Text("Logs", weight=ft.FontWeight.BOLD), self.log_container], spacing=20), padding=ft.padding.only(bottom=20)),
            bottom_bar
        ]

    # --- HELPERS ---
    def _make_pass_field(self, hint, enabled):
        return ft.TextField(hint_text=hint, disabled=not enabled, expand=True, border_color=Palette.BORDER, bgcolor=Palette.INPUT_BG, border_radius=8, filled=True, password=True, can_reveal_password=True, text_size=13, height=45, content_padding=10)

    def _make_copy_field(self, value):
        text_field = ft.TextField(value=value, read_only=True, expand=True, border_color=Palette.BORDER, bgcolor=Palette.INPUT_BG, border_radius=8, filled=True, text_size=13, height=45, content_padding=10)
        text_field.suffix = ft.IconButton(icon=ft.Icons.COPY, icon_size=16, tooltip="Copy", on_click=lambda e: self._copy_text(text_field.value))
        return text_field

    def _copy_text(self, text):
        if text and "Offline" not in text and "Unavailable" not in text:
            pyperclip.copy(text)
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Copied: {text}"), bgcolor=Palette.SUCCESS)
            self.page.snack_bar.open = True
            self.page.update()

    def _build_role_row(self, label, icon, icon_color, switch_control, pass_control):
        return ft.Row([
            ft.Container(content=ft.Icon(icon, color=icon_color, size=20), bgcolor=ft.Colors.with_opacity(0.1, icon_color), padding=8, border_radius=8),
            ft.Text(label, color=Palette.TEXT_HEAD, weight=ft.FontWeight.W_500, width=80),
            ft.Container(expand=True), switch_control, ft.Container(width=20),
            ft.Container(content=pass_control, width=300)
        ], alignment=ft.MainAxisAlignment.START)

    # --- DIALOG ---
    def _open_dialog(self, e): self.customize_dialog.open = True; self.customize_dialog.update()
    def _close_dialog(self, e): self.customize_dialog.open = False; self.customize_dialog.update()
    def _on_logo_picked(self, e: ft.FilePickerResultEvent): 
        if e.files: self.custom_image_path.value = e.files[0].path; self.custom_image_path.update()

    # --- SETTINGS ---
    def get_settings(self) -> dict:
        return {
            "folder_path": self.path_field.value, "port": self.port_field.value,
            "enable_admin": self.admin_switch.value, "admin_pass": self.admin_pass_field.value,
            "enable_viewer": self.viewer_switch.value, "viewer_pass": self.viewer_pass_field.value,
            "enable_uploader": self.uploader_switch.value, "uploader_pass": self.uploader_pass_field.value,
            "brand_title": self.custom_title.value, "brand_subtitle": self.custom_subtitle.value, "brand_logo": self.custom_image_path.value,
            "enable_ngrok": self.ngrok_switch.value, "ngrok_token": self.ngrok_token_field.value
        }

    def toggle_field(self, e):
        if e.control == self.admin_switch: self.admin_pass_field.disabled = not e.control.value; self.admin_pass_field.update()
        elif e.control == self.viewer_switch: self.viewer_pass_field.disabled = not e.control.value; self.viewer_pass_field.update()
        elif e.control == self.uploader_switch: self.uploader_pass_field.disabled = not e.control.value; self.edit_uploader_btn.visible = e.control.value; self.uploader_pass_field.update(); self.edit_uploader_btn.update()
        elif e.control == self.ngrok_switch: self.ngrok_token_field.disabled = not e.control.value; self.ngrok_token_field.update()

    def set_server_state(self, is_running):
        self.start_btn.disabled = is_running
        self.stop_btn.disabled = not is_running
        self.port_field.disabled = is_running
        if is_running:
            self.status_badge.content.value = "Status: Online"; self.status_badge.content.color = Palette.SUCCESS; self.status_badge.border = ft.border.all(1, Palette.SUCCESS); self.status_badge.bgcolor = ft.Colors.with_opacity(0.1, Palette.SUCCESS)
        else:
            self.status_badge.content.value = "Status: Offline"; self.status_badge.content.color = Palette.DANGER; self.status_badge.border = ft.border.all(1, Palette.DANGER); self.status_badge.bgcolor = ft.Colors.with_opacity(0.1, Palette.DANGER)
        self.update()

    def add_log_line(self, message: str, color: str = "green"):
        color_map = {"green": Palette.SUCCESS, "red": Palette.DANGER, "cyan": Palette.ACCENT, "white": Palette.TEXT_HEAD}
        text_color = color_map.get(color, Palette.TEXT_HEAD)
        self.log_view.controls.append(ft.Text(message, color=text_color, font_family="Consolas", size=12, selectable=True))
        if len(self.log_view.controls) > 150: self.log_view.controls.pop(0)
        self.log_view.update()
        self.log_view.scroll_to(offset=-1, duration=300)

    def set_urls(self, local_url: str, public_url: str):
        self.local_url_field.value = local_url if local_url else "Server is offline"
        self.public_url_field.value = public_url if public_url else "Ngrok link not available"
        self.local_url_field.update()
        self.public_url_field.update()