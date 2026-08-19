"""Pydantic Settings for Google Ads API configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GoogleAdsSettings(BaseSettings):
    """Loads Google Ads API credentials from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_prefix="GOOGLE_ADS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    developer_token: str = Field(description="Google Ads API developer token")
    
    # --- OAuth2 Refresh Token Fields ---
    client_id: str = Field(default="", description="OAuth2 Client ID")
    client_secret: str = Field(default="", description="OAuth2 Client Secret")
    refresh_token: str = Field(default="", description="OAuth2 Refresh Token")
    
    # --- Service Account Fields (kept optional for fallback) ---
    service_account_path: str = Field(
        default="", 
        description="Path to service account JSON key file"
    )
    impersonated_email: str = Field(
        default="",
        description="Email of the Workspace user to impersonate (domain-wide delegation)",
    )
    
    login_customer_id: str = Field(
        default="",
        description="MCC customer ID (required for MCC-level access)",
    )
    customer_id: str = Field(
        default="",
        description="Default customer ID for operations",
    )

    def to_client_dict(self) -> dict:
        """Convert settings to a dict suitable for GoogleAdsClient.load_from_dict()."""
        config = {
            "developer_token": self.developer_token,
            "use_proto_plus": True,
        }
        
        # Route Auth: Use Refresh Token if provided, otherwise fallback to Service Account
        if self.client_id and self.client_secret and self.refresh_token:
            config["client_id"] = self.client_id
            config["client_secret"] = self.client_secret
            config["refresh_token"] = self.refresh_token
        elif self.service_account_path:
            config["json_key_file_path"] = str(Path(self.service_account_path).expanduser())
            if self.impersonated_email:
                config["impersonated_email"] = self.impersonated_email
        else:
            raise ValueError(
                "Missing credentials: You must provide either OAuth2 tokens "
                "(client_id, client_secret, refresh_token) OR a service_account_path."
            )

        if self.login_customer_id:
            config["login_customer_id"] = self.login_customer_id.replace("-", "")
            
        return config