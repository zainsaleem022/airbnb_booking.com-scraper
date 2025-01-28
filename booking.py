import urllib.parse as urlparse
import requests
from requests.exceptions import Timeout, RequestException
import logging
from bs4 import BeautifulSoup
import json
import gzip
from io import BytesIO
import brotli  # Import the Brotli library
import re
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




def parse_html_and_extract_results(html):
    """Parse HTML and extract listings from the results array in the specified script tag."""
    listing_data = []
    
    if not html:
        logger.warning("No HTML content provided.")
        return
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all script tags
    for script in soup.find_all('script'):

        # Check if the script tag has the specific attributes
        if script.get('data-capla-store-data') == 'apollo':

            if script.string and '"results":' in script.string:
                try:
                    # Extract JSON data from the script tag
                    script_content = script.string.strip()
                    json_data = json.loads(script_content)
                    
                    # Recursively search for the "results" array
                    results = find_results_in_json(json_data)

                    
                    if results is not None:
                        print(f"Length of results array: {len(results)}")
                    else:
                        logger.warning("'results' array not found in JSON data.")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON: {str(e)}")
                except Exception as e:
                    logger.error(f"Error parsing script content: {str(e)}")
    
    if results:
        for result in results:
            try:
                basic_property = result.get("basicPropertyData", {})
                price_info = result.get("priceDisplayInfoIrene", {}).get("displayPrice", {}).get("amountPerStay", {})
                reviews = basic_property.get("reviews", {})
                photos = basic_property.get("photos", {}).get("main", {}).get("highResUrl", {})

                # Process image URL
                relative_url = photos.get("relativeUrl", "")
                if relative_url:
                    # Replace image size and prepend base URL
                    modified_url = re.sub(r'max[^/]+', 'max800', relative_url)
                    full_image_url = f"https://cf.bstatic.com{modified_url}"
                else:
                    full_image_url = ""

                # Calculate prices
                amount_unformatted = price_info.get("amountUnformatted", 0)
                discounted_price = round(amount_unformatted * 0.85, 2)
                currency_symbol = "€" if "€" in price_info.get("amount", "") else "$"

                listing_data.append({
                    "Listing ID": basic_property.get("id"),
                    "Listing Type": None,
                    "Name": result.get("displayName", {}).get("text", ""),
                    "Title": result.get("displayName", {}).get("text", ""),
                    "Average Rating": f"{reviews.get('totalScore', 0)} ({reviews.get('reviewsCount', 0)})",
                    "Discounted Price": "",
                    "Original Price": "",
                    "Total Price": f"{currency_symbol}{discounted_price:.2f}",
                    "Picture": full_image_url,
                    "Website": "booking",
                    "Price": discounted_price
                })
                
            except Exception as e:
                logger.error(f"Error processing listing: {str(e)}")
                continue

        # print(f"Successfully processed {len(listing_data)} listings")
        return listing_data
    return []


def find_results_in_json(data):
    """Recursively search for the 'results' array in a JSON object."""
    if isinstance(data, dict):
        # Check if the current dictionary has a "results" key
        if "results" in data and isinstance(data["results"], list):
            return data["results"]
        
        # Recursively search in nested dictionaries
        for key, value in data.items():
            result = find_results_in_json(value)
            if result is not None:
                return result
    elif isinstance(data, list):
        # Recursively search in nested lists
        for item in data:
            result = find_results_in_json(item)
            if result is not None:
                return result
    
    # Return None if "results" is not found
    return None


def fetch_html_from_url(final_url):
    """Fetch HTML content from the final URL with Brotli and gzip decompression support."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',  # Indicates support for compressed responses
    }
    
    try:
        response = requests.get(
            final_url,
            headers=headers,
            timeout=10  # Total timeout (connect + read) in seconds
        )
        response.raise_for_status()  # Raise exception for 4xx/5xx status codes

        # Log response headers and raw content for debugging
        logger.debug("Response Headers: %s", response.headers)
        logger.debug("Raw Content (first 100 bytes): %s", response.content[:100])

        # Check the Content-Encoding header to determine decompression method
        content_encoding = response.headers.get('Content-Encoding', '').lower()

        if content_encoding == 'br':
            # Decompress Brotli response
            try:
                decompressed_data = brotli.decompress(response.content)
                return decompressed_data.decode('utf-8')  # Decode to string
            except brotli.error as e:
                # logger.error("Brotli decompression failed. Attempting fallback methods...")
                # Fallback: Try decoding as plain text
                return response.content.decode('utf-8', errors='replace')
        elif content_encoding == 'gzip':
            # Decompress gzip response
            compressed_data = BytesIO(response.content)
            decompressed_data = gzip.GzipFile(fileobj=compressed_data).read()
            return decompressed_data.decode('utf-8')  # Decode to string
        elif content_encoding == 'deflate':
            # Decompress deflate response
            import zlib
            decompressed_data = zlib.decompress(response.content)
            return decompressed_data.decode('utf-8')  # Decode to string
        else:
            # Assume plain text response
            return response.text
        
    except Timeout:
        logger.warning("Request timed out after 10 seconds - no content received")
    except RequestException as e:
        logger.error(f"Request failed: {str(e)}")
    
    return None  # Explicit return on failure

def find_link_with_listing_id(html, listing_id):
    """Find and print the link containing the specified listing ID in its query parameters."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Convert the listing ID to the substring format
    substring_to_find = str(listing_id)
    
    # Iterate through all anchor tags with href
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        
        # Parse the URL and extract query parameters
        parsed_url = urlparse.urlparse(href)
        query_params = urlparse.parse_qs(parsed_url.query)
        
        # Check if any query parameter value contains the substring
        for param, values in query_params.items():
            for value in values:
                if substring_to_find in value:
                    return href  # Return the first matching link
    
    print("No link found with the specified listing ID.")
    return None



