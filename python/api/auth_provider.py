from python.helpers.api import ApiHandler, Request, Response
from python.helpers.oauth import OAuthManager
from python.helpers import print_style
import threading

class AuthProvider(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    async def process(self, input: dict, request: Request) -> dict:
        provider_id = input.get("provider_id", "").lower()
        stage = input.get("stage", "start") # start, poll

        if provider_id == "github_copilot":
            if stage == "start":
                data = OAuthManager.github_copilot_start()
                if data:
                    return {"status": "success", "data": data}
                else:
                    return {"status": "error", "message": "Failed to initiate GitHub login"}

            elif stage == "poll":
                device_code = input.get("device_code")
                if not device_code:
                    return {"status": "error", "message": "device_code required for polling"}

                # Poll once (non-blocking long term) or short timeout
                # Re-using the poll method but with short expire/interval to just check once or twice
                # Actually OAuthManager.github_copilot_poll blocks until expire.
                # We should probably modify it or just trust the frontend to call it
                # but if we call it here it will block the API thread (or async loop if not careful).
                # Since we are in async process, blocking is bad.
                # However, the polling logic in oauth.py uses time.sleep which is blocking.
                # We'll just check once.

                # To properly support polling via API without blocking, we should probably
                # implement a "check once" method in OAuthManager or just call the URL once here.
                # But reusing the logic is better.
                # Let's use a thread to poll in background if the user wants "auto poll"
                # OR just return instructions.

                # For this implementation, let's assume the frontend will call poll
                # and we want to return immediately if pending.

                # Let's create a non-blocking check or short timeout check
                import requests
                client_id = "Iv1.b507a3d201c00000"
                resp = requests.post(
                    "https://github.com/login/oauth/access_token",
                    data={
                        "client_id": client_id,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
                    },
                    headers={"Accept": "application/json"}
                )

                if resp.status_code == 200:
                    token_data = resp.json()
                    if "access_token" in token_data:
                        from python.helpers import dotenv
                        dotenv.save_dotenv_value("GITHUB_COPILOT_TOKEN", token_data["access_token"])
                        return {"status": "success", "token_saved": True}

                    error = token_data.get("error")
                    if error == "authorization_pending":
                        return {"status": "pending", "message": "Authorization pending"}
                    elif error == "slow_down":
                        return {"status": "pending", "message": "Slow down", "interval": 5}
                    else:
                        return {"status": "error", "message": error}

                return {"status": "error", "message": "Failed to check status"}

        elif provider_id == "google":
            # For Google, we just return instructions for now as it uses ADC local command
            return {
                "status": "info",
                "message": "For Google (Gemini), please run 'gcloud auth application-default login' in your terminal."
            }

        return {"status": "error", "message": f"Provider {provider_id} auth not implemented"}
