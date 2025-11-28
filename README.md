> **⚠️ Disclaimer:** This script is provided "as is" without warranty of any kind. Always test the migration process on a limited scope (using Mode 3, Option 2) before performing a full bulk migration on a production tenant.

# Netskope CCI Tag Migrator

A Python utility designed to automate the migration of Cloud Confidence Index (CCI) tags and their associated applications from one Netskope tenant to another.

This tool ensures a controlled migration process by splitting the workflow into extraction, mapping, deployment, and rollback phases.

## 📡 API Reference

This tool exclusively uses the **Netskope REST API v2**.
To function correctly, the script requires API Tokens with specific permissions (Scopes) on the following endpoints:

| Tenant | Method | Endpoint | Purpose | Permission Required |
| :--- | :--- | :--- | :--- | :--- |
| **Source** | `GET` | `/api/v2/services/cci/tags/all` | Fetch all existing tags | **Read** |
| **Source** | `GET` | `/api/v2/services/cci/apps/all` | Fetch apps for a specific tag | **Read** |
| **Dest** | `POST` | `/api/v2/services/cci/tags` | Create a new tag with apps | **Read & Write** |
| **Dest** | `DELETE`| `/api/v2/services/cci/tags` | Delete a tag (Rollback) | **Read & Write** |

## ⚙️ The 4 Modes of Operation

The script is executed using a positional argument to select the mode (`1`, `2`, `3`, or `4`).

### Mode 1: Extraction
**Command:** `python netskope_migrator.py 1`
* **Action:** Connects to the **Old Tenant** and retrieves a list of all CCI Tags.
* **Output:** Generates a `tags.json` file locally.

### Mode 2: Association
**Command:** `python netskope_migrator.py 2`
* **Action:** Reads `tags.json`, iterates through every tag, and queries the **Old Tenant** to find which applications are assigned to each tag.
* **Output:** Generates a `applications_per_tag.json` file.
* **Note:** This file serves as the "master plan" for the migration. You can manually inspect it to verify data before deployment.

### Mode 3: Deployment
**Command:** `python netskope_migrator.py 3`
* **Action:** Reads `applications_per_tag.json` and pushes the configuration to the **New Tenant**.
* **Features:**
    * **Bulk Migration:** Apply all tags found in the JSON file.
    * **Selective Migration:** Apply only one specific tag (prompted by name).

### Mode 4: Rollback
**Command:** `python netskope_migrator.py 4`
* **Action:** Reads `applications_per_tag.json` and deletes the corresponding tags from the **New Tenant**.
* **Use Case:** Emergency cleanup or reverting changes if the migration was incorrect.

## 📋 Prerequisites

1.  **Python 3.6+** installed.
2.  **Requests library**:
    ```bash
    pip install requests
    ```
3.  **API Tokens**: Generated via the Netskope UI under *Settings > Tools > REST API v2*.

## 🚀 Setup & Configuration

1.  Clone this repository or download the script.
2.  Open `netskope_migrator.py` in a text editor.
3.  Locate the **CONFIGURATION** section at the top of the file.
4.  Update the variables with your specific tenant URLs and tokens:

```python
# ==============================================================================
# CONFIGURATION
# ==============================================================================
OLD_TENANT_URL = "[https://source-tenant.goskope.com](https://source-tenant.goskope.com)"
OLD_TENANT_TOKEN = "your_source_read_token"

NEW_TENANT_URL = "[https://dest-tenant.goskope.com](https://dest-tenant.goskope.com)"
NEW_TENANT_TOKEN = "your_dest_read_write_token"
