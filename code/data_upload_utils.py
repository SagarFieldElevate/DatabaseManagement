import os
import base64
import requests

def upload_to_github(filename, repo_name, branch, upload_path, token):
    with open(filename, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    upload_url = f"https://api.github.com/repos/{repo_name}/contents/{upload_path}/{filename}"
    upload_payload = {
        "message": f"Upload {filename}",
        "content": content,
        "branch": branch
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    upload_resp = requests.put(upload_url, headers=headers, json=upload_payload)
    if upload_resp.status_code not in [200, 201]:
        raise Exception(f"❌ GitHub upload failed: {upload_resp.status_code} - {upload_resp.text}")

    # Construct raw GitHub URL manually
    raw_url = f"https://raw.githubusercontent.com/{repo_name}/{branch}/{upload_path}/{filename}"
    response_json = upload_resp.json()
    response_json['content']['raw_url'] = raw_url
    return response_json

def update_airtable(record_id, raw_url, filename, airtable_url, airtable_token):
    airtable_headers = {
        "Authorization": f"Bearer {airtable_token}",
        "Content-Type": "application/json"
    }
    patch_payload = {
        "fields": {
            "Database Attachment": [
                {
                    "url": raw_url,
                    "filename": filename
                }
            ]
        }
    }
    patch_url = f"{airtable_url}/{record_id}"
    airtable_resp = requests.patch(patch_url, headers=airtable_headers, json=patch_payload)
    if airtable_resp.status_code != 200:
        raise Exception(f"❌ Airtable upload failed: {airtable_resp.status_code} - {airtable_resp.text}")

def create_airtable_record(name, raw_url, filename, airtable_url, airtable_token, additional_fields=None):
    airtable_headers = {
        "Authorization": f"Bearer {airtable_token}",
        "Content-Type": "application/json"
    }
    fields = {
        "Name": name,
        "Database Attachment": [
            {
                "url": raw_url,
                "filename": filename
            }
        ]
    }
    if additional_fields:
        fields.update(additional_fields)

    post_payload = {
        "records": [{"fields": fields}]
    }
    airtable_resp = requests.post(airtable_url, headers=airtable_headers, json=post_payload)
    if airtable_resp.status_code != 200:
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
