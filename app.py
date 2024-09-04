from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import os
from gradio_client import Client, file
from zipfile import ZipFile
import json

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
client = Client("https://pragnakalp-ocr-image-to-text.hf.space/--replicas/ydkay/")

LINKS_FILE = 'links.json'

# Load and save links
def load_links():
    try:
        with open(LINKS_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_links(links):
    with open(LINKS_FILE, 'w') as file:
        json.dump(links, file)

links = load_links()
command = None 

# Process uploaded images
def process_images(files):
    links = load_links()
    clusters = {}
    for file in files:
        text = extract_text(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        for word in text.split():
            if word.startswith("#") and len(word) >= 3 and word[1].isalpha() and word[2:].isdigit():
                global command
                command = word[1]
                cluster = int(word[2:])
                if command == "A":
                    clusters.setdefault(cluster, []).append(file)
                elif command == "X":
                    return handle_command_b(cluster)
                break
    return clusters

# Handle command B
def handle_command_b(cluster_code):
    links = load_links()
    if str(cluster_code) in links:
        link = links[str(cluster_code)]
        return {"redirect": link}
    else:
        return {"redirect": url_for('add_link', cluster=cluster_code)}

@app.route('/')
def index():
    return render_template('index.html', links=links)

@app.route('/add_link/<cluster>', methods=['GET', 'POST'])
def add_link(cluster):
    links = load_links()
    if request.method == 'POST':
        link = request.form['link']
        links[cluster] = link
        save_links(links)
        return redirect(url_for('index'))
    return render_template('add_link.html', cluster=cluster)

def extract_text(image_path):
    result = client.predict("PaddleOCR", file(image_path), api_name="/predict")
    return result

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"})

    files = request.files.getlist('file')
    for file in files:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
    
    clusters = process_images(files)
    global command
    if command == 'X':
        return jsonify(clusters)

    zip_files = []
    for cluster, image_files in clusters.items():
        with ZipFile(f'{cluster}.zip', 'w') as zipf:
            for image in image_files:
                zipf.write(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
        zip_files.append(f'{cluster}.zip')
    
    return jsonify({"zip_files": zip_files})

@app.route('/download/<filename>')
def download(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
