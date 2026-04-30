# bus tracker - Tom H
# this file is the backend server for the live bus tracking component
# it uses Flask to create a REST API that the map frontend calls every 10 seconds
# it fetches real time bus location data from the UK governments BODS API
# and returns it as clean JSON that the Google Maps frontend can use
 
import os
import requests
import xml.etree.ElementTree as ET
from flask import Flask, jsonify
from flask_cors import CORS
 
app = Flask(__name__)
CORS(app) # CORS allows the HTML map page to make requests to this server from a different origin
 
# the API key is stored as an environment variable rather than hardcoded in the code
# this is a security measure so the key is never exposed in the repository
# on Railway it is set in the environment variables dashboard
# locally it is set in the command line using: set BODS_KEY=your_key_here
BODS_KEY = os.environ.get("BODS_KEY")
 
# bounding box defining the geographic area we want bus data for
# these coordinates cover greater london
# the BODS API uses this to filter results to only buses within this area
LONDON_BOX = {
    "minLat": 51.28,
    "maxLat": 51.70,
    "minLon": -0.54,
    "maxLon": 0.27
}
 
# this function handles all communication with the BODS API
# BODS - Bus Open Data Service - is a UK government mandated service
# all bus operators in England are legally required to submit live GPS
# coordinates of every vehicle to this API every 10 to 30 seconds
# the optional line parameter allows filtering by route number e.g. "35"
def fetch_buses_from_bods(line=None):
    url = "https://data.bus-data.dft.gov.uk/api/v1/datafeed/"
    
    # build the query parameters for the API request
    # api_key authenticates our request
    # boundingBox restricts results to the london area
    params = {
        "api_key": BODS_KEY,
        "boundingBox": f"{LONDON_BOX['minLon']},{LONDON_BOX['minLat']},{LONDON_BOX['maxLon']},{LONDON_BOX['maxLat']}"
    }
    
    # if a specific route is requested add lineRef to filter the results
    if line:
        params["lineRef"] = line
 
    # make the HTTP GET request to the BODS API with a 30 second timeout
    resp = requests.get(url, params=params, timeout=30)
    print("api response status:", resp.status_code)
 
    buses = []
    
    # BODS returns data in SIRI-VM XML format rather than JSON
    # this is an older transport industry standard format
    # we use ElementTree to parse through the XML and extract the data we need
    root = ET.fromstring(resp.content)
    
    # each VehicleActivity element in the XML represents one bus
    # that is currently broadcasting its live location
    for activity in root.iter("{http://www.siri.org.uk/siri}VehicleActivity"):
        try:
            # MonitoredVehicleJourney contains all the data about the bus journey
            vj = activity.find(".//{http://www.siri.org.uk/siri}MonitoredVehicleJourney")
            
            # extract the real time GPS coordinates from VehicleLocation
            lat = float(vj.find("{http://www.siri.org.uk/siri}VehicleLocation/{http://www.siri.org.uk/siri}Latitude").text)
            lon = float(vj.find("{http://www.siri.org.uk/siri}VehicleLocation/{http://www.siri.org.uk/siri}Longitude").text)
            
            # extract additional journey information
            line_name = vj.findtext("{http://www.siri.org.uk/siri}PublishedLineName", "Unknown")
            dest = vj.findtext("{http://www.siri.org.uk/siri}DestinationName", "Unknown")
            vehicle_ref = vj.findtext("{http://www.siri.org.uk/siri}VehicleRef", "Unknown")
            operator = vj.findtext("{http://www.siri.org.uk/siri}OperatorRef", "Unknown")
            
            # bearing is the compass direction the bus is travelling in degrees
            # not all operators broadcast this so we check before accessing it
            bearing_el = vj.find("{http://www.siri.org.uk/siri}Bearing")
            bearing = float(bearing_el.text) if bearing_el is not None else 0.0
 
            # append each bus as a dictionary to our list
            # this gets converted to JSON before being sent to the map
            buses.append({
                "id": vehicle_ref,
                "line": line_name,
                "destination": dest,
                "operator": operator,
                "lat": lat,
                "lon": lon,
                "bearing": bearing
            })
        except:
            # if a vehicle record has missing or malformed data we skip it
            continue
 
    return buses
 
 
# Flask route that returns live buses for a specific route number
# called by the map every 10 seconds e.g. GET /buses/35
@app.route("/buses/<line>")
def get_buses(line):
    try:
        buses = fetch_buses_from_bods(line=line)
        print(f"found {len(buses)} buses on route {line}")
        # jsonify converts the python list to a proper JSON response
        return jsonify({"buses": buses, "count": len(buses)})
    except Exception as e:
        print("something went wrong:", e)
        return jsonify({"error": str(e)}), 500
 
 
# Flask route that returns all buses across london with no route filter
# useful for testing the API connection is working correctly
@app.route("/buses")
def get_all_buses():
    try:
        buses = fetch_buses_from_bods()
        return jsonify({"buses": buses, "count": len(buses)})
    except Exception as e:
        print("something went wrong:", e)
        return jsonify({"error": str(e)}), 500
 
 
# runs the development server locally when the file is executed directly
# when deployed on Railway, the Procfile handles startup using gunicorn instead
if __name__ == "__main__":
    app.run(debug=True)
