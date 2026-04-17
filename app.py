# bus tracker - Tom H
# this file runs the server that gets live bus data from the government api

import os
import requests
import xml.etree.ElementTree as ET
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # this lets the html page talk to the server without getting blocked

# api key is stored as an environment variable so its not hardcoded
BODS_KEY = os.environ.get("BODS_KEY")

# rough bounding box around london
LONDON_BOX = {
    "minLat": 51.28,
    "maxLat": 51.70,
    "minLon": -0.54,
    "maxLon": 0.27
}

# this function calls the bods api and parses the xml it sends back
def fetch_buses_from_bods(line=None):
    url = "https://data.bus-data.dft.gov.uk/api/v1/datafeed/"
    
    # build the request params
    params = {
        "api_key": BODS_KEY,
        "boundingBox": f"{LONDON_BOX['minLon']},{LONDON_BOX['minLat']},{LONDON_BOX['maxLon']},{LONDON_BOX['maxLat']}"
    }
    
    # if a line number is given only get buses for that route
    if line:
        params["lineRef"] = line

    resp = requests.get(url, params=params, timeout=30)
    print("api response status:", resp.status_code)

    buses = []
    
    # bods sends back xml so we have to parse through it
    root = ET.fromstring(resp.content)
    
    for activity in root.iter("{http://www.siri.org.uk/siri}VehicleActivity"):
        try:
            vj = activity.find(".//{http://www.siri.org.uk/siri}MonitoredVehicleJourney")
            
            # get the gps coordinates
            lat = float(vj.find("{http://www.siri.org.uk/siri}VehicleLocation/{http://www.siri.org.uk/siri}Latitude").text)
            lon = float(vj.find("{http://www.siri.org.uk/siri}VehicleLocation/{http://www.siri.org.uk/siri}Longitude").text)
            
            # get other info about the bus
            line_name = vj.findtext("{http://www.siri.org.uk/siri}PublishedLineName", "Unknown")
            dest = vj.findtext("{http://www.siri.org.uk/siri}DestinationName", "Unknown")
            vehicle_ref = vj.findtext("{http://www.siri.org.uk/siri}VehicleRef", "Unknown")
            operator = vj.findtext("{http://www.siri.org.uk/siri}OperatorRef", "Unknown")
            
            # bearing might not always be there so handle that
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
            # skip any buses with missing data
            continue

    return buses


# endpoint to get buses for a specific route e.g. /buses/35
@app.route("/buses/<line>")
def get_buses(line):
    try:
        buses = fetch_buses_from_bods(line=line)
        print(f"found {len(buses)} buses on route {line}")
        return jsonify({"buses": buses, "count": len(buses)})
    except Exception as e:
        print("something went wrong:", e)
        return jsonify({"error": str(e)}), 500


# endpoint to get all buses at once
@app.route("/buses")
def get_all_buses():
    try:
        buses = fetch_buses_from_bods()
        return jsonify({"buses": buses, "count": len(buses)})
    except Exception as e:
        print("something went wrong:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)

