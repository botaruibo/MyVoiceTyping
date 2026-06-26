import customtkinter as ctk


class GUIStyles:
    FONT_FAMILY = "System"

    # macOS-inspired semantic colors.
    COLOR_WINDOW_BG = ("#F2F2F7", "#171717")
    COLOR_CONTENT_BG = ("#F5F5F7", "#171717")
    COLOR_SIDEBAR_BG = ("#EBEBF0", "#141414")
    COLOR_CARD_BG = ("#FFFFFF", "#232323")
    COLOR_CARD_SOFT_BG = ("#F9FAFB", "#1E1E1E")
    COLOR_CARD_BORDER = ("#E5E5EA", "#303030")
    COLOR_DIVIDER = ("#E5E5EA", "#303030")
    COLOR_TEXT_PRIMARY = ("#1C1C1E", "#F5F5F5")
    COLOR_TEXT_SECONDARY = ("#6B7280", "#A7A7A7")
    COLOR_TEXT_MUTED = ("#8E8E93", "#9CA3AF")
    COLOR_ACCENT = ("#007AFF", "#5EA8FF")
    COLOR_DESTRUCTIVE = "#FF4B5C"
    COLOR_BUTTON_FG = ("#FFFFFF", "#2A2A2A")
    COLOR_BUTTON_HOVER = ("#F8F8FA", "#333333")
    COLOR_CONTROL_BG = ("#FFFFFF", "#2B2B2B")

    # Backward-compatible aliases used by older settings components.
    COLOR_BG = COLOR_CONTENT_BG
    COLOR_BORDER = COLOR_CARD_BORDER

    @staticmethod
    def get_card_frame_args():
        return {
            "fg_color": GUIStyles.COLOR_CARD_BG,
            "corner_radius": 10,
            "border_width": 1,
            "border_color": GUIStyles.COLOR_CARD_BORDER
        }

    @staticmethod
    def get_soft_card_frame_args():
        return {
            "fg_color": GUIStyles.COLOR_CARD_SOFT_BG,
            "corner_radius": 10,
            "border_width": 1,
            "border_color": ("#EEF0F3", "#2F2F2F"),
        }

    @staticmethod
    def get_title_font():
        return ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=16, weight="bold")

    @staticmethod
    def get_page_title_font():
        return ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=26, weight="bold")

    @staticmethod
    def get_section_title_font():
        return ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=17, weight="bold")

    @staticmethod
    def get_stat_label_font():
        return ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=12)

    @staticmethod
    def get_stat_value_font():
        return ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=26, weight="bold")

    @staticmethod
    def get_saved_time_value_font():
        return ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=22, weight="bold")

    @staticmethod
    def get_label_font():
        return ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=14)

    @staticmethod
    def get_body_font():
        return ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=13)

    @staticmethod
    def get_note_font():
        return ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=12)

    @staticmethod
    def get_meta_font():
        return ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=11)

    @staticmethod
    def get_button_args():
        return {
            "fg_color": GUIStyles.COLOR_BUTTON_FG,
            "text_color": GUIStyles.COLOR_TEXT_PRIMARY,
            "border_width": 1,
            "border_color": GUIStyles.COLOR_CARD_BORDER,
            "hover_color": GUIStyles.COLOR_BUTTON_HOVER,
            "corner_radius": 6,
            "height": 32,
            "font": GUIStyles.get_label_font()
        }

    @staticmethod
    def get_secondary_button_args():
        return {
            "fg_color": GUIStyles.COLOR_BUTTON_FG,
            "text_color": GUIStyles.COLOR_TEXT_PRIMARY,
            "hover_color": GUIStyles.COLOR_BUTTON_HOVER,
            "border_width": 1,
            "border_color": GUIStyles.COLOR_CARD_BORDER,
            "corner_radius": 8,
            "height": 30,
            "font": ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=12, weight="bold"),
        }

    @staticmethod
    def get_weak_action_button_args():
        return {
            "fg_color": ("#F1F5FF", "#2A2F3A"),
            "hover_color": ("#E6EEFF", "#343B49"),
            "text_color": GUIStyles.COLOR_ACCENT,
            "corner_radius": 7,
            "height": 28,
            "font": ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=12, weight="bold"),
        }

    @staticmethod
    def get_switch_args():
        return {
            "progress_color": GUIStyles.COLOR_ACCENT,
        }

    @staticmethod
    def get_entry_args():
        return {
            "corner_radius": 8,
            "border_width": 1,
            "border_color": GUIStyles.COLOR_CARD_BORDER,
            "fg_color": GUIStyles.COLOR_CONTROL_BG,
            "text_color": GUIStyles.COLOR_TEXT_PRIMARY,
            "height": 36,
            "font": GUIStyles.get_label_font()
        }

    # Navigation Styles
    COLOR_NAV_BG_DEFAULT = "transparent"
    COLOR_NAV_BG_HOVER = ("#DBDBE0", "#2A2A2A")
    COLOR_NAV_BG_ACTIVE = ("#FFFFFF", "#2B2B2B")
    COLOR_NAV_TEXT_DEFAULT = ("#5A5A5A", "#A0A0A0")
    COLOR_NAV_TEXT_ACTIVE = COLOR_TEXT_PRIMARY
    COLOR_NAV_INDICATOR_ACTIVE = "transparent"

    @staticmethod
    def get_nav_font():
        return ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=15, weight="bold")

    # Hotkey Bubble Styles
    COLOR_BUBBLE_FRAME_BG = COLOR_BG
    COLOR_BUBBLE_BG = ("#E8E8E8", "#454545")
    COLOR_BUBBLE_BORDER = ("#D0D0D0", "#5A5A5A")
    COLOR_BUBBLE_TEXT = ("#000000", "#FFFFFF")
