import xml.etree.ElementTree as ET
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.auth.auth import (
    token_required,
    admin_required,
)
from app.database import get_session
from app.utils.om2m_lib import Om2m
from app.utils.utils import get_vertical_name
from app.schemas.cin import (
    ContentInstance,
    ContentInstanceGetAll,
    ContentInstanceDelete,
)
from app.models.node import Node as DBNode
from app.models.sensor_types import SensorTypes as DBSensorType
from app.config.settings import OM2M_URL, OM2M_USERNAME, OM2M_PASSWORD

router = APIRouter()

om2m = Om2m(OM2M_USERNAME, OM2M_PASSWORD, OM2M_URL)


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
    vertical_name = get_vertical_name(node.sensor_type_id, session)
    print(node.orid, vertical_name)

    sensor_type = (
        session.query(DBSensorType)
        .filter(DBSensorType.id == node.sensor_type_id)
        .first()
    )
    print(cin, sensor_type)
    cin = cin.dict()
    con = []
    # check if all of sensor_type.paramaters are in cin
    # if not, raise error
    # if it is then check if datatype matches with sensor_type.data_tpes[idx]
    for idx, param in enumerate(sensor_type.parameters):
        print(idx, param, cin, param in cin)
        if param not in cin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing parameter " + param,
            )
        expected_type = sensor_type.data_types[idx]
        if expected_type == "str":
            expected_type = str
        elif expected_type == "int":
            expected_type = int
        elif expected_type == "float":
            expected_type = float

        if not isinstance(cin[param], expected_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wrong data type for "
                + param
                + ". Expected "
                + str(sensor_type.data_types[idx])
                + " but got "
                + str(type(cin[param])),
            )
        con.append(str(cin[param]))
        print(con)
    response = om2m.create_cin(
        None,
        node.node_data_orid,
        str(con),
        lbl=list(cin.keys()),
    )
    if response.status_code == 201:
        return response.status_code
    elif response.status_code == 409:
        raise HTTPException(status_code=409, detail="CIN already exists")
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating CIN",
        )


@router.delete("/delete")
@token_required
@admin_required
def delete_cin(
    cin: ContentInstanceDelete,
    request: Request,
    session: Session = Depends(get_session),
    current_user=None,
):
    """
    Deletes a resource in OM2M.

    Parameters:
    - cin: ContentInstanceDelete object containing information about the Content Instance to be deleted.
    - request: Request object containing the HTTP request information.
    - session: Session object representing the database session.

    Raises:
    - HTTPException with status code 404 if the Node token is not found.
    - HTTPException with status code 200 if the CIN is deleted successfully.
    - HTTPException with status code 404 if the CIN is not found.
    - HTTPException with status code 500 if there is an error deleting the CIN.

    Returns:
    - None
    """
    node = session.query(DBNode).filter(DBNode.id == cin.node_id).first()
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node token not found"
        )

    try:
        response = om2m.delete_resource(f"{cin.path}/{cin.cin_id}")
        if response.status_code == 200:
            # the CIN can be deleted from the database (CLARIFICATION REQUIRED)
            raise HTTPException(status_code=200, detail="CIN deleted Successfully")
        elif response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="CIN not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting CIN. {e}",
        )
