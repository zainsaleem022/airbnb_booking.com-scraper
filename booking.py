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
import time
from urllib.parse import quote
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_html_from_url(final_url):
    """Fetch HTML content from the final URL with Brotli and gzip decompression support."""
    
    # Use a session to persist headers & cookies
    session = requests.Session()

    
    headers = {
        "authority": "www.booking.com",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "max-age=0",
        "priority": "u=0, i",
        "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36"
    }
    
    cookies = {
        'pcm_personalization_disabled': '0',
        'bkng_sso_auth': 'CAIQsOnuTRpmKeQxi6MaBR7/5Y10VoWzhVrcH7OR92NSZHHNpyr/u0gc1XWKOekh9bOJFFOIlxmGvvnqYNMzTlrumrgJujct2yU+WXc/HuCOUJgIr/7Uvu0f8UwiV+ngT8vcR3o5YeFrZiSxjNRf',
        'pcm_consent': 'analytical%3Dtrue%26countryCode%3DPK%26consentId%3Dbfb591aa-6278-420a-9ad3-85e5b520f410%26consentedAt%3D2025-01-30T19%3A24%3A57.551Z%26expiresAt%3D2025-07-29T19%3A24%3A57.551Z%26implicit%3Dtrue%26marketing%3Dtrue%26regionCode%3DIS%26regulation%3Dnone%26legacyRegulation%3Dnone',
        '_ga_A12345': 'GS1.1.1738264271.13.1.1738265098.0.0.153265832',
        '_ga_SEJWFCBCVM': 'GS1.1.1738264271.11.1.1738265098.60.0.0',
        'lastSeen': '1738265098390',
        'FPID': 'FPID2.2.Tq5tlTqSyoXtGc9QUng0XA5FfFGw6RDhwNyOR8hhXKM%3D.1737617103',
        'FPLC': 'QDhVOlEV1u8iqqw%2FUjcgFWXXxgBVReO%2BgaoaFBkeDknbcJ%2Fo06y84HnUHMeZ%2Brwi4bcdZE6wOCv72XRacUkBJGuRZ%2FrEZ0XcRHZCInOYM%2Fgdn3Agz85NV6Gy%2BPy4FA%3D%3D',
        'cors_js': '1',
        'OptanonConsent': f'isGpcEnabled=0&datestamp=Fri+Jan+31+2025+00%3A24%3A58+GMT%2B0500+(Pakistan+Standard+Time)&version=202403.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=f68af335-eb79-4357-b9cf-16807686c9d8&interactionCount=0&isAnonUser=1&landingPath={quote(final_url)}',
        'bkng_prue': '1',
        'cgumid': '0eY4oOE3SZ9jJ7fNnQVdI4-qegdbxmgF',
        'bkng_sso_session': 'e30',
        'bkng_sso_ses': 'e30',
        'AMP_TOKEN': '%24NOT_FOUND',
        '_ga': 'GA1.2.828592122.1738265101',
        '_gid': 'GA1.2.2013143855.1738265102',
        '_pin_unauth': 'dWlkPVpXUXhOV0V5WWpZdFlqQXpNQzAwT0Rnd0xXSmpNR010Wmpkak5UbGtOR0UyWVdVMg',
        'cto_bundle': 'tQoHiV94WFNzQlQ3MzQxU1hmOWFFdHJVZ0NnVUplTmRJOENOMnY2QWtLNTJZTllHdSUyRng3aGFxNm9ZVzlYdWhORGRaYTAlMkZsM3N6MjVOJTJGdVN4cmxTMTl0NW5YZGZtNiUyQlFBZEFTJTJCbzRUUVVhdnFtNm1CeElNdVpQZUZlZ1VNQjRvJTJGQ1FTTkdyYjFEUGR5RVoxbHpmcktuJTJCOEY5Q0tSTGtiRlY5cWNjRHpDenhEJTJCbFB0ZCUyQmhtaGRHY2swMDlwOUhIMDd3OENGYmJZcmd0dnI3RSUyQlQ5cXhQdnpZUGNkR1picXJRSW1TJTJGQlZ5Qno3TkNPVGs2YXFydiUyRkhHeW5yMmVhOHNtN1pW',
        'bkng': '11UmFuZG9tSVYkc2RlIyh9Yaa29%2F3xUOLbca8KLfxLPedWG1lygLsik1vDj1Qv%2BUxMqpP9mm%2BWUc7ru67exlvDSuKCoC7%2BV4ClMU2OxocjoMnmlQQgc1gW195upt6nU4RofDd67B1GkrQxFu3KZngr8G2Xi53TECixUEh4TNye4cWdOk%2Fz3o3NHAYPO3YCbIyh8qXicKqM5Gw%3D',
        'aws-waf-token': 'f47b6f13-0805-437b-a9bd-28ed6a3aa5de:BQoAtHWHtzWLAAAA:evoGVCHKGVSY0sc7Dk3JKjckY78fhHHk/IRPccifrWCEn2bipt0Kd2REB8PTDEoscUxPYPEkR3mvPqoZiFGCBuE3dkQ0ljtVXCPcK2rSYflFVWVkSVYrU2/WDGF0ycdiNHzsv9X9GMURnNckv3BT0OuJnNE8MWRIlTHQkyQDOzSP6nksUpB3ubkyHm1BCz9dp1EbBXTFcM9iEiMOxUK6jHimzyGTdRJuoiv7zpZPQoh7puLJUpI9i3nbyj3EGL63Bi4=',
        '_gat': '1'
    }
    
    retries = 0
    max_retries = 2
    retry_delay = 1
    
    while retries < max_retries:
        try:
            response = requests.get(
                final_url,
                headers=headers,
                cookies=cookies,
                timeout=10
            )
            print(response)
            
            if response.status_code == 202:
                # If the status code is 202, wait and retry
                retries += 1
                time.sleep(retry_delay)
                continue
            elif response.status_code == 200:
                # If the status code is 200, proceed with processing the response
                response.raise_for_status()  # Raise exception for 4xx/5xx status codes

                # Log response headers and raw content for debugging
                logger.debug("Response Headers: %s", response.headers)
                logger.debug("Raw Content (first 100 bytes): %s", response.content[:100])

                return response.content  # Return the HTML content
            else:
                # Handle other status codes if needed
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            logger.error("Request failed: %s", e)
            break

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
    
    return None  # Explicit return on failure


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

                    
                    # if results is not None:
                    #     print(f"Length of results array: {len(results)}")
                    # else:
                    #     logger.warning("'results' array not found in JSON data.")

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

        # Step 2: Parse HTML and extract results
        if html:
            listings = parse_html_and_extract_results(html)
            
        
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
