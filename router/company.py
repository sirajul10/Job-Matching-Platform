from Pydantic.companypydantic import CompanyPydantic,UpdateCompanyPy,Cmpmember,UpdateRole,Jobdata
from models import Companies,Users,CandidateProfile,CompanyMembers
from router.auth import get_current_user,get_db
from typing import Annotated
from fastapi import APIRouter,Depends,HTTPException,File,UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
from uuid import uuid4
import os

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
    return JSONResponse(status_code=201,content={'message':f'{newcmp.name} added successfull'})


@router.get("/company-details/{cmp_id}")
def company_details(db:db_dependency,user:user_dependency, cmp_id:int):
    ret_cmp = db.query(Companies).filter(Companies.id == cmp_id).first()
    if ret_cmp is None:
        raise HTTPException(status_code=401,detail="Company Not Found")

    return ret_cmp


@router.post("/add-company-member/{cmp_id}")
def add_company_member(db:db_dependency,user:user_dependency,newmebr:Cmpmember,cmp_id:int):
    cmpCreator = db.query(Companies).filter(Companies.created_by == user.get('id')).first()
    if cmpCreator is None:
        raise HTTPException(status_code=402,detail="You are not authenticated")

    cmpuser = db.query(Users).filter(Users.id == newmebr.user_id).first()
    if cmpuser is None:
        raise HTTPException(status_code=401,detail="User not found")

    cmpModel = CompanyMembers(
        user_id = newmebr.user_id,
        company_id = cmp_id,
        role = newmebr.role
    )
    db.add(cmpModel)
    db.commit()
    return JSONResponse(status_code=201,content={'message': f'{cmpuser.username} is added your company as a {newmebr.role}'})


@router.put("/update-company-member-permission/{cmp_id}/{member_id}")
def update_company_member_permission(db:db_dependency,user:user_dependency,newrole:UpdateRole,cmp_id:int,member_id:int):
    cmpCreator = db.query(Companies).filter(Companies.created_by == user.get('id')).first()
    if cmpCreator is None:
        raise HTTPException(status_code=402,detail="You are not authenticated")
    members = db.query(CompanyMembers).filter(CompanyMembers.id == member_id).first()
    
    if members.company_id != cmp_id:
        raise HTTPException(status_code=413,detail="Please Choose correct member")
    members.role = newrole.role
    db.commit()
    users = db.query(Users).filter(Users.id == members.user_id).first()
    return JSONResponse(status_code=400,content={'message': f'{newrole.role} has set for {users.username}'})


@router.delete("/delete-company-member/{cmp_id}/{member_id}")
def delete_company_member(db:db_dependency,user:user_dependency,cmp_id:int,member_id:int):
    cmpCreator = db.query(Companies).filter(Companies.created_by == user.get('id')).first()
    if cmpCreator is None:
        raise HTTPException(status_code=402,detail="You are not authenticated")
    members = db.query(CompanyMembers).filter(CompanyMembers.id == member_id).first()
    
    if members.company_id != cmp_id:
        raise HTTPException(status_code=413,detail="Please Choose correct member")

    users = db.query(Users).filter(Users.id == members.user_id).first()
    db.delete(members)
    db.commit()
    
    return JSONResponse(status_code=400,content={'message': f'{users.username} has Deleted'})

@router.get("/company-members/{cmp_id}")
def delete_company_member(db:db_dependency,user:user_dependency,cmp_id:int):
    cmpCreator = db.query(Companies).filter(Companies.created_by == user.get('id')).first()
    if cmpCreator is None:
        raise HTTPException(status_code=402,detail="You are not authenticated")
    members = db.query(CompanyMembers).filter(CompanyMembers.company_id == cmp_id).all()
    return members



   

@router.patch("/update-company/{cmp_id}")
def update_company(db: db_dependency, user: user_dependency, cmp_id: int, updatedata: UpdateCompanyPy):
    company = db.query(Companies).filter(Companies.id == cmp_id).first()

    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.created_by != user.get('id'):
        raise HTTPException(status_code=403, detail="You are not authorized to update this company")

    update_data = updatedata.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    if "name" in update_data and update_data["name"] is None:
        raise HTTPException(status_code=422, detail="Company name cannot be empty")

    for key, val in update_data.items():
        setattr(company, key, val)

    db.commit()
    db.refresh(company)

    return {"message": f"{company.name} updated successfully"}


@router.delete("/delete-company/{cmp_id}")
def delete_company(db: db_dependency, user: user_dependency, cmp_id: int):
    company = db.query(Companies).filter(Companies.id == cmp_id).first()

    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.created_by != user.get('id'):
        raise HTTPException(status_code=403, detail="You are not authorized to update this company")

    name = company.name

    db.delete(company)
    db.commit()

    return {"message": f"{name} has deleted"}

UPLOAD_DIR = Path("uploads/company_logos")
UPLOAD_DIR.mkdir(parents =True,exist_ok=True)

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
@router.post("/upload-company-logo/{cmp_id}")
def upload_company_logo(
    db: db_dependency,
    user: user_dependency,
    cmp_id: int,
    file: UploadFile = File(...)
):
    company = db.query(Companies).filter(
        Companies.id == cmp_id
    ).first()

    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.created_by != user.get('id'):
        raise HTTPException(status_code=403, detail="You are not authorized to upload this company logo")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG, PNG and WEBP images are allowed")

    file_content = file.file.read(MAX_FILE_SIZE + 1)

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Image size must not exceed 2 MB")

    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    extension = ALLOWED_TYPES[file.content_type]
    filename = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / filename

    try:
        with open(file_path,'wb') as f:
            f.write(file_content)
            if company.logo_url:
                old_file_name = Path(company.logo_url).name
                old_file = UPLOAD_DIR/old_file_name
                if old_file.is_file():
                    old_file.unlink()

            company.logo_url = f"/uploads/company_logos/{filename}"
            db.commit()
            db.refresh(company)
    except Exception:
        db.rollback()
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500,detail="Failed to upload company logo")
    return JSONResponse(status_code=201,content={
        'message':'company logo upload successfull',
        "logo_url":company.logo_url
    })


@router.post("/job-post/{cmp_id}")
def job_post(db:db_dependency,user:user_dependency,jobdata:Jobdata,cmp_id:int):
    pass