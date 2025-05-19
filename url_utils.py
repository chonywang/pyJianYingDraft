import requests
from urllib.parse import urlparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def resolve_short_url(url: str, max_redirects: int = 5) -> str:
    """
    Resolve a shortened URL to its final destination URL.
    
    Args:
        url (str): The shortened URL to resolve
        max_redirects (int): Maximum number of redirects to follow (default: 5)
        
    Returns:
        str: The final destination URL
        
    Raises:
        requests.exceptions.RequestException: If there's an error during the request
    """
    try:
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {url}")
            
        # Make request with allow_redirects=True to automatically follow redirects
        response = requests.get(
            url,
            allow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0'},  # Some URL shorteners require a user agent
            timeout=10  # Timeout after 10 seconds
        )
        
        # Log redirect chain if any
        if len(response.history) > 0:
            logger.info(f"Redirect chain for {url}:")
            for r in response.history:
                logger.info(f"  {r.status_code}: {r.url}")
            logger.info(f"Final URL: {response.url}")
        
        return response.url
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error resolving URL {url}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while resolving URL {url}: {str(e)}")
        raise

def is_short_url(url: str) -> bool:
    """
    Check if a URL appears to be a shortened URL based on common patterns.
    
    Args:
        url (str): The URL to check
        
    Returns:
        bool: True if the URL appears to be shortened, False otherwise
    """
    # List of common URL shortener domains
    shortener_domains = {
        'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 
        'is.gd', 'buff.ly', 'adf.ly', 'j.mp', 'coze.cn', 's.coze.cn'
    }
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check if domain is in known shortener list
        if domain in shortener_domains:
            return True
            
        # Check for other common patterns
        # - Very short domain
        # - Numeric or very short path
        if (len(domain) < 7 and len(parsed.path) < 10) or parsed.path.strip('/').isalnum():
            return True
            
        return False
        
    except Exception:
        return False 