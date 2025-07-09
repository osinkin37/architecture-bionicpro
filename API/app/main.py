from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from keycloak import KeycloakOpenID
from pydantic import BaseModel
from .reports import generate_report
import uvicorn
import logging
import traceback
import sys
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api.log')
    ]
)

# Конфигурация Keycloak
KEYCLOAK_URL = "http://keycloak:8080"
KEYCLOAK_CLIENT_ID = "reports-api"
KEYCLOAK_REALM = "reports-realm"
KEYCLOAK_CLIENT_SECRET = "oNwoLQdvJAvRcL89SydqCWCe5ry1jMgq"

# Инициализация Keycloak
try:
    keycloak_openid = KeycloakOpenID(
        server_url=KEYCLOAK_URL,
        client_id=KEYCLOAK_CLIENT_ID,
        realm_name=KEYCLOAK_REALM,
        client_secret_key=KEYCLOAK_CLIENT_SECRET
    )
    logging.info("Keycloak client initialized successfully")
except Exception as e:
    logging.critical(f"Failed to initialize Keycloak client: {str(e)}")
    sys.exit(1)

app = FastAPI(title="Protected Reports API")

# CORS middleware
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
    """Получение текущего пользователя из JWT токена"""
    try:
        logging.debug(f"Token received: {token[:15]}...")
        
        # Получаем публичный ключ вручную
        public_key = "-----BEGIN PUBLIC KEY-----\n" + \
                    keycloak_openid.public_key() + \
                    "\n-----END PUBLIC KEY-----"
        
        token_info = keycloak_openid.decode_token(
            token,
            public_key,
            options={"verify_aud": False}
        )
        
        user = User(
            id=token_info.get("sub"),
            username=token_info.get("preferred_username"),
            roles=token_info.get("realm_access", {}).get("roles", [])
        )
        
        logging.info(f"User authenticated: {user.username}")
        return user
        
    except Exception as e:
        error_details = {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        logging.error(f"Authentication failed: {error_details}")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def check_prothetic_access(user: User):
    """Проверка наличия необходимой роли у пользователя"""
    try:
        if "prothetic_user" not in user.roles:
            logging.warning(
                f"Access denied for {user.username}. "
                f"Required role: prothetic_user, Actual roles: {user.roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden. Required role: prothetic_user"
            )
        logging.debug(f"Access granted for {user.username}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error in access check: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/reports")
async def get_reports(user: User = Depends(get_current_user)):
    """Получение отчетов (только для prothetic_user)"""
    try:
        check_prothetic_access(user)
        reports = generate_report()
        
        logging.info(f"Report generated for {user.username}")
        return {
            "user": user.username,
            "reports": reports,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Report generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )

if __name__ == "__main__":
    logging.info("Starting API server")
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_config=None
        )
    except Exception as e:
        logging.critical(f"Server failed to start: {str(e)}")
        sys.exit(1)