def run_booking_bot(filters):
    """Main executor for Booking.com bot with error handling."""
    try:
        base_url = "https://www.booking.com/searchresults.html?"
        query_params = {}

        # Destination
        destination = getattr(filters, 'destination', 'islamabad')
        destination = str(destination).strip().rstrip('`')
        query_params['ss'] = destination

        # Language (fixed as per example)
        query_params['lang'] = 'en-us'

        # Check-in date
        checkin_date = '2025-01-20'
        if hasattr(filters, 'checkIn') and filters.checkIn:
            if isinstance(filters.checkIn, dict):
                checkin_date = filters.checkIn.get('date') or filters.checkIn.get('full', '').split('T')[0]
            elif isinstance(filters.checkIn, str):
                checkin_date = filters.checkIn
        query_params['checkin'] = checkin_date

        # Check-out date
        checkout_date = '2025-01-21'
        if hasattr(filters, 'checkOut') and filters.checkOut:
            if isinstance(filters.checkOut, dict):
                checkout_date = filters.checkOut.get('date') or filters.checkOut.get('full', '').split('T')[0]
            elif isinstance(filters.checkOut, str):
                checkout_date = filters.checkOut
        query_params['checkout'] = checkout_date

        # Guests
        guests = getattr(filters, 'guests', {})
        adults = guests.get('adults', 2)
        children = guests.get('children', 0)
        pets_count = guests.get('pets', 0)  # Get pets count from guests

        query_params['group_adults'] = str(adults)
        query_params['no_rooms'] = '1'
        query_params['group_children'] = str(children)

        if children > 0:
            children_ages = guests.get('children_ages', [])
            for i in range(children):
                if i < len(children_ages):
                    age = children_ages[i]
                else:
                    age = 1  # default age if not provided
                query_params.setdefault('age', []).append(str(age))

        # Initialize nflt filters list
        nflt_filters = []

        # Pets (now checked under guests)
        if pets_count > 0:
            nflt_filters.append('hotelfacility=4')

        # Swimming Pool
        if getattr(filters, 'hasPool', False):
            nflt_filters.append('hotelfacility=433')

        # Bedrooms
        bedrooms = getattr(filters, 'bedrooms', 0)
        if bedrooms > 0:
            nflt_filters.append(f'entire_place_bedroom_count={bedrooms}')

        # Bathrooms
        bathrooms = getattr(filters, 'bathrooms', 0)
        if bathrooms > 0:
            nflt_filters.append(f'min_bathrooms={bathrooms}')

        # Property Types
        property_type_mapping = {
            'apartment': 'ht_id=201',
            'guesthouse': 'ht_id=216',
            'hotel': 'ht_id=204',
            'house': 'privacy_type=3',
        }
        property_types = getattr(filters, 'propertyType', [])
        for prop_type in property_types:
            prop_type_lower = str(prop_type).lower()
            if prop_type_lower in property_type_mapping:
                nflt_filters.append(property_type_mapping[prop_type_lower])

        # Add nflt to query_params if any
        if nflt_filters:
            query_params['nflt'] = ';'.join(nflt_filters)

        # Build the query string
        query_string = urlparse.urlencode(query_params, doseq=True)

        final_url = base_url + query_string + "&selected_currency=EUR"
        # print(final_url)
        # Step 1: Fetch HTML content
        
        html = fetch_html_from_url(final_url)

        print(html)

        # Step 2: Parse HTML and extract results
        if html:
            listings = parse_html_and_extract_results(html)
            
        if listings:
             # Find best options
            valid_listings = [l for l in listings if l['Price'] != float('inf')]
            cheapest = min(valid_listings, key=lambda x: x['Price'], default=None)
        
        listing_id = cheapest.get("Listing ID")
        cheapest["Listing URL"] = find_link_with_listing_id(html, listing_id)
        
        
        return {
            "cheapest": cheapest
        }
        
        
    except Exception as e:
        print(f"Error: {e}")
