import os
import base64
import requests

# Name of the Airtable attachment field. Can be overridden using the
# AIRTABLE_ATTACHMENT_FIELD environment variable if a different field name is
# configured in the Airtable base.
ATTACHMENT_FIELD = os.getenv("AIRTABLE_ATTACHMENT_FIELD", "Attachments")

def upload_to_github(filename, repo_name, branch, upload_path, token, max_retries=3):
    """Upload a file to GitHub, retrying on 409 conflicts."""

    with open(filename, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    upload_url = f"https://api.github.com/repos/{repo_name}/contents/{upload_path}/{filename}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    for attempt in range(max_retries):
        # Step 1: Check if file already exists to get its SHA
        get_resp = requests.get(f"{upload_url}?ref={branch}", headers=headers)
        sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None

        # Step 2: Prepare upload payload
        upload_payload = {
            "message": f"Upload {filename}",
            "content": content,
            "branch": branch
        }
        if sha:
            upload_payload["sha"] = sha  # Needed for overwrite

        # Step 3: Upload (PUT) to GitHub
        upload_resp = requests.put(upload_url, headers=headers, json=upload_payload)
        if upload_resp.status_code in [200, 201]:
            # Step 4: Add raw_url manually
            response_json = upload_resp.json()
            raw_url = f"https://raw.githubusercontent.com/{repo_name}/{branch}/{upload_path}/{filename}"
            response_json['content']['raw_url'] = raw_url
            return response_json

        if upload_resp.status_code == 409 and attempt < max_retries - 1:
            # Branch moved; retry after fetching the latest SHA
            continue

        raise Exception(f"❌ GitHub upload failed: {upload_resp.status_code} - {upload_resp.text}")

def update_airtable(record_id, raw_url, filename, airtable_url, airtable_token):
    airtable_headers = {
        "Authorization": f"Bearer {airtable_token}",
        "Content-Type": "application/json"
    }
    patch_payload = {
        "fields": {
            ATTACHMENT_FIELD: [
                {
                    "url": raw_url,
                    "filename": filename
                }
            ]
        }
    }
    patch_url = f"{airtable_url}/{record_id}"
    response = requests.patch(patch_url, headers=airtable_headers, json=patch_payload)
    if response.status_code != 200:
        raise Exception(f"❌ Airtable update failed: {response.status_code} - {response.text}")
    
def create_airtable_record(name, raw_url, filename, airtable_url, airtable_token, additional_fields=None):
    airtable_headers = {
        "Authorization": f"Bearer {airtable_token}",
        "Content-Type": "application/json"
    }

    # Core required fields
    record_fields = {
        "Name": name,
        ATTACHMENT_FIELD: [{
            "url": raw_url,
            "filename": filename
        }]
    }

    # Add any extra fields if they're provided
    if additional_fields:
        record_fields.update(additional_fields)

    post_payload = {
        "records": [{
            "fields": record_fields
        }]
    }

    airtable_resp = requests.post(airtable_url, headers=airtable_headers, json=post_payload)
    if airtable_resp.status_code != 200:
        raise Exception(f"❌ Airtable record creation failed: {airtable_resp.status_code} - {airtable_resp.text}")

        raise Exception(f"❌ Airtable record creation failed: {airtable_resp.status_code} - {airtable_resp.text}")

def delete_file_from_github(filename, repo_name, branch, upload_path, token, sha):
    delete_url = f"https://api.github.com/repos/{repo_name}/contents/{upload_path}/{filename}"
    delete_payload = {
        "message": f"Delete {filename}",
        "sha": sha,
        "branch": branch
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    delete_resp = requests.delete(delete_url, headers=headers, json=delete_payload)
    if delete_resp.status_code != 200:
        raise Exception(f"❌ GitHub file deletion failed: {delete_resp.status_code} - {delete_resp.text}")
