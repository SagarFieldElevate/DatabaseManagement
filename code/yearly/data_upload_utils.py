import os
import base64
import time
import requests
import pandas as pd

# Name of the attachment field in Airtable
ATTACHMENT_FIELD = os.getenv("AIRTABLE_ATTACHMENT_FIELD", "Attachments")

def ensure_utc(df):
    """Ensure all datetime columns use datetime64[ns, UTC]."""
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            if df[col].dt.tz is None:
                df[col] = df[col].dt.tz_localize("UTC")
            else:
                df[col] = df[col].dt.tz_convert("UTC")
        elif pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            converted = pd.to_datetime(df[col], errors="ignore", utc=True)
            if pd.api.types.is_datetime64_any_dtype(converted):
                df[col] = converted
    return df

def standardize_date_column(df):
    """Rename the first date-like column to 'Date' and parse it."""
    date_cols = [c for c in df.columns if 'time' in c.lower() or 'date' in c.lower()]
    target = date_cols[0] if date_cols else df.columns[0]
    if target != 'Date':
        df.rename(columns={target: 'Date'}, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df


_ORIG_TO_EXCEL = pd.DataFrame.to_excel

def _drop_timezone(df):
    """Remove timezone from datetime columns and store non-UTC tz in new columns."""
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            tz = df[col].dt.tz
            if tz is not None:
                if str(tz) != "UTC":
                    df[f"{col}_timezone"] = str(tz)
                df[col] = df[col].dt.tz_convert("UTC").dt.tz_localize(None)
    return df

def _to_excel_utc(self, *args, **kwargs):
    self = ensure_utc(self)
    self = _drop_timezone(self)
    return _ORIG_TO_EXCEL(self, *args, **kwargs)

if not getattr(pd.DataFrame.to_excel, "_utc_patched", False):
    pd.DataFrame.to_excel = _to_excel_utc
    pd.DataFrame.to_excel._utc_patched = True

__all__ = [
    "ensure_utc",
    "standardize_date_column",
    "upload_to_github",
    "create_airtable_record",
    "update_airtable",
    "delete_file_from_github",
    "find_record_id_by_name",
]

def upload_to_github(filename, repo_name, branch, upload_path, token, max_retries=3):
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
            response_json = upload_resp.json()
            raw_url = f"https://raw.githubusercontent.com/{repo_name}/{branch}/{upload_path}/{filename}"
            response_json['content']['raw_url'] = raw_url
            return response_json

        if upload_resp.status_code == 409 and attempt < max_retries - 1:
            continue

        if upload_resp.status_code >= 500 and attempt < max_retries - 1:
            time.sleep(2 ** attempt)
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

def delete_file_from_github(filename, repo_name, branch, upload_path, token, sha=None, max_retries=3):
    """Delete a file from GitHub, retrying on conflicts and always using the latest SHA."""

    delete_url = f"https://api.github.com/repos/{repo_name}/contents/{upload_path}/{filename}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    for attempt in range(max_retries):
        get_resp = requests.get(f"{delete_url}?ref={branch}", headers=headers)
        if get_resp.status_code == 404:
            return
        if get_resp.status_code != 200:
            raise Exception(f"❌ Unable to fetch file SHA: {get_resp.status_code} - {get_resp.text}")

        sha = get_resp.json().get("sha")
        if not sha:
            raise Exception("❌ No SHA returned for file")

        delete_payload = {
            "message": f"Delete {filename}",
            "sha": sha,
            "branch": branch,
        }

        delete_resp = requests.delete(delete_url, headers=headers, json=delete_payload)
        if delete_resp.status_code == 200:
            return delete_resp.json()

        if delete_resp.status_code == 409 and attempt < max_retries - 1:
            continue

        if delete_resp.status_code == 404:
            return

        raise Exception(f"❌ GitHub file deletion failed: {delete_resp.status_code} - {delete_resp.text}")


def find_record_id_by_name(name, airtable_url, airtable_token):
    """Return the Airtable record ID with the given Name."""
    headers = {
        "Authorization": f"Bearer {airtable_token}",
        "Content-Type": "application/json",
    }
    params = {"filterByFormula": f"{{Name}}='{name}'", "maxRecords": 1}
    resp = requests.get(airtable_url, headers=headers, params=params)
    resp.raise_for_status()
    records = resp.json().get("records", [])
    return records[0]["id"] if records else None
