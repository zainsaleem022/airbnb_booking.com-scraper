from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import concurrent.futures
from airbnb import run_airbnb_bot  # Import the Airbnb bot function
from booking import run_booking_bot  # Import the Booking.com bot function
from fastapi import Request


app = FastAPI()

# Define the data model for the request body
class Filters(BaseModel):
    checkIn: dict
    checkOut: dict
    destination: str
    guests: dict
    propertyType: list
    bedrooms: int
    bathrooms: int
    hasPool: bool



# Default home route
@app.get("/")
async def home():
    return {"message": "Welcome to the Web Scraping API", "usage": "Send a POST request to /scrape with the appropriate filters to start scraping."}

# API endpoint to receive filters and run both bots in parallel
@app.post("/scrape")
async def scrape(request: Request):
    try:
        # Parse the JSON body
        filters_data = await request.json()
        filters = Filters(**filters_data)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            airbnb_future = executor.submit(run_airbnb_bot, filters)
            booking_future = executor.submit(run_booking_bot, filters)
            concurrent.futures.wait([airbnb_future, booking_future])
            airbnb_result = airbnb_future.result()
            booking_result = booking_future.result()


        combined_results = {
            "airbnb": airbnb_result,
            "booking": booking_result,
        }
        
        #print(combined_results)

        return {"message": "Scraping completed successfully", "results": combined_results}
    

    except Exception as e:
        print("Error in Server:", e)
        raise HTTPException(status_code=500, detail=str(e))

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
