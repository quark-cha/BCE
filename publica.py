import sys
import os
import json
import requests

# Leer configuración desde archivo JSON
def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# Buscar deposit_id desde el DOI en los depósitos del usuario
def get_deposit_id_from_doi(doi, token):
    print(f"🔎 Buscando deposit_id para DOI: {doi}")
    url = "https://zenodo.org/api/deposit/depositions"
    params = {'access_token': token}
    response = requests.get(url, params=params)
    response.raise_for_status()
    for dep in response.json():
        metadata = dep.get("metadata", {})
        prereserve = metadata.get("prereserve_doi", {})
        if metadata.get("doi") == doi or prereserve.get("doi") == doi:
            if dep.get("submitted") or dep.get("in_review"):
                raise ValueError("⚠️ El depósito está en revisión por una comunidad. Cancela la revisión antes de continuar.")
            return dep["id"]
    raise ValueError(f"❌ No se encontró ningún depósito en tu cuenta con DOI {doi}")

# Crear nueva versión del depósito
def create_new_version(deposit_id, token):
    url = f"https://zenodo.org/api/deposit/depositions/{deposit_id}/actions/newversion"
    params = {'access_token': token}
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()

# Subir archivo al nuevo depósito
def upload_file(deposit_id, file_path, token):
    url = f"https://zenodo.org/api/deposit/depositions/{deposit_id}/files"
    params = {'access_token': token}
    with open(file_path, "rb") as fp:
        file_name = os.path.basename(file_path)
        data = {'name': file_name}
        files = {'file': fp}
        response = requests.post(url, params=params, data=data, files=files)
        response.raise_for_status()
        return response.json()

# Actualizar metadatos
def update_metadata(deposit_id, metadata, token):
    url = f"https://zenodo.org/api/deposit/depositions/{deposit_id}"
    params = {'access_token': token}
    headers = {"Content-Type": "application/json"}
    data = {"metadata": metadata}
    response = requests.put(url, params=params, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    return response.json()

# Publicar depósito
def publish_deposit(deposit_id, token):
    url = f"https://zenodo.org/api/deposit/depositions/{deposit_id}/actions/publish"
    params = {'access_token': token}
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()

# Punto de entrada
if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Uso: python publica.py [config.json]")
        sys.exit(1)

    config_path = sys.argv[1] if len(sys.argv) == 2 else "config.json"
    config = load_config(config_path)

    token = config["token"]
    doi = config.get("doi")
    deposit_id = config.get("deposit_id")
    files = config.get("files", [])
    metadata = config["metadata"]

    try:
        if not deposit_id:
            if not doi:
                print("❌ Error: se requiere 'deposit_id' o 'doi' en el archivo JSON")
                sys.exit(1)
            deposit_id = get_deposit_id_from_doi(doi, token)

        print(f"🔁 Creando nueva versión del depósito: {deposit_id}")
        version_data = create_new_version(deposit_id, token)
        draft_url = version_data["links"]["latest_draft"]
        print(f"📎 Nueva versión creada. Enlace: {draft_url}")

        draft_response = requests.get(draft_url, params={'access_token': token})
        draft_response.raise_for_status()
        draft_data = draft_response.json()
        new_deposit_id = draft_data["id"]

        for file in files:
            if os.path.exists(file):
                print(f"📤 Subiendo archivo: {file}")
                upload_file(new_deposit_id, file, token)
            else:
                print(f"⚠️ Archivo no encontrado: {file}")

        print("📝 Actualizando metadatos...")
        update_metadata(new_deposit_id, metadata, token)

        print("🚀 Publicando depósito...")
        publish_resp = publish_deposit(new_deposit_id, token)

        print(f"✅ Publicado correctamente. Nuevo DOI: {publish_resp.get('doi')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
