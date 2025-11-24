import boto3
import json
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # These will be passed in from the Kubernetes deployment
    aws_region: str = os.environ.get("AWS_REGION", "us-east-1")
    db_credentials_secret_name: str = os.environ.get("DB_CREDENTIALS_SECRET_NAME", "fleet-dev-db-credentials")

    # Other App Settings
    secret_key: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    _database_url: str | None = None

    @property
    def database_url(self) -> str:
        if self._database_url is None:
            print("Database URL not cached. Fetching from AWS Secrets Manager...")
            try:
                session = boto3.session.Session()
                client = session.client(service_name='secretsmanager', region_name=self.aws_region)
                response = client.get_secret_value(SecretId=self.db_credentials_secret_name)
                secret = json.loads(response['SecretString'])

                db_username = secret['username']
                db_password = secret['password']
                db_host = secret['host']
                db_port = secret['port']
                db_name = secret['dbname']

                self._database_url = f"postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
                print("Successfully fetched and constructed Database URL.")
            except Exception as e:
                print(f"ERROR: Could not fetch secrets from AWS: {e}")
                self._database_url = "postgresql://user:pass@host:5432/db_error"
        return self._database_url

settings = Settings()