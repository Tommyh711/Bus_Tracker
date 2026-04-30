# bus tracker backend 
# Flask server that fetches live bus data from the BODS API and returns it as JSON
# third party: Flask, flask-cors, requests (pip libraries), BODS API (UK government)

import os
import requests
import xml.etree.ElementTree as ET
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # allows the map HTML to call this server from a different origin

# API key stored as environment variable for security - set in Railway dashboard
BODS_KEY = os.environ.get("BODS_KEY")

# bounding box covering greater london
LONDON_BOX = {
    "minLat": 51.28,
    "maxLat": 51.70,
    "minLon": -0.54,
    "maxLon": 0.27
}

def fetch_buses_from_bods(line=None):
    # BODS - Bus Open Data Service - UK government API
    # legally requires all bus operators in England to submit live GPS every 10-30 seconds
    url = "https://data.bus-data.dft.gov.uk/api/v1/datafeed/"
    
    params = {
        "api_key": BODS_KEY,
        "boundingBox": f"{LONDON_BOX['minLon']},{LONDON_BOX['minLat']},{LONDON_BOX['maxLon']},{LONDON_BOX['maxLat']}"
    }
    
    if line:
        params["lineRef"] = line  # filter by route number if provided

    resp = requests.get(url, params=params, timeout=30)
    print("api response status:", resp.status_code)

    buses = []
    
    # BODS returns SIRI-VM XML format rather than JSON
    # parsing through it manually to extract the data we need
    root = ET.fromstring(resp.content)
    
    for activity in root.iter("{http://www.siri.org.uk/siri}VehicleActivity"):
        try:
            vj = activity.find(".//{http://www.siri.org.uk/siri}MonitoredVehicleJourney")
            
            lat = float(vj.find("{http://www.siri.org.uk/siri}VehicleLocation/{http://www.siri.org.uk/siri}Latitude").text)
            lon = float(vj.find("{http://www.siri.org.uk/siri}VehicleLocation/{http://www.siri.org.uk/siri}Longitude").text)
            line_name = vj.findtext("{http://www.siri.org.uk/siri}PublishedLineName", "Unknown")
            dest = vj.findtext("{http://www.siri.org.uk/siri}DestinationName", "Unknown")
            vehicle_ref = vj.findtext("{http://www.siri.org.uk/siri}VehicleRef", "Unknown")
            operator = vj.findtext("{http://www.siri.org.uk/siri}OperatorRef", "Unknown")
            bearing_el = vj.find("{http://www.siri.org.uk/siri}Bearing")
            bearing = float(bearing_el.text) if bearing_el is not None else 0.0

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
            continue  # skip buses with missing data

    return buses


# returns live buses for a specific route e.g. /buses/35
# called by the map frontend every 10 seconds
@app.route("/buses/<line>")
def get_buses(line):
    try:
        buses = fetch_buses_from_bods(line=line)
        print(f"found {len(buses)} buses on route {line}")
        return jsonify({"buses": buses, "count": len(buses)})
    except Exception as e:
        print("something went wrong:", e)
        return jsonify({"error": str(e)}), 500


# returns all buses across london, useful for testing
@app.route("/buses")
def get_all_buses():
    try:
        buses = fetch_buses_from_bods()
        return jsonify({"buses": buses, "count": len(buses)})
    except Exception as e:
        print("something went wrong:", e)
        return jsonify({"error": str(e)}), 500


# runs locally on Railway so the Procfile uses gunicorn instead
if __name__ == "__main__":
    app.run(debug=True)
