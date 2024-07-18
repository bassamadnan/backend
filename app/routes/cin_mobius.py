from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.auth.auth import (
    token_required,
    admin_required,
)
from app.database import get_session
from app.utils.om2m_lib import Om2m
from app.utils.utils import get_vertical_name, create_hash
from app.schemas.cin import (
    ContentInstance
)
from app.models.node import Node as DBNode
from app.models.node_owners import NodeOwners as DBNodeOwners
from app.models.user import User as DBUser
from app.models.sensor_types import SensorTypes as DBSensorType
from app.config.settings import OM2M_URL, MOBIUS_XM2MRI, JWT_SECRET_KEY

router = APIRouter()

om2m = Om2m(MOBIUS_XM2MRI, OM2M_URL)


@router.post("/create/{token_id}")
def create_cin(
    cin: ContentInstance,
    token_id: str,
    request: Request,
    session: Session = Depends(get_session),
    current_user=None,
):
    """
    Create a CIN (Content Instance) with the given name and labels.

    Args:
        cin (ContentInstance): The content instance object containing the path, content, and labels.
        token_id (str): The token ID.
        request (Request): The HTTP request object.
        session (Session, optional): The database session. Defaults to Depends(get_session).

    Returns:
        int: The status code of the operation.

    Raises:
        HTTPException: If the node token is not found, CIN already exists, or there is an error creating CIN.
    """
    _, _ = current_user, request
    node = session.query(DBNode).filter(DBNode.token_num == token_id).first()
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node token not found"
        )
    print(node)

    # Check if vendor is assigned to the node
    vendor = (
        session.query(DBUser.id, DBUser.user_type, DBUser.username, DBUser.email)
        .join(DBNodeOwners, DBNodeOwners.vendor_id == DBUser.id)
        .filter(DBNodeOwners.node_id == node.id)
        .first()
    )

    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not assigned to the node",
        )

    # Check Auth
    # get Bearer Token from headers
    bearer_auth_token = request.headers.get("Authorization")
    if bearer_auth_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is missing",
        )
    bearer_auth_token = bearer_auth_token.split(" ")[1]

    # Hash
    hash_token = create_hash([vendor.email, node.node_data_orid], JWT_SECRET_KEY)
    if bearer_auth_token != hash_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is invalid",
        )

    vertical_name = get_vertical_name(node.sensor_type_id, session)
    print(node.orid, vertical_name)

    sensor_type = (
        session.query(DBSensorType)
        .filter(DBSensorType.id == node.sensor_type_id)
        .first()
    )
    print(cin, sensor_type)
    cin = cin.dict()
    cont = cin['m2m:cin']['con']
    print(cin)
    print(len(eval(cont)),len(sensor_type.parameters),sep="\t==\t")
    if len(eval(cont)) != len(sensor_type.parameters):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing parameters",
        )
    lbls = sensor_type.parameters
    # check if all of sensor_type.paramaters are in cin
    # if not, raise error
    # if it is then check if datatype matches with sensor_type.data_tpes[idx]
    response = om2m.create_cin(
        vertical_name,
        node.node_name,
        str(cont),
        lbls
    )
    print(response.status_code)
    if response.status_code == 201:
        return response.status_code
    elif response.status_code == 409:
        raise HTTPException(status_code=409, detail="CIN already exists")
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating CIN",
        )
