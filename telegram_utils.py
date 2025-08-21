
import requests

def send_telegram(photo_path="alert.png"):
    token   = "__your_token__"
    chat_id = "__Your_chat_id__"
    url     = f"https://api.telegram.org/bot{token}/sendPhoto"

    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data  = {"chat_id": chat_id,
                     "caption": "⚠️ Có xâm nhập, nguy hiểm!"}
            r = requests.post(url, files=files, data=data)
            r.raise_for_status()
        print("Send success:", r.json())
    except Exception as ex:
        print("Cannot send telegram:", ex)
