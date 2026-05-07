"""Tool permission tiers.

read    — pure read, no system changes (e.g. read_file, web_search)
write   — modifies workspace or in-app data (e.g. write_file, save_macro)
system  — controls the desktop/processes (e.g. open_app, kill_process, mouse_click)
network — sends data to external services (e.g. comm tools, web_fetch)
risky   — destructive or sensitive (e.g. delete_file, kill_process)

UI/API can require explicit confirmation for higher tiers."""
from __future__ import annotations


TIER = {
    "read_file": "read", "list_files": "read", "list_dir": "read",
    "find_files": "read", "grep_files": "read", "recent_files": "read",
    "file_info": "read", "list_backups": "read",
    "rag_search": "read", "web_search": "read", "calculator": "read",
    "list_processes": "read", "top_processes": "read",
    "network_info": "read", "wifi_info": "read", "list_open_ports": "read",
    "disk_usage": "read", "system_info": "read", "current_time": "read",
    "list_running_apps": "read", "active_window": "read", "active_window_text": "read",
    "list_visible_text": "read", "read_screen": "read", "describe_screen": "read",
    "find_text_on_screen": "read", "read_image": "read", "describe_image": "read",
    "describe_screen_visual": "read", "ping_host": "read",
    "git_status": "read", "git_diff": "read", "git_log": "read", "git_branch": "read",
    "list_reminders": "read", "list_tasks": "read", "fetch_url": "read",
    "fetch_links": "read", "get_public_ip": "read", "get_brightness": "read",
    "get_screen_size": "read", "mouse_position": "read",
    "youtube_info": "read", "pip_search": "read", "pip_installed": "read",
    "apt_search": "read", "apt_show": "read", "env_info": "read",
    "browser_text": "read", "browser_url": "read", "format_python": "read",

    "write_file": "write", "edit_file": "write", "git_init": "write",
    "git_add": "write", "git_commit": "write", "git_checkout": "write",
    "remind_me": "write", "cancel_reminder": "write",
    "add_task": "write", "complete_task": "write", "delete_task": "write",
    "make_pdf": "write", "markdown_to_html": "write", "text_to_speech_file": "write",
    "screenshot": "write", "record_audio": "write",
    "clipboard_copy": "write", "clipboard_paste": "read",
    "undo_last_edit": "write", "set_brightness": "write", "set_volume": "write",

    "open_app": "system", "open_url": "network", "focus_window": "system",
    "type_text": "system", "press_key": "system", "click_text": "system",
    "mouse_move": "system", "mouse_click": "system", "mouse_double_click": "system",
    "mouse_drag": "system", "scroll": "system",
    "media_control": "system", "lock_screen": "system", "notify": "system",
    "browser_open": "system", "browser_click": "system", "browser_fill": "system",
    "browser_press": "system", "browser_screenshot": "write", "browser_eval": "system",
    "browser_close": "system",

    "delete_file": "risky", "kill_process": "risky",
    "run_python_file": "risky", "python_exec": "risky",
    "youtube_download": "network", "download_file": "network",

    "whatsapp_message": "network", "telegram_message": "network",
    "email_compose": "network", "sms_message": "network",
    "facebook_message": "network", "open_facebook": "network",
    "open_instagram": "network", "open_linkedin": "network",
    "open_twitter": "network", "post_tweet": "network",
    "google_search": "network", "youtube_search": "network", "open_maps": "network",
}

DEFAULT_TIER = "system"


def tier_of(tool_name: str) -> str:
    return TIER.get(tool_name, DEFAULT_TIER)
