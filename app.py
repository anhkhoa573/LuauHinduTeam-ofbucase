from flask import Flask, render_template, request, jsonify, Response
import os
import base64
import secrets
import requests
import hashlib
from datetime import datetime

app = Flask(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def upload_to_gist(encoded):
    """Upload Base64 code len GitHub Gist - luu vinh vien."""
    if not GITHUB_TOKEN:
        return None, "Chua cau hinh GITHUB_TOKEN tren Render."
    try:
        headers = {
            "Authorization": "token " + GITHUB_TOKEN,
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "description": "Lua Script " + datetime.utcnow().isoformat(),
            "public": False,
            "files": {
                "script.txt": {"content": encoded}
            }
        }
        r = requests.post("https://api.github.com/gists", json=data, headers=headers, timeout=20)
        if r.status_code == 201:
            return r.json()["id"], None
        return None, "GitHub " + str(r.status_code) + ": " + r.text[:150]
    except Exception as e:
        return None, "Loi upload: " + str(e)


def fetch_from_gist(gist_id):
    """Fetch Base64 code tu Gist."""
    if not GITHUB_TOKEN:
        return None
    try:
        headers = {"Authorization": "token " + GITHUB_TOKEN}
        r = requests.get("https://api.github.com/gists/" + gist_id, headers=headers, timeout=20)
        if r.status_code == 200:
            files = r.json().get("files", {})
            if "script.txt" in files:
                info = files["script.txt"]
                if info.get("truncated"):
                    raw = info.get("raw_url")
                    if raw:
                        r2 = requests.get(raw, headers=headers, timeout=20)
                        if r2.status_code == 200:
                            return r2.text
                return info.get("content", "")
    except Exception as e:
        print("Gist fetch error:", e)
    return None


def build_lua_loader(encoded):
    """Tao Lua loader chong dich nguoc manh."""
    chunks = [encoded[i:i+180] for i in range(0, len(encoded), 180)]

    parts = []
    parts.append("-- ANHKHOA VIP PROTECTION v3.0")
    parts.append("local _g=getfenv or function() return _ENV end")
    parts.append("local _e=_g()")
    parts.append("if _e._LOCK then return end")
    parts.append("_e._LOCK=true")
    parts.append("local _t=type")
    parts.append("local _s=string")
    parts.append("local _tb=table")
    parts.append("local _m=math")

    # Anti-debug nhe
    parts.append("if _e.debug and _e.debug.sethook then")
    parts.append("  local _c=0")
    parts.append("  local _old=_e.debug.sethook")
    parts.append("  _old(function() _c=_c+1 end,'l')")
    parts.append("  _old()")
    parts.append("  if _c>3 then return end")
    parts.append("end")

    # Decoder
    parts.append("local _b='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'")
    parts.append("local function _d(s)")
    parts.append("  s=_s.gsub(s,'[^'.._b..'=]','')")
    parts.append("  return (s:gsub('.',function(x)")
    parts.append("    if x=='=' then return '' end")
    parts.append("    local r,f='',(_b:find(x,1,true)-1)")
    parts.append("    for i=6,1,-1 do r=r..(f%2^i-f%2^(i-1)>0 and '1' or '0') end")
    parts.append("    return r")
    parts.append("  end):gsub('%d%d%d?%d?%d?%d?%d?%d?',function(x)")
    parts.append("    if #x~=8 then return '' end")
    parts.append("    local c=0")
    parts.append("    for i=1,8 do c=c+(x:sub(i,i)=='1' and 2^(8-i) or 0) end")
    parts.append("    return _s.char(c)")
    parts.append("  end))")
    parts.append("end")

    # Ghep chunks
    parts.append("local _p={")
    for chunk in chunks:
        parts.append("'" + chunk + "',")
    parts.append("}")
    parts.append("local _raw=_tb.concat(_p)")
    parts.append("local _code=_d(_raw)")

    # Xoa bien tam
    parts.append("_p=nil")
    parts.append("_raw=nil")
    parts.append("_b=nil")

    # Load
    parts.append("local _f=loadstring or load")
    parts.append("if not _f then return end")
    parts.append("local _ok,_err=pcall(_f,_code)")
    parts.append("if not _ok then return end")
    parts.append("_e._LOCK=nil")

    return chr(10).join(parts)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/encode", methods=["POST"])
def api_encode():
    try:
        data = request.get_json()
        code = data.get("code", "").strip()

        if not code:
            return jsonify({"ok": False, "error": "Nhap code Lua!"})

        if len(code) > 500000:
            return jsonify({"ok": False, "error": "Code qua dai (toi da 500KB)."})

        encoded = base64.b64encode(code.encode("utf-8")).decode("utf-8")

        gist_id, err = upload_to_gist(encoded)
        if not gist_id:
            return jsonify({"ok": False, "error": err})

        host = request.host_url.rstrip("/")
        raw_url = host + "/raw/" + gist_id

        return jsonify({
            "ok": True,
            "raw_url": raw_url,
            "loadstring_url": 'loadstring(game:HttpGet("' + raw_url + '"))()',
            "gist_id": gist_id,
            "original_size": len(code),
            "encoded_size": len(encoded)
        })

    except Exception as e:
        return jsonify({"ok": False, "error": "Loi: " + str(e)})


@app.route("/raw/<gist_id>")
def raw_script(gist_id):
    encoded = fetch_from_gist(gist_id)
    if not encoded:
        return "-- Script khong ton tai hoac da bi xoa.\nreturn", 404

    loader = build_lua_loader(encoded)

    ua = request.headers.get("User-Agent", "").lower()
    keywords = [
        "roblox", "delta", "executor", "synapse", "krnl", "fluxus",
        "evon", "codex", "wave", "solara", "xeno", "hydrogen",
        "argon", "rayfield", "httpget", "http_request", "swift",
        "trigon", "valyse", "sirhurt", "oxygen", "electron",
        "ronix", "byfron", "ares", "awp", "krampus", "lua", "http"
    ]
    is_executor = any(kw in ua for kw in keywords)

    if not is_executor:
        return render_template("protected.html"), 200

    return Response(loader, mimetype="text/plain")


@app.route("/api/check/<gist_id>")
def api_check(gist_id):
    encoded = fetch_from_gist(gist_id)
    if encoded:
        return jsonify({"ok": True, "size": len(encoded), "exists": True})
    return jsonify({"ok": False, "exists": False})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
