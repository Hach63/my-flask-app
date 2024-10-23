from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_mail import Mail, Message
import os
import cv2
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# Configuration de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'YOUR_@'  # Remplacez par votre adresse e-mail
app.config['MAIL_PASSWORD'] = 'YOUR_PWD'  # Remplacez par votre mot de passe
app.config['MAIL_DEFAULT_SENDER'] = 'vdk@gmail.com'
app.secret_key = 'PWD'

# Dossier pour sauvegarder les images uploadées
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Exemple de données de produits
# Exemple de données de produits avec description de la texture
produits = [
    {"nom": "T-shirt", "prix": 20.00, "image": "static/images/tshirt.jpg", "categorie": "homme", 
     "description_texture": "Tissu en coton doux et léger avec une texture légèrement côtelée."},
    
    {"nom": "Jean", "prix": 40.00, "image": "static/images/jean.jpg", "categorie": "homme", 
     "description_texture": "Denim robuste et légèrement extensible avec une texture rugueuse."},
    
    {"nom": "Chaussures", "prix": 60.00, "image": "static/images/chaussures.jpg", "categorie": "homme", 
     "description_texture": "Cuir lisse et souple avec une finition mate."},
    
    {"nom": "Robe", "prix": 50.00, "image": "static/images/robe.jpg", "categorie": "femme", 
     "description_texture": "Tissu fluide en soie avec une texture douce et brillante."},
    
    {"nom": "Chapeaux", "prix": 40.00, "image": "static/images/chapeaux.jpg", "categorie": "femme", 
     "description_texture": "Feutre rigide avec une surface légèrement texturée."},
    
    {"nom": "Chaussures", "prix": 60.00, "image": "static/images/chaussures1.jpg", "categorie": "femme", 
     "description_texture": "Suède doux avec une texture veloutée et élégante."},
]


mail = Mail(app)

# Fonction pour extraire les caractéristiques d'une image
def extract_features(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    orb = cv2.ORB_create()
    keypoints, descriptors = orb.detectAndCompute(img, None)
    if descriptors is None:
        return np.array([])
    return descriptors.flatten()

# Fonction pour trouver des images similaires
# Fonction pour trouver des images similaires
def find_similar_images(uploaded_image_path):
    uploaded_features = extract_features(uploaded_image_path)
    similarities = []
    
    if uploaded_features.size == 0:
        return []  # Aucun feature détecté dans l'image uploadée

    image_dir = app.config['UPLOAD_FOLDER']
    uploaded_image_name = os.path.basename(uploaded_image_path).split('.')[0]  # Obtenir le nom de base sans extension

    for image_name in os.listdir(image_dir):
        if uploaded_image_name in image_name:  # Vérifier si le nom de base est dans le nom de l'image
            image_path = os.path.join(image_dir, image_name)
            image_features = extract_features(image_path)
            if image_features.size == 0:
                continue  # Ignorer si aucun feature détecté dans l'image

            min_len = min(len(uploaded_features), len(image_features))
            similarity = cosine_similarity([uploaded_features[:min_len]], [image_features[:min_len]])[0][0]
            similarities.append((image_name, similarity))

    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities


# Route pour la page d'index avec fonctionnalité d'upload
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            # Créer le dossier si nécessaire avant de sauvegarder le fichier
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            # Trouver des images similaires
            similar_images = find_similar_images(file_path)
            return render_template('index.html', uploaded_image=file.filename, similar_images=similar_images)
    
    return render_template('index.html')

# Route pour la page des produits
@app.route('/produit')
def produit():
    return render_template('produits.html', produits=produits)

# Routes pour gérer le panier
@app.route('/ajouter_au_panier', methods=['POST'])
def ajouter_au_panier():
    data = request.get_json()
    produit = {
        'nom': data['nom'],
        'prix': data['prix'],
        'image': data['image']
    }

    if 'panier' not in session:
        session['panier'] = []

    session['panier'].append(produit)
    session.modified = True

    return jsonify({'success': True, 'cart_count': len(session['panier'])})

@app.route('/panier', methods=['GET', 'POST'])
def panier():
    if request.method == 'POST':
        # Récupération des coordonnées du client depuis le formulaire
        client_name = request.form.get('client_name')
        client_email = request.form.get('client_email')
        client_phone = request.form.get('client_phone')

        # Enregistrement des coordonnées dans la session
        session['client_info'] = {
            'name': client_name,
            'email': client_email,
            'phone': client_phone
        }
        flash('Coordonnées du client enregistrées avec succès !', 'success')

    panier_articles = session.get('panier', [])
    client_info = session.get('client_info', {})

    return render_template('panier.html', articles=panier_articles, client_info=client_info)

@app.route('/retirer_du_panier', methods=['POST'])
def retirer_du_panier():
    data = request.get_json()
    nom = data['nom']

    if 'panier' in session:
        session['panier'] = [produit for produit in session['panier'] if produit['nom'] != nom]

    return jsonify({'success': True, 'cart_count': len(session['panier'])})

# Route pour la page de contact avec envoi d'e-mail
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        if not name or not email or not message:
            flash("Tous les champs doivent être remplis!", 'danger')
            return redirect(url_for('contact'))

        try:
            msg = Message(subject=f'Nouveau message de {name}',
                          recipients=['YOUR_@'],
                          body=f'Nom: {name}\nEmail: {email}\n\nMessage:\n{message}')
            
            mail.send(msg)
            flash('Votre message a été envoyé avec succès!', 'success')
        except Exception as e:
            flash(f"Une erreur s'est produite lors de l'envoi de l'e-mail : {str(e)}", 'danger')
        
        return redirect(url_for('contact'))
    
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)
