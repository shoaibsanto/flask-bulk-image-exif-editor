from flask import Flask, render_template, request, send_file
from PIL import Image
import piexif
import io
import zipfile
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB limit

# Convert decimal degrees to DMS
def deg_to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(((deg - d) * 60 - m) * 60 * 100)
    return ((d, 1), (m, 1), (s, 100))

# Add EXIF metadata
def add_exif_data(img, title, subject, tags, comments, gps_latitude, gps_longitude):
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    exif_dict['0th'][piexif.ImageIFD.ImageDescription] = title.encode('utf-8')
    exif_dict['0th'][piexif.ImageIFD.XPSubject] = subject.encode('utf-16le')
    exif_dict['0th'][piexif.ImageIFD.XPKeywords] = tags.encode('utf-16le')
    exif_dict['0th'][piexif.ImageIFD.XPComment] = comments.encode('utf-16le')
    exif_dict['0th'][18246] = 99  # 5-star rating

    if gps_latitude is not None and gps_longitude is not None:
        exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = 'N' if gps_latitude >= 0 else 'S'
        exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = deg_to_dms(abs(gps_latitude))
        exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = 'E' if gps_longitude >= 0 else 'W'
        exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = deg_to_dms(abs(gps_longitude))

    exif_bytes = piexif.dump(exif_dict)
    output = io.BytesIO()
    img.save(output, format='JPEG', exif=exif_bytes)
    output.seek(0)
    return output

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        files = request.files.getlist("images")
        title = request.form.get("title")
        subject = request.form.get("subject")
        tags = request.form.get("tags")
        comments = request.form.get("comments")

        try:
            gps_lat = float(request.form.get("gps_latitude"))
            gps_lon = float(request.form.get("gps_longitude"))
        except (TypeError, ValueError):
            return "Latitude and Longitude must be selected from the map", 400

        updated_images = []
        for file in files:
            image = Image.open(file)
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            updated_img = add_exif_data(image, title, subject, tags, comments, gps_lat, gps_lon)
            filename = secure_filename(file.filename.rsplit('.', 1)[0] + ".jpg")
            updated_images.append((filename, updated_img))

        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, "a", zipfile.ZIP_DEFLATED) as zip_file:
            for fname, img_bytes in updated_images:
                zip_file.writestr(fname, img_bytes.read())
        zip_io.seek(0)

        return send_file(zip_io, mimetype="application/zip", as_attachment=True, download_name="updated_images.zip")

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
