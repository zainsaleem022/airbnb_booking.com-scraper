from urllib.parse import urlencode, quote
import requests
from bs4 import BeautifulSoup
import json
import re
from concurrent.futures import ThreadPoolExecutor
import logging
from requests.exceptions import Timeout, RequestException


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_get(dictionary, keys, default=None):
    """Safely retrieve nested dictionary values."""
    for key in keys:
        try:
            dictionary = dictionary[key]
        except (KeyError, TypeError):
            return default
    return dictionary

def parse_price(price_str):
    """Parse price string to float with enhanced thousand separator handling."""
    if not price_str:
        return float('inf')
    
    try:
        # Remove all non-digit characters except commas and periods
        clean_str = re.sub(r'[^\d.,]', '', price_str)
        if not clean_str:
            return float('inf')

        # Handle thousand-separated numbers with periods (e.g., "1.639")
        if '.' in clean_str and ',' not in clean_str:
            parts = clean_str.split('.')
            # Check if all segments after the first are 3 digits (thousand separators)
            if all(len(part) == 3 for part in parts[1:]):
                clean_str = clean_str.replace('.', '')
            # Handle single-period cases like "12.345" (12 thousand 345)
            elif len(parts) == 2 and len(parts[-1]) == 3:
                clean_str = clean_str.replace('.', '')

        # Handle European format with comma as decimal (e.g., "1.234,56")
        if ',' in clean_str and '.' in clean_str:
            # Prioritize comma as decimal if it appears after period
            if clean_str.index(',') > clean_str.index('.'):
                clean_str = clean_str.replace('.', '').replace(',', '.')
            else:
                clean_str = clean_str.replace(',', '')
        elif ',' in clean_str:
            # Handle comma as decimal separator
            parts = clean_str.split(',')
            if len(parts) == 2 and parts[1].isdigit():
                clean_str = f"{parts[0]}.{parts[1]}"
            else:
                clean_str = clean_str.replace(',', '')

        return float(clean_str)
    except Exception as e:
        logger.warning(f"Price parsing error: {str(e)}")
        return float('inf')

def parse_review_count(rating_str):
    """Extract review count with improved pattern matching."""
    try:
        return int(re.search(r'(\d{1,3}(?:,\d{3})*)', rating_str.replace(',', '')).group(1))
    except Exception:
        return -1

