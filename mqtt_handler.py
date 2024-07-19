from fastapi import FastAPI
from app.database import get_session
from app.utils.om2m_lib import Om2m
from app.utils.utils import get_vertical_name, create_hash
from app.models.node import Node as DBNode
from app.models.node_owners import NodeOwners as DBNodeOwners
from app.models.user import User as DBUser
from app.models.sensor_types import SensorTypes as DBSensorType
from app.config.settings import OM2M_URL, MOBIUS_XM2MRI, JWT_SECRET_KEY, BROKER_ADDR, BORKER_PORT, DEFAULT_TOPIC

import paho.mqtt.client as mqtt
import json
import re
from threading import Thread

# Initialize Om2m instance
om2m = Om2m(MOBIUS_XM2MRI, OM2M_URL)

# Create a FastAPI app instance
app = FastAPI()
# Initialize the database session once at the start
session_generator = get_session()
session = next(session_generator)

def get_vendor(msg_topic):
    """
    Extracts the vendor name from the MQTT message topic.

    Args:
        msg_topic (str): The MQTT message topic.

    Returns:
        str: The vendor name extracted from the topic (or None if not found).
    """
    match = re.match(r"oneM2M/req/(.+)", msg_topic)
    if match:
        return match.group(1)
    else:
        return None

def create_cin(cin, authentication: str, token_id: str):
    with next(get_session()) as session:
        node = session.query(DBNode).filter(DBNode.token_num == token_id).first()
        if node is None:
            print("Node not found")
            return

    # Check if vendor is assigned to the node
    vendor = (
        session.query(DBUser.id, DBUser.user_type, DBUser.username, DBUser.email)
        .join(DBNodeOwners, DBNodeOwners.vendor_id == DBUser.id)
        .filter(DBNodeOwners.node_id == node.id)
        .first()
    )

    if vendor is None:
        print("Vendor not assigned to the node")
        return

    # Check Auth
    # get Bearer Token from headers
    bearer_auth_token = authentication
    if bearer_auth_token is None:
        print("Authorization token is missing")
        return
    bearer_auth_token = bearer_auth_token.split(" ")[1]

    # Hash
    hash_token = create_hash([vendor.email, node.node_data_orid], JWT_SECRET_KEY)
    if bearer_auth_token != hash_token:
        print("Authorization token is invalid")
        return

    vertical_name = get_vertical_name(node.sensor_type_id, session)
    print(node.orid, vertical_name)

    sensor_type = (
        session.query(DBSensorType)
        .filter(DBSensorType.id == node.sensor_type_id)
        .first()
    )
    print(cin, sensor_type)
    # cin = cin.dict()
    con = []
    # check if all of sensor_type.paramaters are in cin
    # if not, raise error
    # if it is then check if datatype matches with sensor_type.data_tpes[idx]
    for idx, param in enumerate(sensor_type.parameters):
        print(idx, param, cin, param in cin)
        if param not in cin:
            print("Missing parameter " + param)
            return
        expected_type = sensor_type.data_types[idx]
        if expected_type == "str" or expected_type == "string":
            expected_type = str
        elif expected_type == "int":
            expected_type = int
        elif expected_type == "float":
            expected_type = float

        if not isinstance(cin[param], expected_type):
            print("Wrong data type for "
            + param
            + ". Expected "
            + str(sensor_type.data_types[idx])
            + " but got "
            + str(type(cin[param])))
            return
        con.append(str(cin[param]))
        print(con)
    response = om2m.create_cin(
        vertical_name,
        node.node_name,
        str(con),
        lbl=list(cin.keys()),
    )
    if response.status_code == 201:
        return response.status_code
    elif response.status_code == 409:
        print("CIN already exists")
    else:
        print("Error creating CIN")

def on_connect(client, userdata, flags, rc):
    """Callback function executed upon successful connection."""
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(DEFAULT_TOPIC)
    else:
        print("Connection failed with code:", rc)

def on_message(client, userdata, msg):
    """Callback function triggered when a message is received on the subscribed topic."""
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        print(f"PATH : {get_vendor(msg.topic)} \nHEADER : {data['Authentication']} \n TOKEN_ID : {data['token_id']}\nDATA : {data['data']}")
        create_cin(data['data'], data['Authentication'], data['token_id'])
    except json.JSONDecodeError:
        print(f"Error: Payload could not be decoded as JSON: {msg.payload}")

# def mqtt_listener():
#     client = mqtt.Client()
#     client.on_connect = on_connect
#     client.on_message = on_message
#     client.connect(BROKER_ADDR, BORKER_PORT)
#     # Start the client loop indefinitely (stay connected)
#     client.loop_forever()

def start_mqtt_client():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_ADDR, BORKER_PORT)
    client.loop_forever()

@app.on_event("startup")
async def startup_event():
    Thread(target=start_mqtt_client, daemon=True).start()

# if __name__=="__main__":
#     mqtt_listener()
#     session.close()  # Close the session when the script ends
