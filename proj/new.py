import shutil, uvicorn
from fastapi import FastAPI,File, UploadFile,Request,Form,HTTPException,status,Depends, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError,jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os,random,smtplib
from email.message import EmailMessage
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
import pymongo
load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
CONNECTION_STRING=os.getenv("CONNECTION_STRING")
Email_address=os.getenv("Email_ADDRESS")
EmailPassword=os.getenv("EMAIL_PASSWORD")
c = pymongo.MongoClient(CONNECTION_STRING)
db = "users1"
if db not in c.list_database_names():
    db = c[db]
db= c.get_database("users1")
col ="user_details1" 
if col not in db.list_collection_names():
    db.create_collection(col)
col=db.user_details1
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static",StaticFiles(directory="static"),name="static")
templates = Jinja2Templates(directory="templates")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html",{"request":request})
@app.get("/signin")
def signin(request:Request,respone:RedirectResponse):
    return templates.TemplateResponse("signin.html",{"request":request})
@app.get("/signup")
def signup(request: Request):
    return templates.TemplateResponse("signup.html",{"request":request})
@app.post("/newuser")
def newuser(request:Request,username: str = Form(),email:str=Form(),password: str = Form(),confirm_password:str=Form()):
    record=col.find_one({"Username":username})
    if record!=None and record["Username"] == username:
        return {"Error":"Username already taken"}
    email_verify_in_db = col.find_one({"Email":email})
    if email_verify_in_db != None and email_verify_in_db["Email"] == email:
        return {"Error":"One email can have only one account"}
    if password!=confirm_password:
        return {"Info":"password and retyped password are not same"}
    password=pwd_context.hash(password)
    code = random.randint(1000,9999)
    record ={"Username":username,
            "Email":email,
            "pswd":password,
            "code":code,
            "path":"static/images/user.png",
            "account":"user"
            }
    sendmail(email,code)
    col.insert_one(record)
    return templates.TemplateResponse("emailverifier.html",{"request":request,"username":record['Username']})
    # return templates.TemplateResponse("signin.html",{"request": request})
@app.post("/logincheck")
def logincheck(request: Request,response: Response,formdata: OAuth2PasswordRequestForm = Depends()):
    data={"Username":formdata.username,"pswd":formdata.password}
    if record:=col.find_one({"Username":formdata.username}):
        if record["code"] != "verified":
            return templates.TemplateResponse("emailverifier.html",{"request":request,"username":record["Username"]})
        return login(data,request,response)
@app.post("/verify_email")
def verify_email(*,username:str=Form(),code:int=Form(),request: Request):
    rec=col.find_one({"Username":username})
    if rec:
        if rec['code'] == code:
            col.update_one({"Username":username},{"$set":{"code":"verified"}})
            return templates.TemplateResponse("signin.html",{"request":request})
        else:
            return "Entered code is incorrect" 
    else:
        return "Username not found"
def login(data: dict,request:Request,response:RedirectResponse):
    record=col.find_one({"Username":data["Username"]})
    if record == None:
        return {"Error":"User not found in db"}
    elif pwd_context.verify(data['pswd'],record['pswd']):
        t=encoder(data)
        return templates.TemplateResponse("index.html",{"request":request,"username":data["Username"],"token":t})
    elif record['pswd'] != data["pswd"]:
        return {"hello":"hello"}
def encoder(data: dict):
        to_encode = data.copy()
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
@app.post("/verify_token")
def verify_token(data: dict):
    # return data['data']
    d = jwt.decode(data['data'],SECRET_KEY,ALGORITHM)
    record=col.find_one({"Username":d["Username"]})
    if record == None:
        return {"Error":"User not found in db"}
    elif pwd_context.verify(d["pswd"],record['pswd']):
        shipment_col=db['shipment_data']
        rec=shipment_col.find({'Username':d["Username"]})
        s={}
        i=1
        for r in rec:
            del r['_id']
            s[i]=r
            i+=1
        return {"verification":"success","username":record["Username"],"email":record['Email'],"profilepic":record['path'],'shipments':s,"account":record['account']}
    elif record['pswd'] != data["pswd"]:
        return False
    return{"d":d}
