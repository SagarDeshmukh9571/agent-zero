import requests
import time
import os
import json
import threading
from typing import Optional, Dict, Any
from python.helpers import dotenv
from python.helpers import print_style

class OAuthManager:
    @staticmethod
    def github_copilot_start() -> Optional[Dict[str, Any]]:
        """
        Initiates GitHub Device Code Flow.
        Returns dictionary with device_code, user_code, verification_uri, etc.
        """
        client_id = "Iv1.b507a3d201c00000"
        try:
            resp = requests.post(
                "https://github.com/login/device/code",
                data={"client_id": client_id, "scope": "read:user"},
                headers={"Accept": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()
            if not all(k in data for k in ("device_code", "user_code", "verification_uri")):
                 print_style.print_red(f"Error getting device code: {data}")
                 return None
            return data
        except Exception as e:
            print_style.print_red(f"Error initiating GitHub login: {str(e)}")
            return None

    @staticmethod
    def github_copilot_poll(device_code: str, interval: int = 5, expires_in: int = 900) -> Optional[str]:
        """
        Polls for the GitHub token using the device code.
        Blocks until success, timeout, or error.
        Saves token to secrets on success.
        """
        client_id = "Iv1.b507a3d201c00000"
        start_time = time.time()

        while time.time() - start_time < expires_in:
            time.sleep(interval)
            try:
                token_resp = requests.post(
                    "https://github.com/login/oauth/access_token",
                    data={
                        "client_id": client_id,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
                    },
                    headers={"Accept": "application/json"}
                )

                if token_resp.status_code != 200:
                    continue

                token_data = token_resp.json()

                if "access_token" in token_data:
                    token = token_data["access_token"]
                    # Save to secrets
                    dotenv.save_dotenv_value("GITHUB_COPILOT_TOKEN", token)
                    return token

                error = token_data.get("error")
                if error == "authorization_pending":
                    continue
                elif error == "slow_down":
                    interval += 2
                elif error == "expired_token":
                    return None
                elif error == "access_denied":
                    return None
            except Exception:
                pass

        return None

    @staticmethod
    def github_copilot_login() -> Optional[str]:
        """
        CLI wrapper for GitHub Copilot login (blocking).
        """
        print_style.print_purple("Initiating GitHub Copilot authentication...")
        data = OAuthManager.github_copilot_start()
        if not data:
            return None

        print_style.print_green(f"\nPlease visit: {data['verification_uri']}")
        print_style.print_green(f"Enter code: {data['user_code']}\n")
        print_style.print_purple("Waiting for authentication... (Ctrl+C to cancel)")

        token = OAuthManager.github_copilot_poll(
            data['device_code'],
            data.get('interval', 5),
            data.get('expires_in', 900)
        )

        if token:
            print_style.print_green("Authentication successful! Saving token...")
            return token
        else:
            print_style.print_red("Authentication failed or timed out.")
            return None

    @staticmethod
    def google_oauth_setup():
        """Helper to guide user through Google ADC setup."""
        print_style.print_purple("Google Authentication Setup")
        print_style.print_purple("---------------------------")
        print("To use Google models (Gemini) via Vertex AI or Google AI Studio,")
        print("the recommended method is using Application Default Credentials (ADC).")
        print("\n1. Install Google Cloud CLI: https://cloud.google.com/sdk/docs/install")
        print("2. Run the following command in your terminal:")
        print_style.print_green("\n    gcloud auth application-default login\n")
        print("This will open your browser to authenticate and create a credentials file")
        print("that Agent Zero will automatically detect.")
        print("\nAlternatively, if you have a Google AI Studio API key, you can")
        print("set GOOGLE_API_KEY in your settings or secrets.env manually.")
