from flask import Flask, jsonify
from flask_cors import CORS
from bods_client.client import BODSClient
from bods_client.models import BoundingBox, SIRIVMParams, Siri
import os

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("BODS_KEY")
client = BODSClient(api_key=API_KEY)

LONDON_BBOX = BoundingBox(**{
    "min_latitude": 51.28, "max_latitude": 51.70,
    "min_longitude": -0.54, "max_longitude": 0.27,
})

@app.route("/buses")
def get_all_buses():
    params = SIRIVMParams(bounding_box=LONDON_BBOX)
    raw = client.get_siri_vm_data_feed(params=params)
    siri = Siri.from_bytes(raw)
    acts = siri.service_delivery.vehicle_monitoring_delivery.vehicle_activities
    buses = []
    for act in acts:
        mvj = act.monitored_vehicle_journey
        loc = mvj.vehicle_location
        if not loc: continue
        buses.append({
            "id":          str(mvj.vehicle_ref),
            "line":        str(mvj.published_line_name or "?"),
            "destination": str(mvj.destination_name or "?"),
            "operator":    str(mvj.operator_ref or "?"),
            "lat":         float(loc.latitude),
            "lon":         float(loc.longitude),
            "bearing":     float(mvj.bearing or 0),
        })
    return jsonify({"buses": buses, "count": len(buses)})

@app.route("/buses/<line>")
def get_buses_by_line(line):
    params = SIRIVMParams(bounding_box=LONDON_BBOX)
    raw = client.get_siri_vm_data_feed(params=params)
    siri = Siri.from_bytes(raw)
    acts = siri.service_delivery.vehicle_monitoring_delivery.vehicle_activities
    buses = []
    for act in acts:
        mvj = act.monitored_vehicle_journey
        loc = mvj.vehicle_location
        if not loc: continue
        if str(mvj.published_line_name).upper() != line.upper(): continue
        buses.append({
            "id":          str(mvj.vehicle_ref),
            "line":        str(mvj.published_line_name or "?"),
            "destination": str(mvj.destination_name or "?"),
            "operator":    str(mvj.operator_ref or "?"),
            "lat":         float(loc.latitude),
            "lon":         float(loc.longitude),
            "bearing":     float(mvj.bearing or 0),
        })
    return jsonify({"buses": buses, "count": len(buses)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
