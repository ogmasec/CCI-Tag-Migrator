# Import necessary libraries
import requests  # To make HTTP requests to the API
import json      # To handle JSON data
import argparse  # To parse command-line arguments (e.g., "python script.py 4")
import os        # To interact with the OS (e.g., check if a file exists)
import logging   # To create detailed log files

# ==============================================================================
# LOGGING SETUP
# Configures the logging system to record script actions.
# ==============================================================================
logging.basicConfig(
    level=logging.DEBUG,  # Capture all log levels, from DEBUG to CRITICAL.
    format='%(asctime)s - %(levelname)s - %(message)s',  # Define log message format.
    filename='migration_log.log',  # Log file name.
    filemode='w'  # 'w' overwrites the log file on each run; 'a' would append.
)
# Also log important messages to the console.
console = logging.StreamHandler()
console.setLevel(logging.INFO) # Only show INFO level and higher in the console.
formatter = logging.Formatter('%(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


# ==============================================================================
# CONFIGURATION
# IMPORTANT: Fill in your tenant details here.
# ==============================================================================
OLD_TENANT_URL = "https://your-old-tenant.goskope.com"
OLD_TENANT_TOKEN = "your_netskope_api_token_for_the_old_tenant"

NEW_TENANT_URL = "https://your-new-tenant.goskope.com"
NEW_TENANT_TOKEN = "your_netskope_api_token_for_the_new_tenant"


# ==============================================================================
# Global variables for script-generated files.
TAGS_FILE = "tags.json"
APPS_PER_TAG_FILE = "applications_per_tag.json"


# Makes a GET request to the API, typically to fetch data.
def make_api_get_request(base_url, endpoint, token, params=None):
    headers = {"Netskope-Api-Token": token}
    full_url = f"{base_url}{endpoint}"
    logging.debug(f"GET Request: URL={full_url}, Params={params}")
    try:
        response = requests.get(full_url, headers=headers, params=params)
        logging.debug(f"Response: Status={response.status_code}, Body={response.text}")
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx).
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during GET request to {full_url}: {e}")
        return None


# Makes a POST request to the API, typically to create or update data.
def make_api_post_request(base_url, endpoint, token, payload):
    headers = {"Netskope-Api-Token": token, "Content-Type": "application/json"}
    full_url = f"{base_url}{endpoint}"
    logging.debug(f"POST Request: URL={full_url}, Payload={json.dumps(payload)}")
    try:
        response = requests.post(full_url, headers=headers, data=json.dumps(payload))
        logging.debug(f"Response: Status={response.status_code}, Body={response.text}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during POST request to {full_url}: {e}")
        return None


# Makes a DELETE request to the API, handling Netskope's specific response behavior.
def make_api_delete_request(base_url, endpoint, token, params=None):
    """
    Handles the specific case where a 200 OK response contains a 202 Accepted status in its body.
    """
    headers = {"Netskope-Api-Token": token}
    full_url = f"{base_url}{endpoint}"
    logging.debug(f"DELETE Request: URL={full_url}, Params={params}")
    try:
        response = requests.delete(full_url, headers=headers, params=params)
        logging.debug(f"Response: Status={response.status_code}, Body={response.text}")

        # If HTTP status is 200, check the JSON body for the real status.
        if response.status_code == 200:
            try:
                response_data = response.json()
                # If the status code inside the body is 202, it's a success.
                if response_data.get("status_code") == 202:
                    logging.info("API returned 200 OK, but body confirms 202 Accepted. Treating as success.")
                    return 202  # Return the "real" status code.
                else:
                    logging.warning(f"API returned 200 OK, but body indicates a different status: {response.text}")
                    return 200  # Return 200 to be treated as a failure.
            except json.JSONDecodeError:
                logging.error(f"API returned 200 OK, but the response body was not valid JSON: {response.text}")
                return 200

        response.raise_for_status() # Raise exception for other non-200 codes.
        return response.status_code
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error during DELETE request: {e}")
        if e.response is not None:
            return e.response.status_code
        return None


# --- Script Steps ---

# Step 1: Fetches all tags from the old tenant.
def get_all_tags():
    logging.info("--- Starting Step 1: Get All Tags ---")
    endpoint = "/api/v2/services/cci/tags/all"
    data = make_api_get_request(OLD_TENANT_URL, endpoint, OLD_TENANT_TOKEN)
    if data and data.get("status") == "Success":
        tags = data.get("data", {}).get("tags", [])
        logging.info(f"Successfully found {len(tags)} tags.")
        for tag in tags:
            logging.info(f"  - {tag}")
        # Write the list of tags to the tags.json file.
        with open(TAGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tags, f, indent=4)
    else:
        logging.error("Failed to get tags.")


