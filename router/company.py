from Pydantic.companypydantic import CompanyPydantic
from models import Companies,Users,CandidateProfile
from router.auth import get_current_user,get_db
from typing import Annotated
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

router = APIRouter()
db_dependency = Annotated[Session,Depends(get_db)]
user_dependency = Annotated[dict,Depends(get_current_user)]

@router.post("/create-company")
def create_company(db:db_dependency,user:user_dependency,newcmp:CompanyPydantic):
    cmp = db.query(Companies).filter(Companies.name == newcmp.name).first()
    if cmp:
        raise HTTPException(status_code=404,detail="Company Already Exist")
    user_id = user.get('id')

    compModel = Companies(
        name = newcmp.name,
        description = newcmp.description,
        website = newcmp.website,
        logo_url = newcmp.logo_url,
        industry = newcmp.industry,
        size = newcmp.size,
        location = newcmp.location,
        created_by=user_id
    
    )
    db.add(compModel)
    db.commit()
    return JSONResponse(status_code=201,content={'message',f'{newcmp.name} added successfull'})

