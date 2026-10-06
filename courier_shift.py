from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import os
import uuid

courier_shift = Blueprint("courier_shift", __name__)

UPLOAD_FOLDER = os.path.join("uploads", "courier_shifts")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def save_camera_photo(photo, prefix):
    if not photo or not photo.filename:
        return None

    if photo.mimetype not in ALLOWED_TYPES:
        return None

    ext = os.path.splitext(photo.filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"

    filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_FOLDER, filename)
    photo.save(path)

    return filename


@courier_shift.route("/api/courier/shift/start", methods=["POST"])
def start_shift():
    """
    Kuryer ish boshlaganda:
    1. Ilova kamerani ochadi va yangi selfi oladi.
    2. Termo-sumka kamerada yangi suratga olinadi.
    3. GPS koordinatalari yuboriladi.
    4. Server vaqtni avtomatik qayd qiladi.

    Mobil ilovada galereya tanlash tugmasi berilmasligi kerak.
    """

    courier_id = request.form.get("courier_id")
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")
    bag_status = request.form.get("bag_status")

    selfie = request.files.get("selfie")
    bag_photo = request.files.get("bag_photo")

    if not courier_id:
        return jsonify({
            "ok": False,
            "error": "Kuryer ID kiritilmagan"
        }), 400

    if not latitude or not longitude:
        return jsonify({
            "ok": False,
            "error": "GPS lokatsiya aniqlanmadi"
        }), 400

    if not selfie:
        return jsonify({
            "ok": False,
            "error": "Jonli selfi talab qilinadi"
        }), 400

    if not bag_photo:
        return jsonify({
            "ok": False,
            "error": "Termo-sumka rasmi talab qilinadi"
        }), 400

    if bag_status not in {"yaroqli", "yaroqsiz"}:
        return jsonify({
            "ok": False,
            "error": "Sumka holatini belgilang"
        }), 400

    selfie_name = save_camera_photo(selfie, "selfie")
    bag_name = save_camera_photo(bag_photo, "bag")

    if not selfie_name or not bag_name:
        return jsonify({
            "ok": False,
            "error": "Rasm formati noto'g'ri"
        }), 400

    shift_data = {
        "courier_id": courier_id,
        "latitude": latitude,
        "longitude": longitude,
        "selfie": selfie_name,
        "bag_photo": bag_name,
        "bag_status": bag_status,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "online"
    }

    return jsonify({
        "ok": True,
        "message": "Kuryer ishga chiqdi",
        "shift": shift_data
    }), 201


@courier_shift.route("/api/courier/shift/location", methods=["POST"])
def update_location():
    data = request.get_json(silent=True) or {}

    courier_id = data.get("courier_id")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not courier_id or latitude is None or longitude is None:
        return jsonify({
            "ok": False,
            "error": "Kuryer ID va GPS koordinatalari kerak"
        }), 400

    return jsonify({
        "ok": True,
        "courier_id": courier_id,
        "latitude": latitude,
        "longitude": longitude,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })


@courier_shift.route("/api/courier/shift/end", methods=["POST"])
def end_shift():
    data = request.get_json(silent=True) or {}
    courier_id = data.get("courier_id")

    if not courier_id:
        return jsonify({
            "ok": False,
            "error": "Kuryer ID kerak"
        }), 400

    return jsonify({
        "ok": True,
        "courier_id": courier_id,
        "status": "offline",
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "message": "Ish vaqti yakunlandi"
    })
