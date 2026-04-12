# Bus tracker project - Tom H
# uses the BODS api to get live bus locations in london

import os
import requests
import xml.etree.ElementTree as ET
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # needed so the map html can talk to this server

# get the api key from environment variable
BODS_KEY = os.environ.get("BODS_KEY")

# london bounding box
LONDON_BOX = {
    "minLat": 51.28,
    "maxLat": 51.70,
    "minLon": -0.54,
    "maxLon": 0.27
}

def fetch_buses_from_bods(line=None):
    url = "https://data.bus-data.dft.gov.uk/api/v1/datafeed/"
    params = {
        "api_key": BODS_KEY,
        "boundingBox": f"{LONDON_BOX['minLon']},{LONDON_BOX['minLat']},{LONDON_BOX['maxLon']},{LONDON_BOX['maxLat']}"
    }
    if line:
        params["lineRef"] = line

    resp = requests.get(url, params=params, timeout=30)
    print("status:", resp.status_code)

    buses = []
    root = ET.fromstring(resp.content)
    ns = {"s": "http://www.siri.org.uk/siri"}

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
        except Exception as e:
            continue

    return buses

# route to get buses for a specific line e.g. /buses/25
@app.route("/buses/<line>")
def get_buses(line):
    try:
        buses = fetch_buses_from_bods(line=line)
        print(f"Found {len(buses)} buses on route {line}")
        return jsonify({"buses": buses, "count": len(buses)})
    except Exception as e:
        print("error:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/buses")
def get_all_buses():
    try:
        buses = fetch_buses_from_bods()
        return jsonify({"buses": buses, "count": len(buses)})
    except Exception as e:
        print("error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