# Step 2: For each tag, fetches its associated applications.
def get_apps_for_tags():
    logging.info("--- Starting Step 2: Get Apps For Tags ---")
    if not os.path.exists(TAGS_FILE):
        logging.error(f"File '{TAGS_FILE}' not found. Please run Step 1 first.")
        return
    # Read tags from the file created in Step 1.
    with open(TAGS_FILE, 'r', encoding='utf-8') as f:
        tags = json.load(f)
    apps_per_tag = {}
    endpoint = "/api/v2/services/cci/apps/all"
    # Loop through each tag to get its apps.
    for tag in tags:
        logging.info(f"Searching apps for tag: '{tag}'")
        params = {"tag": tag, "tagtype": "all"}
        data = make_api_get_request(OLD_TENANT_URL, endpoint, OLD_TENANT_TOKEN, params=params)
        if data and data.get("status") == "Success":
            apps = data.get("data", {}).get("apps", [])
            apps_per_tag[tag] = apps
            logging.info(f"  -> Found {len(apps)} app(s).")
        else:
            apps_per_tag[tag] = []
    # Save the tag-to-apps mapping to a file.
    with open(APPS_PER_TAG_FILE, 'w', encoding='utf-8') as f:
        json.dump(apps_per_tag, f, indent=4)


# Step 3: Applies tags to applications on the new tenant.
def apply_tags_on_new_tenant():
    logging.info("--- Starting Step 3: Apply Tags ---")
    if not os.path.exists(APPS_PER_TAG_FILE):
        logging.error(f"File '{APPS_PER_TAG_FILE}' not found. Please run Step 2 first.")
        return
    # Read the tag/app mapping from the Step 2 file.
    with open(APPS_PER_TAG_FILE, 'r', encoding='utf-8') as f:
        apps_per_tag = json.load(f)
    logging.info(f"Applying tags to tenant: {NEW_TENANT_URL}")
    confirm = input("Are you sure you want to continue? (yes/no): ").lower()
    if confirm != 'yes':
        logging.info("Operation cancelled by user.")
        return
    
    # Helper function to apply a single tag to its apps.
    def _apply_single_tag(tag, apps):
        if not apps: return
        logging.info(f"Applying tag '{tag}' to {len(apps)} apps.")
        payload = {"tag": tag, "apps": apps}
        endpoint = "/api/v2/services/cci/tags"
        make_api_post_request(NEW_TENANT_URL, endpoint, NEW_TENANT_TOKEN, payload)

    # Interactive loop to ask the user to apply all tags or a specific one.
    while True:
        mode = input("Apply (1) All tags or (2) A specific tag? [1/2]: ").strip()
        if mode in ['1', '2']: break
    if mode == '1':
        for tag, apps in apps_per_tag.items():
            _apply_single_tag(tag, apps)
    elif mode == '2':
        target_tag = input("Enter the exact tag name: ").strip()
        if target_tag in apps_per_tag:
            _apply_single_tag(target_tag, apps_per_tag[target_tag])
        else:
            logging.error(f"Tag '{target_tag}' not found in migration file.")


# Step 4: Rolls back the migration by deleting the created tags.
def rollback_tags_on_new_tenant():
    logging.info("--- Starting Step 4: Rollback Tags ---")
    if not os.path.exists(APPS_PER_TAG_FILE):
        logging.error(f"File '{APPS_PER_TAG_FILE}' not found.")
        return

    logging.warning(f"This will delete tags from tenant: {NEW_TENANT_URL}")
    if input("Are you absolutely sure? (yes/no): ").lower() != 'yes':
        logging.info("Rollback operation cancelled by user.")
        return

    # Use the Step 2 file as a plan for what to delete.
    with open(APPS_PER_TAG_FILE, 'r', encoding='utf-8') as f:
        apps_per_tag = json.load(f)

    tags_to_delete = list(apps_per_tag.keys())
    endpoint = "/api/v2/services/cci/tags"

    # Loop through each tag to delete.
    for tag in tags_to_delete:
        logging.info(f"Attempting to delete tag: '{tag}'")
        # Prepare the query parameters for the request.
        params = {"tags": tag}
        # Call the delete function.
        status_code = make_api_delete_request(NEW_TENANT_URL, endpoint, NEW_TENANT_TOKEN, params=params)
        
        # Interpret the returned status code.
        if status_code == 202:
            logging.info(f"  => SUCCESS: Deletion request for tag '{tag}' was accepted.")
        elif status_code == 404:
            logging.warning(f"  => INFO: Tag '{tag}' was not found (might be already deleted).")
        else:
            # All other cases (including the non-compliant 200) are failures.
            logging.error(f"  => FAILURE: Failed to delete tag '{tag}'. Final status code: {status_code}")


# Main entry point of the script.
if __name__ == "__main__":
    # Configure the command-line argument parser.
    parser = argparse.ArgumentParser(
        description="Netskope CCI Tag Migration Script",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # Add the "step" argument, which is required and must be 1, 2, 3, or 4.
    parser.add_argument(
        "step", 
        choices=['1', '2', '3', '4'], 
        help="""1: Get all tags\n2: Get apps for each tag\n3: Apply tags\n4: Rollback tags"""
    )
    # Parse the arguments provided by the user.
    args = parser.parse_args()
    
    # Execute the function corresponding to the user's chosen step.
    if args.step == '1':
        get_all_tags()
    elif args.step == '2':
        get_apps_for_tags()
    elif args.step == '3':
        apply_tags_on_new_tenant()
    elif args.step == '4':
        rollback_tags_on_new_tenant()
