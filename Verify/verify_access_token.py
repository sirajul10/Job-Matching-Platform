from datetime import timedelta,time, timezone,datetime
from jose import jwt

secret_key = "8e484fb160b3165eac1f581dd8b7a873f91920d45e3ff37bdad93523d71427c0"
Algorithm = "HS256"
def verify_token():
    pass
def generate_token(email:str, timevalue:timedelta,otp_number:int):
    encode = {
        "sub":email,
        "otp":otp_number
    }
    expires = datetime.now(timezone.utc)+timevalue
    encode.update({'exp':expires})
    return jwt.encode(
        encode,secret_key,algorithm=Algorithm
    )
   
    