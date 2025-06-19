from django import template
from core.utils import (
    get_country_flag_emoji, 
    get_browser_icon, 
    get_device_icon, 
    get_os_icon
)

register = template.Library()


@register.filter
def country_flag(country_name):
    """Get flag emoji for a country name"""
    return get_country_flag_emoji(country_name)


@register.filter
def browser_icon(browser_name):
    """Get FontAwesome icon class for browser"""
    return get_browser_icon(browser_name)


@register.filter
def device_icon(device_type):
    """Get FontAwesome icon class for device type"""
    return get_device_icon(device_type)


@register.filter
def os_icon(os_name):
    """Get FontAwesome icon class for operating system"""
    return get_os_icon(os_name)


@register.filter
def percentage(value, total):
    """Calculate percentage with one decimal place"""
    if not total or total == 0:
        return "0.0"
    try:
        return f"{(value / total * 100):.1f}"
    except (TypeError, ZeroDivisionError):
        return "0.0"


@register.simple_tag
def analytics_card(title, value, icon="fas fa-chart-bar", color="blue"):
    """Generate an analytics card"""
    return {
        'title': title,
        'value': value,
        'icon': icon,
        'color': color
    } 