from flask import jsonify

def format_sensor_data(sensor_data):
    formatted_data = {
        "labels": [],
        "datasets": []
    }
    
    for sensor in sensor_data:
        formatted_data["labels"].append(sensor["timestamp"])
        for dataset in sensor["readings"]:
            if not any(d["label"] == dataset["label"] for d in formatted_data["datasets"]):
                formatted_data["datasets"].append({
                    "label": dataset["label"],
                    "data": [],
                    "borderColor": dataset.get("color", "rgba(75, 192, 192, 1)"),
                    "backgroundColor": dataset.get("backgroundColor", "rgba(75, 192, 192, 0.2)"),
                })
            dataset_entry = next(d for d in formatted_data["datasets"] if d["label"] == dataset["label"])
            dataset_entry["data"].append(dataset["value"])
    
    return formatted_data

def generate_chart_options(title):
    return {
        "responsive": True,
        "maintainAspectRatio": False,
        "scales": {
            "x": {
                "type": "time",
                "time": {
                    "unit": "minute"
                },
                "title": {
                    "display": True,
                    "text": "Time"
                }
            },
            "y": {
                "title": {
                    "display": True,
                    "text": "Sensor Value"
                }
            }
        },
        "plugins": {
            "legend": {
                "display": True,
                "position": "top"
            },
            "title": {
                "display": True,
                "text": title
            }
        }
    }