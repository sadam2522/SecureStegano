import os
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from PIL import Image
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load or generate key
key_path = "secret.key"
if not os.path.exists(key_path):
    with open(key_path, "wb") as f:
        f.write(Fernet.generate_key())
key = open(key_path, "rb").read()
fernet = Fernet(key)

# Enkripsi pesan
def encrypt_message(message):
    return fernet.encrypt(message.encode())

# Konversi byte ke bit string
def byte_to_bits(data):
    return ''.join([bin(byte)[2:].zfill(8) for byte in data])

# Konversi integer ke 32-bit bit string
def int_to_bits(n):
    return bin(n)[2:].zfill(32)

def embed_data(image_path, message):
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img).astype(np.uint8)
    flat_pixels = pixels.flatten()

    encrypted = encrypt_message(message)
    data_len = len(encrypted)
    data_bits = int_to_bits(data_len) + byte_to_bits(encrypted)

    if len(data_bits) > len(flat_pixels):
        raise ValueError("Data terlalu besar untuk gambar ini.")

    for i in range(len(data_bits)):
        modified = (int(flat_pixels[i]) & ~1) | int(data_bits[i])
        flat_pixels[i] = np.uint8(modified)

    new_pixels = flat_pixels.reshape(pixels.shape)
    stego_img = Image.fromarray(new_pixels, "RGB")
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'hasil_embed.png')
    stego_img.save(output_path)

    return output_path, encrypted.decode()


# Fungsi untuk mengekstrak pesan dari gambar
def extract_data(image_path):
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img).flatten()

    length_bits = ''.join([str(pixels[i] & 1) for i in range(32)])
    data_len = int(length_bits, 2)

    bits = [str(pixels[i] & 1) for i in range(32, 32 + (data_len * 8))]
    byte_data = bytes(int(''.join(bits[i:i+8]), 2) for i in range(0, len(bits), 8))

    return fernet.decrypt(byte_data).decode()

# ================= ROUTES ===================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/embed', methods=['POST'])
def embed():
    try:
        message = request.form['message']
        image = request.files['image']
        filename = secure_filename(image.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(input_path)

        output_path, encrypted_msg = embed_data(input_path, message)
        return render_template('result_embed.html',
                               image_path='uploads/hasil_embed.png',
                               encrypted=encrypted_msg)
    except Exception as e:
        return f"Gagal embed: {str(e)}"

@app.route('/extract', methods=['POST'])
def extract():
    try:
        image = request.files['image']
        filename = secure_filename(image.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(input_path)

        decrypted_msg = extract_data(input_path)
        return render_template('result_extract.html', message=decrypted_msg)
    except Exception as e:
        return f"Gagal extract: {str(e)}"

@app.route('/download')
def download():
    path = os.path.join(app.config['UPLOAD_FOLDER'], 'hasil_embed.png')
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
