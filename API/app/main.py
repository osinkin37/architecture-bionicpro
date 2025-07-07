from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from keycloak import KeycloakOpenID
from pydantic import BaseModel
from .reports import generate_report
import uvicorn

# Конфигурация Keycloak из docker-compose
KEYCLOAK_URL = "http://keycloak:8080"
KEYCLOAK_CLIENT_ID = "reports-api"
KEYCLOAK_REALM = "reports-realm"
KEYCLOAK_CLIENT_SECRET = "oNwoLQdvJAvRcL89SydqCWCe5ry1jMgq"

keycloak_openid = KeycloakOpenID(
    server_url=KEYCLOAK_URL,
    client_id=KEYCLOAK_CLIENT_ID,
    realm_name=KEYCLOAK_REALM,
    client_secret_key=KEYCLOAK_CLIENT_SECRET
)

app = FastAPI(title="Protected Reports API")

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token")

class User(BaseModel):
    id: str
    username: str
    roles: list[str]

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        token_info = keycloak_openid.decode_token(
            token,
            keycloak_openid.public_key(),
            options={"verify_aud": False}
        )
        return User(
            id=token_info.get("sub"),
            username=token_info.get("preferred_username"),
            roles=token_info.get("realm_access", {}).get("roles", [])
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def check_prothetic_access(user: User):
    if "prothetic_user" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden. Required role: prothetic_user"
        )

@app.get("/reports")
async def get_reports(user: User = Depends(get_current_user)):
    check_prothetic_access(user)
    return {
        "user": user.username,
        "reports": generate_report()
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)