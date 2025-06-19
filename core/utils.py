import re
import requests

try:
    from user_agents import parse as ua_parse
    HAS_USER_AGENTS = True
except ImportError:
    HAS_USER_AGENTS = False


def parse_user_agent(user_agent_string):
    """
    Parse user agent string to extract device, browser, and OS information
    """
    if not user_agent_string:
        return {
            'device_type': 'Unknown',
            'browser': 'Unknown',
            'operating_system': 'Unknown'
        }
    
    # Use user-agents library if available, otherwise fallback to regex
    if HAS_USER_AGENTS:
        try:
            user_agent = ua_parse(user_agent_string)
            
            # Determine device type
            if user_agent.is_mobile:
                device_type = 'Mobile'
            elif user_agent.is_tablet:
                device_type = 'Tablet'
            elif user_agent.is_pc:
                device_type = 'Desktop'
            else:
                device_type = 'Unknown'
            
            # Get browser info
            browser = f"{user_agent.browser.family}"
            if user_agent.browser.version_string:
                browser += f" {user_agent.browser.version_string}"
            
            # Get OS info
            operating_system = f"{user_agent.os.family}"
            if user_agent.os.version_string:
                operating_system += f" {user_agent.os.version_string}"
            
            return {
                'device_type': device_type,
                'browser': browser[:100],  # Limit to 100 chars to fit in model
                'operating_system': operating_system[:100]
            }
        
        except Exception as e:
            # Fallback parsing if user_agents library fails
            return parse_user_agent_fallback(user_agent_string)
    else:
        # Use fallback parsing if user_agents library is not available
        return parse_user_agent_fallback(user_agent_string)


def parse_user_agent_fallback(user_agent_string):
    """
    Fallback user agent parsing using regex patterns
    """
    ua = user_agent_string.lower()
    
    # Device type detection
    if any(mobile in ua for mobile in ['mobile', 'android', 'iphone', 'ipod']):
        device_type = 'Mobile'
    elif 'ipad' in ua or 'tablet' in ua:
        device_type = 'Tablet'
    else:
        device_type = 'Desktop'
    
    # Browser detection
    browser = 'Unknown'
    if 'chrome' in ua and 'edge' not in ua:
        browser = 'Chrome'
    elif 'firefox' in ua:
        browser = 'Firefox'
    elif 'safari' in ua and 'chrome' not in ua:
        browser = 'Safari'
    elif 'edge' in ua:
        browser = 'Edge'
    elif 'opera' in ua or 'opr' in ua:
        browser = 'Opera'
    elif 'msie' in ua or 'trident' in ua:
        browser = 'Internet Explorer'
    
    # Operating system detection
    operating_system = 'Unknown'
    if 'windows' in ua:
        operating_system = 'Windows'
    elif 'macintosh' in ua or 'mac os' in ua:
        operating_system = 'macOS'
    elif 'linux' in ua:
        operating_system = 'Linux'
    elif 'android' in ua:
        operating_system = 'Android'
    elif 'ios' in ua or 'iphone' in ua or 'ipad' in ua:
        operating_system = 'iOS'
    
    return {
        'device_type': device_type,
        'browser': browser,
        'operating_system': operating_system
    }


def get_location_from_ip(ip_address):
    """
    Get geographic location from IP address using a free IP geolocation service
    """
    if not ip_address or ip_address in ['127.0.0.1', '::1', 'localhost']:
        return {
            'country': 'Local',
            'city': 'Local'
        }
    
    try:
        # Using ipapi.co service (free tier: 1000 requests/day)
        response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            country = data.get('country_name', 'Unknown')
            city = data.get('city', 'Unknown')
            
            return {
                'country': country[:100] if country else 'Unknown',
                'city': city[:100] if city else 'Unknown'
            }
    
    except Exception as e:
        # If the API call fails, try alternative service
        try:
            # Fallback to ip-api.com (free tier: 1000 requests/hour)
            response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    country = data.get('country', 'Unknown')
                    city = data.get('city', 'Unknown')
                    
                    return {
                        'country': country[:100] if country else 'Unknown',
                        'city': city[:100] if city else 'Unknown'
                    }
        
        except Exception:
            pass
    
    # If all APIs fail, return Unknown
    return {
        'country': 'Unknown',
        'city': 'Unknown'
    }


