import yaml
from google_auth_oauthlib.flow import InstalledAppFlow

# Load OAuth client credentials directly from your google-ads.yaml file
with open("google-ads.yaml", "r") as f:
    yaml_config = yaml.safe_load(f)

CLIENT_ID = yaml_config.get("client_id")
CLIENT_SECRET = yaml_config.get("client_secret")

# Scope required for Google Ads API
SCOPES = ["https://www.googleapis.com/auth/adwords"]

def main():
    if not CLIENT_ID or CLIENT_ID == "CLIENT_ID":
        raise ValueError("Please set a valid client_id in google-ads.yaml")

    client_config = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    # Initialize the OAuth authorization flow
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    
    # Opens a local browser for user authentication
    credentials = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

    print("\n" + "="*50)
    print("SUCCESSFULLY GENERATED REFRESH TOKEN:")
    print("="*50)
    print(credentials.refresh_token)
    print("="*50)
    print("\nCopy this token into the `refresh_token:` field in your google-ads.yaml file.")

if __name__ == "__main__":
    main()