@app.get("/forgot_password")
def forgot_password(request:Request):
    return templates.TemplateResponse("forgotPassword.html",{"request":request})
@app.post("/codeSend")
def codeSend(request:Request,data:dict):
    rec = col.find_one({"Username":data['username']})
    if rec==None:
        return {"message":"User not found in Database"}
    code = random.randint(1000,9999)
    col.update_one({'Username':data['username']},{"$set":{"code":code}})
    sendmail(rec['Email'],code)
@app.post('/uploadPicPath')
def uploadPicPath(request:Request,username:str=Form(),profilePic: UploadFile=File(...)):
    rec=col.find_one({"Username":username})
    file_path=rec['path']
    if file_path!='static/images/user.png':
        if os.path.exists(file_path):
            col.update_one({'Username':username},{'$set':{'path':'static/images/user.png'}})
            os.remove(file_path)
    path=os.path.join('static/images/',profilePic.filename)
    with open(path, "wb") as image:
        shutil.copyfileobj(profilePic.file, image)
    col.update_one({"Username":username},{'$set':{'path':path}})
    return templates.TemplateResponse('index.html',{"request":request})
@app.post('/deleteProfilePic')
def deleteProfilePic(data:dict):
    rec=col.find_one({'Username':data['username']})
    file_path = rec['path']
    if file_path == 'static/images/user.png':
        return
    if os.path.exists(file_path):
        col.update_one({'Username':data['username']},{'$set':{'path':'static/images/user.png'}})
        os.remove(file_path)
    
@app.post("/updatePassword")
def updatePassword(request:Request,username:str=Form(),code:str=Form(),newPassword:str=Form(),confirmPassword:str=Form()):
    rec = col.find_one({"Username":username})
    print(code)
    print(rec['code'])
    if int(code)==rec['code']:
        print("hi")
        newPassword=pwd_context.hash(newPassword)
        col.update_one({'Username':username},{'$set':{'pswd':newPassword}})
        col.update_one({'Username':username},{"$set":{"code":"verified"}})
        return templates.TemplateResponse("signin.html",{'request':request})
    else:
        return templates.TemplateResponse("error.html",{"request":request,"error":"The code you entered is incorrect"})
    pass
@app.post('/createShipment')
def createShipment(request:Request,username:str=Form(),shipmentNumber:str=Form(),routeDetails:str=Form(),selectedDevice:str=Form(),PONumber:str=Form(),NDCNumber:str=Form(),snoofGoods:str=Form(),contNumber:str=Form(),goodsType:str=Form(),deliveryDate:str=Form(),deliveryNo:str=Form(),batchId:str=Form(),shipmentDescription:str=Form()):
    shipment_col1 ="shipment_data" 
    if shipment_col1 not in db.list_collection_names():
        db.create_collection(shipment_col1)
    shipment_col=db[shipment_col1]
    rec=shipment_col.find_one({'Shipment_Number':shipmentNumber})
    # if rec:
    #     return {"Error":"Shipment already Taken"}
    shipment_rec={"Username":username,"Shipment_Number":shipmentNumber,"RouteDetails":routeDetails,"SelectedDevice":selectedDevice,"PONumber":PONumber,"NDCNumber":NDCNumber,"SnoOfGoods":snoofGoods,"ContainerNo.":contNumber,"GoodsType":goodsType,"DeliveryDate":deliveryDate,"DeliveryNo":deliveryNo,"BatchId":batchId,"ShipmentDescription":shipmentDescription}
    shipment_col.insert_one(shipment_rec)
    return templates.TemplateResponse("index.html",{"request":request})
@app.post("/getDeviceData")
def getDeviceData(data:dict):
    deviceDataCol=db['device_data']
    d1=deviceDataCol.find()
    d2={}
    i=1
    for d in d1:
        del d['_id']
        d2[i]=d
        i+=1
    return {"data":d2}
def sendmail(email,code):
    msg=EmailMessage()
    msg['Subject']="Email verification"
    msg['From']=Email_address
    msg['To']=email
    msg.set_content(
        f"""\
    Name:{""}
    Email:{""}
    Message:{code}
    """,
    )
    with smtplib.SMTP_SSL('smtp.gmail.com',465) as smtp:
        smtp.login(Email_address,EmailPassword)
        smtp.send_message(msg)