def fetch_listings_html(url):
    """Robust HTML fetcher with direct GET request and timeout handling."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    }
    
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=10  # Total timeout (connect + read) in seconds
        )
        response.raise_for_status()  # Raise exception for 4xx/5xx status codes
        return response.text
        
    except Timeout:
        logger.warning("Request timed out after 10 seconds - no content received")
    except RequestException as e:
        logger.error(f"Request failed: {str(e)}")
    
    return None  # Explicit return on failure

def extract_listing_data(html):
    """Advanced data extraction with multiple fallback methods."""
    soup = BeautifulSoup(html, 'html.parser')
    listing_data = []
    
    # Method 1: Try official JSON data source
    script_data = None
    for script in soup.find_all('script'):
        if script.get('id') == 'data-deferred-state-0':
            try:
                script_data = json.loads(script.string)
                break
            except json.JSONDecodeError:
                continue
    
    # Method 2: Search for alternative data patterns
    if not script_data:
        for script in soup.find_all('script'):
            if 'niobeMinimalClientData' in script.text:
                try:
                    script_data = json.loads(script.string)
                    break
                except json.JSONDecodeError:
                    continue
    
    # Process found data
    if script_data:
        for item in safe_get(script_data, ['niobeMinimalClientData'], []):
            if isinstance(item, list) and len(item) > 1:
                results = safe_get(item[1], ['data', 'presentation', 'staysSearch', 'results', 'searchResults'], [])
                for result in results:
                    if result.get('__typename') == 'StaySearchResult':
                        try:
                            listing = result.get('listing', {})
                            price_info = result.get('pricingQuote', {})
                            
                            # Price parsing and discount calculation
                            total_price_str = safe_get(price_info, ['structuredStayDisplayPrice', 'secondaryLine', 'price'], '')
                            numeric_price = parse_price(total_price_str)
                            if numeric_price != float('inf'):
                                discounted_price = numeric_price * 0.85
                                currency_symbol = '€' if '€' in total_price_str else '$'
                                formatted_discounted_price = f"{currency_symbol}{discounted_price:.2f}"
                            else:
                                formatted_discounted_price = total_price_str
                            
                            # Image handling
                            contextual_pictures = result.get('contextualPictures', [])
                            picture_url = contextual_pictures[0].get('picture') if contextual_pictures else None
                            
                            listing_data.append({
                                "Listing ID": listing.get("id"),
                                "Listing Type": listing.get("listingObjType"),
                                "Name": listing.get("name"),
                                "Title": listing.get("title"),
                                "Average Rating": result.get('avgRatingLocalized'),
                                "Discounted Price": safe_get(price_info, ['structuredStayDisplayPrice', 'primaryLine', 'discountedPrice']),
                                "Original Price": safe_get(price_info, ['structuredStayDisplayPrice', 'primaryLine', 'originalPrice']),
                                "Total Price": formatted_discounted_price,
                                "Picture": picture_url,
                                "Website": "airbnb",
                                "Price": discounted_price
                            })
                        except Exception as e:
                            logger.warning(f"Error processing listing: {str(e)}")
    
    # Method 3: Fallback to HTML parsing (maintain original structure but won't match old format perfectly)
    if not listing_data:
        for card in soup.select('[data-testid="card-container"]'):
            try:
                listing_data.append({
                    "Listing ID": card.get('data-id'),
                    "Name": safe_get(card.select_one('[data-testid="listing-card-title"]'), ['text'], ''),
                    "Total Price": safe_get(card.select_one('._1jo4hgw'), ['text'], ''),
                    "Website": "airbnb",
                    "url": safe_get(card.select_one('a'), ['href'], ''),
                })
            except Exception as e:
                logger.warning(f"HTML fallback parse error: {str(e)}")
    
    return listing_data



def enhanced_fetch_listings(url):
    """Robust listing fetcher with retry logic."""
    try:
        html = fetch_listings_html(url)
        return extract_listing_data(html)
    except Exception as e:
        logger.error(f"Critical fetch failure: {str(e)}")
        return []

def run_airbnb_bot(filters):
    """Main executor with improved error handling."""
    try:
        # Base URL and common parameters
        base_url = "https://www.airbnb.es/s/"
        destination = getattr(filters, 'destination', 'islamabad')
        destination = destination.rstrip('`')  # Remove any trailing backticks
        base_url += f"{quote(str(destination), safe='')}/homes?"

        common_params = {
            'refinement_paths%5B%5D': '%2Fhomes',
            'flexible_trip_lengths%5B%5D': 'one_week',
            'price_filter_input_type': '0',
            'channel': 'EXPLORE',
            'source': 'structured_search_input_header',
            'search_type': 'filter_change',
            'search_mode': 'regular_search',
            'date_picker_type': 'calendar',
        }

        # Initialize query parameters with common parameters
        query_params = common_params.copy()
        selected_filter_order = []

        # Check-in and check-out dates
        if hasattr(filters, 'checkIn') and filters.checkIn:
            if isinstance(filters.checkIn, dict):
                checkin_date = filters.checkIn.get('date') or filters.checkIn.get('full', '').split('T')[0]
            elif isinstance(filters.checkIn, str):
                checkin_date = filters.checkIn
            else:
                checkin_date = '2025-01-20'  # Default or handle as needed
            query_params['checkin'] = checkin_date

        if hasattr(filters, 'checkOut') and filters.checkOut:
            if isinstance(filters.checkOut, dict):
                checkout_date = filters.checkOut.get('date') or filters.checkOut.get('full', '').split('T')[0]
            elif isinstance(filters.checkOut, str):
                checkout_date = filters.checkOut
            else:
                checkout_date = '2025-01-21'  # Default or handle as needed
            query_params['checkout'] = checkout_date

        # Guests
        if hasattr(filters, 'guests'):
            guests = getattr(filters, 'guests', {})
            query_params['adults'] = str(guests.get('adults', '1'))
            query_params['children'] = str(guests.get('children', '1'))
            infants = guests.get('infants', 0)
            if infants > 0:
                query_params['infants'] = str(infants)

        # Add pets to query parameters if present
        if hasattr(filters, 'guests') and filters.guests.get('pets', 0) > 0:
            query_params['pets'] = str(filters.guests.get('pets'))

        # Property Type mapping
        property_type_mapping = {
            'apartment': '3',
            'house': '1',
            'guesthouse': '2',
            'hotel': '4',
        }

        # Property Types
        if hasattr(filters, 'propertyType'):
            property_types = getattr(filters, 'propertyType', [])
            for prop_type in property_types:
                # Convert property type to lowercase
                prop_type_lower = str(prop_type).lower()
                if prop_type_lower in property_type_mapping:
                    prop_id = property_type_mapping[prop_type_lower]
                    if 'l2_property_type_ids%5B%5D' not in query_params:
                        query_params['l2_property_type_ids%5B%5D'] = []
                    query_params['l2_property_type_ids%5B%5D'].append(prop_id)
                    selected_filter_order.append(f'l2_property_type_ids%3A{prop_id}')

        # Bedrooms
        if hasattr(filters, 'bedrooms') and filters.bedrooms > 0:
            query_params['min_bedrooms'] = str(filters.bedrooms)
            selected_filter_order.append(f'min_bedrooms%3A{filters.bedrooms}')

        # Pool
        if hasattr(filters, 'hasPool') and filters.hasPool:
            if 'amenities%5B%5D' not in query_params:
                query_params['amenities%5B%5D'] = []
            query_params['amenities%5B%5D'].append('7')
            selected_filter_order.append('amenities%3A7')


        # Add bathrooms to query parameters if present
        if hasattr(filters, 'bathrooms') and filters.bathrooms > 0:
            bathroom_count = str(filters.bathrooms)
            query_params['min_bathrooms'] = bathroom_count
            selected_filter_order.append(f'min_bathrooms%3A{bathroom_count}')

        # Add selected_filter_order to query_params
        if selected_filter_order:
            query_params['selected_filter_order%5B%5D'] = selected_filter_order

        # Construct the query string
        query_string = urlencode(query_params, doseq=True, safe='%')

        # Original URL
        original_url = f"{base_url}{query_string}"
        
        # print(original_url)
        # original_result = fetch_and_parse_listings(original_url)
        # URL with cursor parameter
        cursor_param = "&cursor=eyJzZWN0aW9uX29mZnNldCI6MCwiaXRlbXNfb2Zmc2V0IjoxOCwidmVyc2lvbiI6MX0%3D"
        cursor_url = f"{original_url}{cursor_param}"
        
        # Fetch from multiple pages
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(enhanced_fetch_listings, original_url),
                executor.submit(enhanced_fetch_listings, cursor_url)
            ]
            results = [f.result() for f in futures]
        
        all_listings = [item for sublist in results for item in sublist]
        
        # Find best options
        valid_listings = [l for l in all_listings if l['Price'] != float('inf')]
        cheapest = min(valid_listings, key=lambda x: x['Price'], default=None)
        
        if cheapest:
            # Extract listing URL from global HTML
            listing_id = cheapest.get("Listing ID")
            cheapest["Listing URL"] = f"https://www.airbnb.es/rooms/{listing_id}"
         
        
        return {
            "cheapest": cheapest
        }
        
    except Exception as e:
        logger.error(f"Critical error in bot execution: {str(e)}")
        return {"error": "Failed to retrieve listings"}