def get_country_flag_emoji(country_name):
    """
    Get flag emoji for a country name
    """
    country_flags = {
        'United States': '🇺🇸',
        'United Kingdom': '🇬🇧',
        'Canada': '🇨🇦',
        'Germany': '🇩🇪',
        'France': '🇫🇷',
        'Japan': '🇯🇵',
        'China': '🇨🇳',
        'India': '🇮🇳',
        'Brazil': '🇧🇷',
        'Australia': '🇦🇺',
        'Russia': '🇷🇺',
        'South Korea': '🇰🇷',
        'Italy': '🇮🇹',
        'Spain': '🇪🇸',
        'Netherlands': '🇳🇱',
        'Sweden': '🇸🇪',
        'Norway': '🇳🇴',
        'Denmark': '🇩🇰',
        'Finland': '🇫🇮',
        'Switzerland': '🇨🇭',
        'Austria': '🇦🇹',
        'Belgium': '🇧🇪',
        'Portugal': '🇵🇹',
        'Poland': '🇵🇱',
        'Turkey': '🇹🇷',
        'Mexico': '🇲🇽',
        'Argentina': '🇦🇷',
        'Chile': '🇨🇱',
        'Colombia': '🇨🇴',
        'Peru': '🇵🇪',
        'South Africa': '🇿🇦',
        'Egypt': '🇪🇬',
        'Nigeria': '🇳🇬',
        'Kenya': '🇰🇪',
        'Thailand': '🇹🇭',
        'Indonesia': '🇮🇩',
        'Malaysia': '🇲🇾',
        'Singapore': '🇸🇬',
        'Philippines': '🇵🇭',
        'Vietnam': '🇻🇳',
        'Bangladesh': '🇧🇩',
        'Pakistan': '🇵🇰',
        'Israel': '🇮🇱',
        'Saudi Arabia': '🇸🇦',
        'United Arab Emirates': '🇦🇪',
        'Local': '🏠',
        'Unknown': '🌍'
    }
    
    return country_flags.get(country_name, '🌍')


def get_browser_icon(browser_name):
    """
    Get FontAwesome icon class for browser
    """
    browser_name = browser_name.lower()
    
    if 'chrome' in browser_name:
        return 'fab fa-chrome'
    elif 'firefox' in browser_name:
        return 'fab fa-firefox-browser'
    elif 'safari' in browser_name:
        return 'fab fa-safari'
    elif 'edge' in browser_name:
        return 'fab fa-edge'
    elif 'opera' in browser_name:
        return 'fab fa-opera'
    elif 'internet explorer' in browser_name or 'ie' in browser_name:
        return 'fab fa-internet-explorer'
    else:
        return 'fas fa-globe'


def get_device_icon(device_type):
    """
    Get FontAwesome icon class for device type
    """
    device_type = device_type.lower()
    
    if 'mobile' in device_type:
        return 'fas fa-mobile-alt'
    elif 'tablet' in device_type:
        return 'fas fa-tablet-alt'
    elif 'desktop' in device_type:
        return 'fas fa-desktop'
    else:
        return 'fas fa-question-circle'


def get_os_icon(os_name):
    """
    Get FontAwesome icon class for operating system
    """
    os_name = os_name.lower()
    
    if 'windows' in os_name:
        return 'fab fa-windows'
    elif 'mac' in os_name or 'ios' in os_name:
        return 'fab fa-apple'
    elif 'linux' in os_name:
        return 'fab fa-linux'
    elif 'android' in os_name:
        return 'fab fa-android'
    else:
        return 'fas fa-desktop' 