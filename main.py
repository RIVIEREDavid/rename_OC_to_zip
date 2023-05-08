import re
import streamlit as st
import zipfile
from PyPDF2 import PdfReader, PdfWriter
import io
import pytesseract
from pdf2image.pdf2image import convert_from_bytes
from datetime import datetime
import tempfile
from pathlib import Path

regex = re.compile(r"(4|5)50\d{7}|ENQA\s?\d{4}")


# Fonction de lecture OCR
def ocr(image):
    return pytesseract.image_to_string(image)


def extract_text(file_list):
    """
    Extraction du texte de chaque fichier et conversion en chaine de caractères.
    """
    text_list = []
    for file in file_list:
        pdf_reader = PdfReader(file)
        text = ""
        for i in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[i]
            text += page.extract_text()
        text_list.append(text)
    return text_list


def custom_date() -> str:
    custom_date = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")
    return custom_date


def rename_files(pdf_files):
    """
    Renommage des fichiers en fonctione de la regex
    """

    # initialisation de la liste des fichiers PDF
    new_pdf_files = []

    for file in pdf_files:
        pdf_reader = PdfReader(file)
        first_page_text = pdf_reader.pages[0].extract_text() # en testant le contenu de cette variable, on vérifie si on a affaire a un fichier PDF natif ou scanné.
        file_extension = Path(file.name).suffix

        # 2 CAS DE FIGURE A GERER

        # 1. SI FICHIER SCANNE:

        if first_page_text == "":

            # on va splitter chaque page du fichier pdf de type UploadedFile
            # pour ça on va commencer par créer une liste vide qui va contenir des noms de fichiers TEMPORAIRES correspondant à chaque n°de page du PDF d'origine
            # ceci afin de travailler sur le cloud Streamlit et non en local, ce que ne permet pas l'application
            page_list = []
            my_temp_dir = tempfile.TemporaryDirectory()

            # pour chaque page du PDF
            for num_page in range(len(pdf_reader.pages)):
                # création d'un writer
                pdf_writer = PdfWriter()
                # ajout de la page en-cour du fichier de départ
                pdf_writer.add_page(pdf_reader.pages[num_page])
                # création d'un nouveau nom temporaire
                new_file_name_temp = str(num_page).rjust(2, "0") + file_extension.lower()
                # création d'un nouveau chemin temporaire
                new_file_path_temp = Path(my_temp_dir.name) / new_file_name_temp
                # création du pdf modifié dans le dossier temporaire
                with open(new_file_path_temp, 'wb') as output_file:
                    pdf_writer.write(output_file)
                # on lit le contenu du fichier renommé
                with open(new_file_path_temp, 'rb') as f:
                    file_content = f.read()
                # on crée un objet BytesIO contenant le contenu du fichier renommé
                file_object = io.BytesIO(file_content)
                # enfin on ajoute cet objet à la liste
                page_list.append(file_object)

            # pour chaque liste de fichier temporaire
            for item in page_list:
                # on récupère le contenu
                item_data = item.getvalue()
                # on convertit en type bytes pour pouvoir exécuter le script ocr
                images = convert_from_bytes(item_data, dpi=200)
                text_result = ''
                for img in images:
                    img_to_text = ocr(img)
                    text_result += img_to_text
                po_list = sorted([i.group(0) for i in re.finditer(regex, text_result)])
                po_list_str = "_".join(set(po_list))
                if po_list_str == "":
                    new_file_name = custom_date() + "_" + "ERREUR_COMMANDE" + file_extension.lower()
                else:
                    new_file_name = custom_date() + "_" + po_list_str + file_extension.lower()
                new_pdf_files.append((new_file_name, item))

        # 2. SI FICHIER EST NATIF:

        else:

            my_temp_dir = tempfile.TemporaryDirectory()

            # pour chaque page du fichier on va vérifier si la regex existe dans le texte, si oui on garde la page et on renomme, sinon on continue:
            for num_page in range(len(pdf_reader.pages)):
                # on extrait le texte de la page en-cours de balayage et on créée une variable contenant la liste des commandes trouvées
                page_text = pdf_reader.pages[num_page].extract_text()
                po_list = sorted([i.group(0) for i in re.finditer(regex, page_text)], reverse=True)
                po_list_str = "_".join(set(po_list))
                # si cette liste est vide, alors on créée un fichier donc le nom contient "ERREUR_COMMANDE"
                if po_list_str == "":
                    new_file_name = custom_date() + "_" + "ERREUR_COMMANDE" + file_extension.lower()
                # sinon on ajoute la page dans un nouveau fichier pdf
                else:
                    # on crée une instance de la classe PdfWriter
                    pdf_writer = PdfWriter()
                    pdf_writer.add_page(pdf_reader.pages[num_page])
                    new_file_name = custom_date() + "_" + po_list_str + file_extension.lower()
                    new_file_path = Path(my_temp_dir.name) / new_file_name
                    with open(new_file_path, 'wb') as output_file:
                        pdf_writer.write(output_file)
                    # on lit le contenu du fichier renommé
                    with open(new_file_path, 'rb') as f:
                        file_content = f.read()
                    # on crée un objet BytesIO contenant le contenu du fichier renommé
                    file_object = io.BytesIO(file_content)
                    # on ajoute l'objet BytesIO contenant le fichier renommé à la liste des fichiers PDF renommés
                    new_pdf_files.append((new_file_name, file_object))
                                                           

    return new_pdf_files


@st.cache_data(persist="disk") #le décorateur st.cache_data permet de retourner le résultat de la fonction dans le cache, et non en local.
def zip_files(new_pdf_files):
    """
    Création d'un fichier zip temporaire à partir de la liste de fichiers PDF renommés.
    """
    zip_name = 'pdf_files.zip'
    with zipfile.ZipFile(zip_name, 'w') as myzip:
        for new_file_name, pdf_file in new_pdf_files:
            myzip.writestr(new_file_name, pdf_file.getvalue())
    # Vérifier si le fichier zip existe
    if Path(zip_name).exists():
        # Retourner le fichier zip sous forme de bytes
        zip_data = open(zip_name, 'rb').read()
        # Supprimer le fichier zip
        Path(zip_name).unlink()
        return zip_data
    else:
        # Retourner une valeur vide
        return None
    

if __name__ == "__main__":

    # Interface utilisateur avec Streamlit
    st.title('Renommer ARC')

    # Sélection des fichiers PDF
    pdf_files = st.file_uploader('Sélectionnez les fichiers PDF', type='pdf', accept_multiple_files=True)

    # Si des fichiers ont été sélectionnés, on les renomme et on les zippes
    if pdf_files:
        with st.spinner("Travail en cours... Merci de patienter"):
            new_pdf_files = rename_files(pdf_files)
            # appeler la fonction zip_files et stocker le résultat dans zip_data
        zip_data = zip_files(new_pdf_files)
        # vérifier que zip_data n'est pas égal à None
        if zip_data is not None:
            st.success('Les fichiers ont été renommés et zippés avec succès !')
            # Utiliser zip_data comme argument pour st.download_button
            st.download_button('Télécharger le fichier zip', data=zip_data, file_name=f'{custom_date()}_pdf_files.zip', mime='application/zip')
        else:
        # afficher un message d'erreur
            st.error("Le fichier zip n'a pas pu être créé.")