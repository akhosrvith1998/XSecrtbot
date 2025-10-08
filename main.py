import requests, time, json, os, hashlib, logging, traceback
from threading import Thread
from flask import Flask

BOT_TOKEN = "8416509515:AAEUSEFSOFdq8A0PmNOyn9-GVGjq-UnArUQ"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
DATA_FILE = "data.json"
POLL_TIMEOUT = 20

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logging.error("load error")
        traceback.print_exc()
        return {"users": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        logging.error("save error")
        traceback.print_exc()

def ensure_user(data, user_id):
    users = data.setdefault("users", {})
    if str(user_id) not in users:
        users[str(user_id)] = {
            "activated": False,
            "mode": None,
            "buffer": [],
            "files": {},
        }
    return users[str(user_id)]

def make_file_key(filename):
    return hashlib.sha1(filename.encode("utf-8")).hexdigest()[:10]

def build_panel_markup():
    return {"inline_keyboard":[[
        {"text":"ثبت محتوا","callback_data":"panel_register"},
        {"text":"مشاهده فایل ها","callback_data":"panel_list"},
        {"text":"حذف فایل","callback_data":"panel_delete"},
    ]]}

def build_nav_markup(file_key, index, total):
    prev_index = max(index-1,0)
    next_index = min(index+1,total-1)
    return {"inline_keyboard":[[
        {"text":"قبلی","callback_data":f"view|{file_key}|{prev_index}"},
        {"text":"بعدی","callback_data":f"view|{file_key}|{next_index}"},
    ]]}

def telegram_request(method, payload=None, files=None):
    url = f"{API_URL}/{method}"
    try:
        if files:
            r = requests.post(url,data=payload,files=files,timeout=30)
        else:
            r = requests.post(url,json=payload,timeout=30)
        return r.json()
    except Exception:
        logging.error("telegram request error")
        traceback.print_exc()
        return None

def send_message(chat_id,text,reply_markup=None):
    payload={"chat_id":chat_id,"text":text}
    if reply_markup is not None:
        payload["reply_markup"]=reply_markup
    return telegram_request("sendMessage",payload)

def send_media(chat_id,item,reply_markup=None):
    t=item.get("type")
    payload={"chat_id":chat_id}
    if reply_markup is not None:
        payload["reply_markup"]=reply_markup
    if t=="photo":
        payload["photo"]=item["file_id"]
        return telegram_request("sendPhoto",payload)
    if t=="video":
        payload["video"]=item["file_id"]
        return telegram_request("sendVideo",payload)
    if t=="document":
        payload["document"]=item["file_id"]
        return telegram_request("sendDocument",payload)
    if t=="audio":
        payload["audio"]=item["file_id"]
        return telegram_request("sendAudio",payload)
    payload["document"]=item["file_id"]
    return telegram_request("sendDocument",payload)

def edit_message_media(chat_id,message_id,item,reply_markup=None):
    media={"type":item["type"],"media":item["file_id"]}
    payload={"chat_id":chat_id,"message_id":message_id,"media":media}
    if reply_markup is not None:
        payload["reply_markup"]=reply_markup
    return telegram_request("editMessageMedia",payload)

def answer_callback(callback_query_id):
    return telegram_request("answerCallbackQuery",{"callback_query_id":callback_query_id})

def handle_update(update,data):
    try:
        if "message" in update:
            msg=update["message"]
            user=msg.get("from") or {}
            user_id=user.get("id")
            if user_id is None:
                return
            chat_id=msg["chat"]["id"]
            u=ensure_user(data,user_id)
            text=msg.get("text")
            if text is not None and text.strip()=="88077413Cph4W":
                u["activated"]=True
                u["mode"]=None
                u["buffer"]=[]
                save_data(data)
                send_message(chat_id,"ربات فعال شد. برای دیدن پنل بنویس: پنل")
                return
            if not u.get("activated"):
                return
            if u.get("mode")=="awaiting_filename" and text:
                filename=text.strip()
                if not u.get("buffer"):
                    send_message(chat_id,"هیچ محتوایی برای ذخیره در بافر وجود ندارد.")
                    u["mode"]=None
                    u["buffer"]=[]
                    save_data(data)
                    return
                key=make_file_key(filename)
                u["files"][key]={"name":filename,"items":u["buffer"][:]}
                u["buffer"]=[]
                u["mode"]=None
                save_data(data)
                send_message(chat_id,f'فایل "{filename}" ذخیره شد.')
                return
            if u.get("mode")=="awaiting_delete" and text:
                filename=text.strip()
                found_key=None
                for k,v in u["files"].items():
                    if v.get("name")==filename:
                        found_key=k
                        break
                if not found_key:
                    send_message(chat_id,f'فایل "{filename}" پیدا نشد.')
                else:
                    del u["files"][found_key]
                    save_data(data)
                    send_message(chat_id,f'فایل "{filename}" حذف شد.')
                u["mode"]=None
                return
            if u.get("mode")=="collecting":
                if "photo" in msg:
                    file_id=msg["photo"][-1]["file_id"]
                    u["buffer"].append({"file_id":file_id,"type":"photo"})
                    save_data(data)
                    return
                if "video" in msg:
                    file_id=msg["video"]["file_id"]
                    u["buffer"].append({"file_id":file_id,"type":"video"})
                    save_data(data)
                    return
                if "document" in msg:
                    file_id=msg["document"]["file_id"]
                    u["buffer"].append({"file_id":file_id,"type":"document"})
                    save_data(data)
                    return
                if "audio" in msg:
                    file_id=msg["audio"]["file_id"]
                    u["buffer"].append({"file_id":file_id,"type":"audio"})
                    save_data(data)
                    return
                if text and text.strip()=="00":
                    u["mode"]="awaiting_filename"
                    save_data(data)
                    send_message(chat_id,"اسم فایل رو بگو تا ذخیره کنم.")
                    return
                return
            if text and text.strip()=="پنل":
                send_message(chat_id,"پنل:",reply_markup=build_panel_markup())
                return
            if text:
                wanted=text.strip()
                found_key=None
                for k,v in u["files"].items():
                    if v.get("name")==wanted:
                        found_key=k
                        break
                if found_key:
                    items=u["files"][found_key]["items"]
                    if not items:
                        send_message(chat_id,"فایل خالی است.")
                        return
                    markup=build_nav_markup(found_key,0,len(items))
                    send_media(chat_id,items[0],reply_markup=markup)
                    return
            return
        if "callback_query" in update:
            cq=update["callback_query"]
            user=cq.get("from") or {}
            user_id=user.get("id")
            if user_id is None:
                return
            u=ensure_user(data,user_id)
            if not u.get("activated"):
                return
            data_payload=cq.get("data") or ""
            chat_id=cq["message"]["chat"]["id"]
            message_id=cq["message"]["message_id"]
            if data_payload=="panel_register":
                u["mode"]="collecting"
                u["buffer"]=[]
                save_data(data)
                answer_callback(cq["id"])
                send_message(chat_id,"بفرست..")
                return
            if data_payload=="panel_list":
                answer_callback(cq["id"])
                files=u.get("files",{})
                if not files:
                    send_message(chat_id,"هیچ فایلی ذخیره نشده.")
                    return
                txt="فایل‌های شما:\n"
                for k,v in files.items():
                    txt+=f"- {v.get('name')}\n"
                send_message(chat_id,txt)
                return
            if data_payload=="panel_delete":
                u["mode"]="awaiting_delete"
                save_data(data)
                answer_callback(cq["id"])
                send_message(chat_id,"اسم فایلی که میخوای حذف شه چیه؟")
                return
            if data_payload.startswith("view|"):
                answer_callback(cq["id"])
                try:
                    parts=data_payload.split("|")
                    if len(parts)!=3:
                        return
                    file_key=parts[1]
                    idx=int(parts[2])
                    if file_key not in u.get("files",{}):
                        send_message(chat_id,"فایل پیدا نشد.")
                        return
                    items=u["files"][file_key]["items"]
                    idx=max(0,min(idx,len(items)-1))
                    item=items[idx]
                    markup=build_nav_markup(file_key,idx,len(items))
                    edit_message_media(chat_id,message_id,item,reply_markup=markup)
                except Exception:
                    logging.error("view error")
                    traceback.print_exc()
                return
    except Exception:
        logging.error("handle_update error")
        traceback.print_exc()

app = Flask(__name__)

@app.route("/health")
def health():
    return "OK"

def keep_alive_loop():
    while True:
        try:
            for t in [2,4,6,9,11,13]:
                time.sleep(t*60)
                requests.get("http://localhost:5000/health")
        except:
            time.sleep(30)

def main_loop():
    data=load_data()
    offset=None
    while True:
        try:
            params={"timeout":POLL_TIMEOUT}
            if offset:
                params["offset"]=offset
            r=requests.get(f"{API_URL}/getUpdates",params=params,timeout=POLL_TIMEOUT+10)
            res=r.json()
            if not res.get("ok"):
                logging.error("getUpdates error: %s",res)
                time.sleep(1)
                continue
            updates=res.get("result",[])
            for up in updates:
                offset=up["update_id"]+1
                handle_update(up,data)
            save_data(data)
        except Exception:
            logging.error("main loop error")
            traceback.print_exc()
            time.sleep(1)

if __name__=="__main__":
    Thread(target=lambda: app.run(host="0.0.0.0",port=5000)).start()
    Thread(target=keep_alive_loop).start()
    main_loop()